"""The Deepgram provider: one request for the whole recording, with global diarization.

Deepgram analyses the file as a whole, so speaker numbers are consistent from the start of
the interview to the end. On this path there is no need to reconcile labels across
fragments (`speaker_reconciliation.py`): the mapping is used only to give real names to the
handful of global speakers.

A note on the speaker count: Deepgram works out how many speakers there are for itself, and
`speakers_expected` is sent only as a hint. If the API rejects it the request is retried
without it — the expected number is ADVISORY here. The Gladia provider, built on pyannote,
genuinely binds it through `number_of_speakers` / `min_speakers` / `max_speakers`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from models import TranscriptSegment, Word
from providers.base import (CancelCallback, ProgressCallback, ProviderCapabilities, ProviderError, ProviderInfo,
                            TranscriptionProvider, emit_progress, group_by_speaker, language_code, merge_turns,
                            whole_file_segment)
from providers.http import (TRANSIENT_STATUS, UPLOAD_TIMEOUT, UploadReader, content_type, error_detail,
                            friendly, with_retry)

SERVICE = "Deepgram"
API_URL = "https://api.deepgram.com/v1/listen"
MODEL = "nova-2"
DEFAULT_LANGUAGE = "ro"
# The upload takes the first part of the bar; the rest is Deepgram's own processing.
UPLOAD_SHARE = .60
# Deepgram's pre-recorded endpoint is synchronous: this one request carries the upload and the
# transcription. There is no job id to poll, so the only defence for a long file is a generous
# timeout plus retries. For multi-hour recordings the async providers are the safer choice.
REQUEST_TIMEOUT = UPLOAD_TIMEOUT
RETRY_ATTEMPTS = 3


def request_params(language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0,
                   with_speaker_hint: bool = True) -> dict[str, str]:
    params = {"model": MODEL, "diarize": "true",
              "utterances": "true", "punctuate": "true", "smart_format": "true"}
    # Deepgram has its own flag for detection; `language=auto` is not a code it accepts.
    code = language_code(language, DEFAULT_LANGUAGE)
    if code: params["language"] = code
    else: params["detect_language"] = "true"
    if with_speaker_hint and expected_speakers and expected_speakers > 1:
        params["speakers_expected"] = str(int(expected_speakers))
    return params


def _number(raw: Any, default: float = 0.0) -> float:
    try: return float(raw)
    except (TypeError, ValueError): return default


def _optional_number(raw: Any) -> float | None:
    return None if raw is None else _number(raw)


def _word(raw: dict[str, Any]) -> Word:
    start = _number(raw.get("start")); end = _number(raw.get("end"), start)
    return Word(start, end, str(raw.get("punctuated_word") or raw.get("word") or ""),
                _optional_number(raw.get("confidence")))


def _from_utterance(raw: dict[str, Any]) -> TranscriptSegment | None:
    text = str(raw.get("transcript") or "").strip()
    if not text: return None
    start = _number(raw.get("start")); end = _number(raw.get("end"), start)
    words = [_word(item) for item in raw.get("words") or [] if isinstance(item, dict)]
    return whole_file_segment(raw.get("speaker", 0), text, start, end, words, _optional_number(raw.get("confidence")))


def _channel_words(results: dict[str, Any]) -> list[dict[str, Any]]:
    channels = results.get("channels") or []
    alternatives = (channels[0].get("alternatives") or []) if channels else []
    return (alternatives[0].get("words") or []) if alternatives else []


def parse_response(payload: dict[str, Any]) -> list[TranscriptSegment]:
    results = payload.get("results") or {}
    utterances = results.get("utterances") or []
    if utterances:
        items = [_from_utterance(raw) for raw in utterances if isinstance(raw, dict)]
    else:
        # Fallback for responses with no `utterances`: group the words by speaker.
        items = group_by_speaker((raw.get("speaker", 0), _word(raw)) for raw in _channel_words(results)
                                 if isinstance(raw, dict))
    segments = [item for item in items if item and item.original_text]
    if not segments: raise ProviderError("The Deepgram response contains no speech.")
    ordered = sorted(segments, key=lambda s: (s.absolute_start, s.absolute_end))
    return merge_turns(ordered)


class DeepgramProvider(TranscriptionProvider):
    """Global diarization: the whole recording in a single request."""

    info = ProviderInfo(
        key="deepgram",
        label="Deepgram · global diarization",
        model=MODEL,
        key_label="Deepgram API key",
        missing_key="Enter the Deepgram API key.",
        transfer_note="The original is never modified. A complete copy of the recording is sent to Deepgram.",
        capabilities=ProviderCapabilities(supports_diarization=True, supports_word_timestamps=True,
                                          supports_confidence=True, global_speakers=True),
        note="The key is never saved. The expected speaker count is only a hint for this provider.")

    def __init__(self, api_key: str, cancelled: CancelCallback | None = None,
                 timeout: int = REQUEST_TIMEOUT, retry_attempts: int = RETRY_ATTEMPTS,
                 sleeper=time.sleep) -> None:
        self.api_key = api_key; self.cancelled = cancelled; self.timeout = timeout
        self.retry_attempts = retry_attempts; self.sleeper = sleeper

    def transcribe(self, audio_path: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        if not self.api_key.strip(): raise ProviderError(self.info.missing_key)
        path = Path(audio_path)
        if not path.is_file(): raise ProviderError("The selected recording is no longer available.")
        def notice(attempt: int, attempts: int, delay: float, exc: ProviderError) -> None:
            emit_progress(progress_cb, f"Connection problem ({exc}). Retrying in {delay:.0f}s "
                                       f"— attempt {attempt + 1} of {attempts}.", None)

        payload = with_retry(lambda: self._send(path, language, expected_speakers, progress_cb, True),
                             self.retry_attempts, on_retry=notice, sleeper=self.sleeper,
                             cancelled=self.cancelled)
        emit_progress(progress_cb, "Reading the Deepgram response.", .97)
        segments = parse_response(payload)
        speakers = len({item.speaker_id for item in segments})
        emit_progress(progress_cb, f"{speakers} speakers identified across the whole recording.", None)
        return segments

    def _send(self, path: Path, language: str, expected_speakers: int,
              progress_cb: ProgressCallback | None, with_speaker_hint: bool) -> dict[str, Any]:
        params = request_params(language, expected_speakers, with_speaker_hint)
        url = f"{API_URL}?{urlencode(params)}"
        size = path.stat().st_size
        emit_progress(progress_cb, "Uploading the recording to Deepgram: 0%.", 0.0)
        try:
            with path.open("rb") as handle:
                reader = UploadReader(handle, size, progress_cb, self.cancelled, b"", b"",
                                      "Uploading the recording to Deepgram", UPLOAD_SHARE,
                                      "Deepgram is processing the recording. This can take several minutes.")
                request = Request(url, data=reader, method="POST",
                                  headers={"Authorization": f"Token {self.api_key}",
                                           "Content-Type": content_type(path), "Content-Length": str(size)})
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = error_detail(exc)
            # The speaker-count hint is advisory: if it is refused, retry without it.
            if with_speaker_hint and "speakers_expected" in params and exc.code in (400, 422):
                emit_progress(progress_cb, "Deepgram rejected the expected speaker count; retrying without that hint.", None)
                return self._send(path, language, expected_speakers, progress_cb, False)
            raise ProviderError(friendly(SERVICE, exc.code, detail),
                                transient=exc.code in TRANSIENT_STATUS) from exc
        except URLError as exc:
            raise ProviderError(f"Could not connect to Deepgram: {exc.reason}", transient=True) from exc
        except ProviderError: raise
        except TimeoutError as exc:
            raise ProviderError("The request to Deepgram timed out.", transient=True) from exc
        except OSError as exc:
            raise ProviderError(f"The Deepgram response could not be read: {exc}", transient=True) from exc
        except ValueError as exc:
            raise ProviderError(f"The Deepgram response could not be read: {exc}") from exc
