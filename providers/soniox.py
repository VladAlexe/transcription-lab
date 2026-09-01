"""The Soniox provider: asynchronous file transcription, with diarization, word timings
and confidence.

Soniox reports at token level: each token carries its text, its interval, a confidence
score and a global speaker number. Consecutive tokens from the same speaker are grouped
into a single turn.

The flow has four steps: upload the file, request the transcription, poll the status, then
download the transcript.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from models import TranscriptSegment, Word
from typing import Callable

from providers.base import (CancelCallback, ProgressCallback, ProviderCapabilities, ProviderError, ProviderInfo,
                            TranscriptionProvider, emit_progress, format_elapsed, group_by_speaker)
from providers.http import (JOB_TIMEOUT, POLL_TIMEOUT, RETRY_ATTEMPTS, send, send_json, upload_file, with_retry)

SERVICE = "Soniox"
API_BASE = "https://api.soniox.com/v1"
MODEL = "stt-async-preview"
DEFAULT_LANGUAGE = "ro"
UPLOAD_SHARE = .55
POLL_START = .60
POLL_CEILING = .92
POLL_INTERVAL = 5.0
POLL_ATTEMPTS = 2160  # ~3 hours at a 5 second interval


def request_payload(file_id: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0) -> dict[str, Any]:
    payload: dict[str, Any] = {"file_id": file_id, "model": MODEL, "enable_speaker_diarization": True,
                               "language_hints": [language or DEFAULT_LANGUAGE]}
    # Soniox works the speaker count out for itself; the value stays a hint, as with Deepgram.
    if expected_speakers and expected_speakers > 1: payload["num_speakers"] = int(expected_speakers)
    return payload


def _number(raw: Any, default: float = 0.0) -> float:
    try: return float(raw)
    except (TypeError, ValueError): return default


def _token(raw: dict[str, Any]) -> tuple[Any, Word]:
    start = _number(raw.get("start_ms")) / 1000.0
    end = _number(raw.get("end_ms"), _number(raw.get("start_ms"))) / 1000.0
    confidence = raw.get("confidence")
    word = Word(start, end, str(raw.get("text") or ""), None if confidence is None else _number(confidence))
    return raw.get("speaker", 0), word


def parse_transcript(payload: dict[str, Any]) -> list[TranscriptSegment]:
    tokens = payload.get("tokens") or []
    segments = group_by_speaker(_token(raw) for raw in tokens if isinstance(raw, dict))
    if not segments: raise ProviderError("The Soniox response contains no speech.")
    return sorted(segments, key=lambda s: (s.absolute_start, s.absolute_end))


class SonioxProvider(TranscriptionProvider):
    """Global diarization, timings and confidence at token level, in one async flow."""

    info = ProviderInfo(
        key="soniox",
        label="Soniox · asynchronous transcription",
        model=MODEL,
        key_label="Soniox API key",
        missing_key="Enter the Soniox API key.",
        transfer_note="The original is never modified. A complete copy of the recording is sent to Soniox.",
        capabilities=ProviderCapabilities(supports_diarization=True, supports_word_timestamps=True,
                                          supports_confidence=True, global_speakers=True),
        note="The key is never saved. The expected speaker count is only a hint for this provider.")

    def __init__(self, api_key: str, cancelled: CancelCallback | None = None,
                 poll_interval: float = POLL_INTERVAL, poll_attempts: int = POLL_ATTEMPTS,
                 retry_attempts: int = RETRY_ATTEMPTS,
                 sleeper: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.api_key = api_key; self.cancelled = cancelled
        self.poll_interval = poll_interval; self.poll_attempts = poll_attempts
        self.retry_attempts = retry_attempts
        self.sleeper = sleeper; self.clock = clock

    def _retry_notice(self, progress_cb: ProgressCallback | None):
        def notice(attempt: int, attempts: int, delay: float, exc: ProviderError) -> None:
            emit_progress(progress_cb,
                          f"Connection problem ({exc}). Retrying in {delay:.0f}s "
                          f"— attempt {attempt + 1} of {attempts}.", None)
        return notice

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def transcribe(self, audio_path: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        if not self.api_key.strip(): raise ProviderError(self.info.missing_key)
        path = Path(audio_path)
        if not path.is_file(): raise ProviderError("The selected recording is no longer available.")

        uploaded = upload_file(SERVICE, f"{API_BASE}/files", self._headers, path, "file", None, progress_cb,
                               self.cancelled, "Uploading the recording to Soniox", UPLOAD_SHARE,
                               "Upload complete. Requesting transcription.",
                               on_retry=self._retry_notice(progress_cb), sleeper=self.sleeper)
        file_id = uploaded.get("id") or uploaded.get("file_id")
        if not file_id: raise ProviderError("Soniox did not return an uploaded file identifier.")

        started = with_retry(lambda: send_json(SERVICE, f"{API_BASE}/transcriptions", self._headers,
                                               request_payload(str(file_id), language, expected_speakers),
                                               timeout=JOB_TIMEOUT),
                             self.retry_attempts, on_retry=self._retry_notice(progress_cb),
                             sleeper=self.sleeper, cancelled=self.cancelled)
        transcription_id = started.get("id")
        if not transcription_id: raise ProviderError("Soniox did not return a transcription identifier.")

        self._poll(str(transcription_id), progress_cb)
        emit_progress(progress_cb, "Downloading the Soniox transcript.", .96)
        payload = with_retry(lambda: send(SERVICE, f"{API_BASE}/transcriptions/{transcription_id}/transcript",
                                          self._headers, timeout=JOB_TIMEOUT),
                             self.retry_attempts, on_retry=self._retry_notice(progress_cb),
                             sleeper=self.sleeper, cancelled=self.cancelled)
        segments = parse_transcript(payload)
        speakers = len({item.speaker_id for item in segments})
        emit_progress(progress_cb, f"{speakers} speakers identified across the whole recording.", None)
        return segments

    def _poll(self, transcription_id: str, progress_cb: ProgressCallback | None) -> None:
        """Short, independent status requests; a dropped one resumes the same job id."""
        started = self.clock()
        notice = self._retry_notice(progress_cb)
        emit_progress(progress_cb, "Soniox is processing the recording. This can take several minutes.", POLL_START)
        for attempt in range(1, self.poll_attempts + 1):
            if self.cancelled and self.cancelled():
                raise ProviderError("The transcription was cancelled while processing.")
            payload = with_retry(lambda: send(SERVICE, f"{API_BASE}/transcriptions/{transcription_id}",
                                              self._headers, timeout=POLL_TIMEOUT),
                                 self.retry_attempts, on_retry=notice, sleeper=self.sleeper,
                                 cancelled=self.cancelled)
            status = str(payload.get("status") or "").lower()
            if status in ("completed", "done", "success"): return
            if status in ("error", "failed"):
                raise ProviderError(f"Soniox reported a processing error. {payload.get('error_message') or ''}".strip())
            share = POLL_START + (POLL_CEILING - POLL_START) * (1 - 1 / (1 + attempt / 8))
            emit_progress(progress_cb,
                          f"Processing on Soniox — elapsed {format_elapsed(self.clock() - started)}.", share)
            if self.poll_interval: self.sleeper(self.poll_interval)
        raise ProviderError("Soniox did not finish the transcription within the expected time.")
