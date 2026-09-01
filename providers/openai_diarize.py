"""Furnizorul OpenAI `gpt-4o-transcribe-diarize`.

The logic moved here from `transcription.py`, which remains a compatibility shim. This
provider fragments the recording to stay under the API's size limit, and diarization is
done independently for each fragment: the resulting labels are `Fragment NN · Speaker X`
and are NOT global. Manual reconciliation is unavoidable on this path; see
`providers/deepgram.py` for the global-speaker alternative.
"""
from __future__ import annotations

import time
from functools import partial
from pathlib import Path
from typing import Any, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from audio_processing import create_chunks, probe_audio
from models import AudioChunk, MediaToolPaths, TranscriptSegment
from providers.base import (CancelCallback, ProgressCallback, ProviderCapabilities, ProviderError, ProviderInfo,
                            TranscriptionProvider, emit_progress)

MODEL = "gpt-4o-transcribe-diarize"
DEFAULT_LANGUAGE = "ro"
PREPARATION_SHARE = .35


class TranscriptionError(ProviderError):
    """Kept under its historical name, re-exported by `transcription.py`."""


def _value(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def parse_response(response: Any, chunk: AudioChunk) -> list[TranscriptSegment]:
    items = _value(response, "segments")
    if items is None and hasattr(response, "model_dump"): items = response.model_dump().get("segments")
    if not items: raise TranscriptionError(f"The API response for fragment {chunk.index} is empty.")
    result: list[TranscriptSegment] = []
    for item in items:
        speaker, start, end, text = (_value(item, x) for x in ("speaker", "start", "end", "text"))
        if None in (speaker, start, end, text): continue
        local_start, local_end = float(start), float(end); original = str(speaker)
        result.append(TranscriptSegment(chunk.index, chunk.start, original,
            f"Fragment {chunk.index:02d} · Speaker {original}", local_start, local_end,
            chunk.start + local_start, chunk.start + local_end, str(text), None,
            chunk.index > 1 and local_start < chunk.overlap_seconds))
    if not result: raise TranscriptionError(f"Fragment {chunk.index} contains no usable speech.")
    return result


def _friendly(exc: Exception) -> str:
    status, text = getattr(exc, "status_code", None), str(exc).lower()
    if status == 401 or "api key" in text: return "The API key is invalid or lacks the required permissions."
    if status == 413 or "too large" in text: return "The audio fragment is too large for the API. Lower the fragment limit."
    if status == 429 or "quota" in text or "billing" in text or "credit" in text:
        return "The API credit or quota is exhausted. ChatGPT and API billing are separate."
    if isinstance(exc, APITimeoutError): return "The OpenAI request timed out. Try again."
    if isinstance(exc, APIConnectionError): return "Could not connect to OpenAI."
    return f"The OpenAI request failed: {exc}"


def transcribe_chunk(api_key: str, chunk: AudioChunk, attempts: int = 3,
                     language: str = DEFAULT_LANGUAGE) -> list[TranscriptSegment]:
    client = OpenAI(api_key=api_key)
    for attempt in range(1, attempts + 1):
        try:
            with Path(chunk.path).open("rb") as audio:
                response = client.audio.transcriptions.create(model=MODEL, file=audio,
                    response_format="diarized_json", chunking_strategy="auto", language=language or DEFAULT_LANGUAGE)
            return parse_response(response, chunk)
        except AuthenticationError as exc: raise TranscriptionError(_friendly(exc)) from exc
        except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
            if attempt == attempts: raise TranscriptionError(_friendly(exc)) from exc
            time.sleep(2 ** (attempt - 1))
        except APIStatusError as exc:
            if exc.status_code >= 500 and attempt < attempts: time.sleep(2 ** (attempt - 1)); continue
            raise TranscriptionError(_friendly(exc)) from exc
        except TranscriptionError: raise
        except Exception as exc: raise TranscriptionError(_friendly(exc)) from exc
    raise TranscriptionError("The transcription could not be completed.")


def transcribe_chunks(api_key: str, chunks: list[AudioChunk], progress: Callable[[int, int, str], None] | None = None,
                      cancelled: CancelCallback | None = None,
                      chunk_transcriber: Callable[..., list[TranscriptSegment]] | None = None) -> list[TranscriptSegment]:
    # `chunk_transcriber` is the injection point used both by the `transcription.py` shim
    # (for monkeypatching in tests) and to fix the language asked of the provider.
    transcriber = chunk_transcriber or transcribe_chunk
    result: list[TranscriptSegment] = []
    for pos, chunk in enumerate(chunks, 1):
        if cancelled and cancelled(): raise TranscriptionError("The transcription was cancelled before the next fragment.")
        if progress: progress(pos, len(chunks), f"Transcribing fragment {pos} of {len(chunks)}.")
        result.extend(transcriber(api_key, chunk))
    return sorted(result, key=lambda s: (s.absolute_start, s.absolute_end, s.chunk_index))


class OpenAIDiarizeProvider(TranscriptionProvider):
    """The historical path: fragment locally with FFmpeg, then one request per fragment."""

    info = ProviderInfo(
        key="openai",
        label="OpenAI · per-fragment diarization",
        model=MODEL,
        key_label="OpenAI API key",
        missing_key="Enter the OpenAI API key.",
        transfer_note="The original is never modified. Only temporary fragments are sent to OpenAI.",
        capabilities=ProviderCapabilities(supports_diarization=True, supports_word_timestamps=False,
                                          supports_confidence=False, global_speakers=False),
        note="The key is never saved. ChatGPT and API billing are separate.",
        uploads_whole_file=False)

    def __init__(self, api_key: str, output_dir: str, media_tools: MediaToolPaths | None = None,
                 safe_chunk_mb: float = 23.0, fallback_bitrate_kbps: int = 48, overlap_seconds: float = 0.0,
                 force_encode: bool = False, cancelled: CancelCallback | None = None) -> None:
        self.api_key = api_key; self.output_dir = output_dir; self.media_tools = media_tools
        self.safe_chunk_mb = safe_chunk_mb; self.fallback_bitrate_kbps = fallback_bitrate_kbps
        self.overlap_seconds = overlap_seconds; self.force_encode = force_encode; self.cancelled = cancelled
        # The fragments created during the run; the controller takes them for project state.
        self.chunks: list[AudioChunk] = []

    def transcribe(self, audio_path: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        # `expected_speakers` is not accepted by gpt-4o-transcribe-diarize; purely informational.
        if not self.api_key.strip(): raise TranscriptionError(self.info.missing_key)
        info = probe_audio(audio_path, self.media_tools)

        def preparation(current: int, total: int, message: str) -> None:
            emit_progress(progress_cb, message, PREPARATION_SHARE * current / max(total, 1))

        self.chunks = create_chunks(info, self.output_dir, self.overlap_seconds, preparation, self.safe_chunk_mb,
                                    self.fallback_bitrate_kbps, self.force_encode, self.cancelled, self.media_tools)
        emit_progress(progress_cb, f"Created {len(self.chunks)} temporary fragments.", None)
        emit_progress(progress_cb, "Audio preparation finished.", PREPARATION_SHARE)

        def api(current: int, total: int, message: str) -> None:
            emit_progress(progress_cb, message, PREPARATION_SHARE + (1 - PREPARATION_SHARE) * (current - 1) / max(total, 1))

        transcriber = partial(transcribe_chunk, language=language) if language and language != DEFAULT_LANGUAGE else None
        return transcribe_chunks(self.api_key, self.chunks, api, self.cancelled, transcriber)
