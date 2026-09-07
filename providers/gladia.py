"""The Gladia provider: Whisper transcription plus pyannote diarization, whole recording.

Unlike Deepgram, the speaker count here is genuinely BINDING: `diarization_config` takes
`number_of_speakers`, `min_speakers` and `max_speakers`, and pyannote honours those limits.
When the researcher gives no number, diarization stays fully automatic.

The v2 API has three steps: upload the file, request the transcription, then poll for the
result.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from models import TranscriptSegment, Word
from typing import Callable

from providers.base import (CancelCallback, ProgressCallback, ProviderCapabilities, ProviderError, ProviderInfo,
                            TranscriptionProvider, emit_progress, language_code, format_elapsed, merge_turns, whole_file_segment)
from providers.http import (JOB_TIMEOUT, POLL_TIMEOUT, RETRY_ATTEMPTS, send, send_json, upload_file, with_retry)

SERVICE = "Gladia"
API_BASE = "https://api.gladia.io/v2"
MODEL = "gladia-v2"
DEFAULT_LANGUAGE = "ro"
UPLOAD_SHARE = .55
POLL_START = .60
POLL_CEILING = .92
POLL_INTERVAL = 5.0
# Five seconds apart, this waits about three hours before giving up — comfortably longer than
# any two-hour recording takes to process, and each individual request is only seconds long.
POLL_ATTEMPTS = 2160


def diarization_config(expected_speakers: int) -> dict[str, Any]:
    """Genuinely binds the speaker count, where Deepgram only takes it as a hint."""
    if not expected_speakers or expected_speakers < 1: return {}
    count = int(expected_speakers)
    return {"number_of_speakers": count, "min_speakers": count, "max_speakers": count}


def request_payload(audio_url: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0) -> dict[str, Any]:
    payload: dict[str, Any] = {"audio_url": audio_url, "diarization": True}
    code = language_code(language, DEFAULT_LANGUAGE)
    # "Detect automatically" is an option in Settings, not a language code. Sent as one it
    # would reach Gladia as `language: "auto"`, which is not a language it knows.
    if code is None: payload["detect_language"] = True
    else: payload["language"] = code; payload["detect_language"] = False
    config = diarization_config(expected_speakers)
    if config: payload["diarization_config"] = config
    return payload


def _number(raw: Any, default: float = 0.0) -> float:
    try: return float(raw)
    except (TypeError, ValueError): return default


def _optional_number(raw: Any) -> float | None:
    return None if raw is None else _number(raw)


def _word(raw: dict[str, Any]) -> Word:
    start = _number(raw.get("start")); end = _number(raw.get("end"), start)
    return Word(start, end, str(raw.get("word") or raw.get("text") or ""), _optional_number(raw.get("confidence")))


def _utterance(raw: dict[str, Any]) -> TranscriptSegment | None:
    text = str(raw.get("text") or raw.get("transcript") or "").strip()
    if not text: return None
    start = _number(raw.get("start")); end = _number(raw.get("end"), start)
    words = [_word(item) for item in raw.get("words") or [] if isinstance(item, dict)]
    return whole_file_segment(raw.get("speaker", 0), text, start, end, words, _optional_number(raw.get("confidence")))


def parse_result(payload: dict[str, Any]) -> list[TranscriptSegment]:
    transcription = ((payload.get("result") or {}).get("transcription") or {})
    utterances = transcription.get("utterances") or []
    segments = [item for item in (_utterance(raw) for raw in utterances if isinstance(raw, dict))
                if item and item.original_text]
    if not segments: raise ProviderError("The Gladia response contains no speech.")
    ordered = sorted(segments, key=lambda s: (s.absolute_start, s.absolute_end))
    # Gladia returns one utterance per short phrase; merge them back into readable turns.
    return merge_turns(ordered)


class GladiaProvider(TranscriptionProvider):
    """Global diarization with the speaker count enforced, when the researcher knows it."""

    info = ProviderInfo(
        key="gladia",
        label="Gladia · Whisper + pyannote",
        model=MODEL,
        key_label="Gladia API key",
        missing_key="Enter the Gladia API key.",
        transfer_note="The original is never modified. A complete copy of the recording is sent to Gladia.",
        capabilities=ProviderCapabilities(supports_diarization=True, supports_word_timestamps=True,
                                          supports_confidence=True, global_speakers=True),
        note="The key is never saved. The expected speaker count is enforced by the diarizer.")

    def __init__(self, api_key: str, cancelled: CancelCallback | None = None,
                 poll_interval: float = POLL_INTERVAL, poll_attempts: int = POLL_ATTEMPTS,
                 retry_attempts: int = RETRY_ATTEMPTS,
                 sleeper: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.api_key = api_key; self.cancelled = cancelled
        self.poll_interval = poll_interval; self.poll_attempts = poll_attempts
        self.retry_attempts = retry_attempts
        # Injected so tests can drive a long job without waiting for one.
        self.sleeper = sleeper; self.clock = clock

    @property
    def _headers(self) -> dict[str, str]:
        return {"x-gladia-key": self.api_key}

    def transcribe(self, audio_path: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        if not self.api_key.strip(): raise ProviderError(self.info.missing_key)
        path = Path(audio_path)
        if not path.is_file(): raise ProviderError("The selected recording is no longer available.")

        uploaded = upload_file(SERVICE, f"{API_BASE}/upload", self._headers, path, "audio", None, progress_cb,
                               self.cancelled, "Uploading the recording to Gladia", UPLOAD_SHARE,
                               "Upload complete. Requesting transcription.",
                               on_retry=self._retry_notice(progress_cb), sleeper=self.sleeper)
        audio_url = uploaded.get("audio_url") or uploaded.get("audio_metadata", {}).get("audio_url")
        if not audio_url: raise ProviderError("Gladia did not return the uploaded file address.")

        payload = request_payload(str(audio_url), language, expected_speakers)
        if "diarization_config" in payload:
            emit_progress(progress_cb, f"Diarization constrained to {expected_speakers} speakers.", None)
        started = with_retry(lambda: send_json(SERVICE, f"{API_BASE}/pre-recorded", self._headers, payload,
                                               timeout=JOB_TIMEOUT),
                             self.retry_attempts, on_retry=self._retry_notice(progress_cb),
                             sleeper=self.sleeper, cancelled=self.cancelled)
        result_url = started.get("result_url") or (f"{API_BASE}/pre-recorded/{started['id']}" if started.get("id") else "")
        if not result_url: raise ProviderError("Gladia did not return a transcription identifier.")

        result = self._poll(str(result_url), progress_cb)
        emit_progress(progress_cb, "Reading the Gladia response.", .96)
        segments = parse_result(result)
        speakers = len({item.speaker_id for item in segments})
        emit_progress(progress_cb, f"{speakers} speakers identified across the whole recording by pyannote.", None)
        return segments

    def _retry_notice(self, progress_cb: ProgressCallback | None):
        def notice(attempt: int, attempts: int, delay: float, exc: ProviderError) -> None:
            emit_progress(progress_cb,
                          f"Connection problem ({exc}). Retrying in {delay:.0f}s "
                          f"— attempt {attempt + 1} of {attempts}.", None)
        return notice

    def _poll(self, result_url: str, progress_cb: ProgressCallback | None) -> dict[str, Any]:
        """Ask the job for its status until it finishes.

        Each request is short and independent, so a long job never depends on one connection
        staying open. A dropped packet retries the SAME job id rather than restarting the work.
        """
        started = self.clock()
        notice = self._retry_notice(progress_cb)
        emit_progress(progress_cb, "Gladia is processing the recording. This can take several minutes.", POLL_START)
        for attempt in range(1, self.poll_attempts + 1):
            if self.cancelled and self.cancelled():
                raise ProviderError("The transcription was cancelled while processing.")
            payload = with_retry(lambda: send(SERVICE, result_url, self._headers, timeout=POLL_TIMEOUT),
                                 self.retry_attempts, on_retry=notice, sleeper=self.sleeper,
                                 cancelled=self.cancelled)
            status = str(payload.get("status") or "").lower()
            if status in ("done", "completed", "success"): return payload
            if status in ("error", "failed"):
                detail = str(payload.get("error_code") or (payload.get("error") or {}) or "")
                raise ProviderError(f"Gladia reported a processing error. {detail}".strip())
            # Asymptotic: the duration is unknown, but the bar has to keep moving visibly.
            share = POLL_START + (POLL_CEILING - POLL_START) * (1 - 1 / (1 + attempt / 8))
            emit_progress(progress_cb,
                          f"Processing on Gladia — elapsed {format_elapsed(self.clock() - started)}.", share)
            if self.poll_interval: self.sleeper(self.poll_interval)
        raise ProviderError("Gladia did not finish the transcription within the expected time.")
