"""Compatibility shim: the OpenAI logic moved to `providers/openai_diarize.py`.

The module is kept so that `document_export.py`, `views/transcription_view.py` and the
existing tests can go on importing `MODEL`, `parse_response`, `transcribe_chunk` and
`transcribe_chunks` from here, unchanged.
"""
from __future__ import annotations

from typing import Callable

from models import AudioChunk, TranscriptSegment
from providers import openai_diarize as _openai
from providers.openai_diarize import MODEL, TranscriptionError, parse_response, transcribe_chunk

__all__ = ["MODEL", "TranscriptionError", "parse_response", "transcribe_chunk", "transcribe_chunks"]


def transcribe_chunks(api_key: str, chunks: list[AudioChunk], progress: Callable[[int, int, str], None] | None = None,
                      cancelled: Callable[[], bool] | None = None) -> list[TranscriptSegment]:
    # `transcribe_chunk` is read from THIS module's namespace on every call, so that
    # replacing it (`transcription.transcribe_chunk = ...`) keeps working in tests.
    return _openai.transcribe_chunks(api_key, chunks, progress, cancelled, transcribe_chunk)
