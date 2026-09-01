"""Shim de compatibilitate: logica OpenAI a fost mutată în `providers/openai_diarize.py`.

Modulul este păstrat pentru ca `document_export.py`, `views/transcription_view.py` și testele
existente să continue să importe `MODEL`, `parse_response`, `transcribe_chunk` și
`transcribe_chunks` de aici, fără modificări.
"""
from __future__ import annotations

from typing import Callable

from models import AudioChunk, TranscriptSegment
from providers import openai_diarize as _openai
from providers.openai_diarize import MODEL, TranscriptionError, parse_response, transcribe_chunk

__all__ = ["MODEL", "TranscriptionError", "parse_response", "transcribe_chunk", "transcribe_chunks"]


def transcribe_chunks(api_key: str, chunks: list[AudioChunk], progress: Callable[[int, int, str], None] | None = None,
                      cancelled: Callable[[], bool] | None = None) -> list[TranscriptSegment]:
    # `transcribe_chunk` este citit din spațiul de nume al ACESTUI modul la fiecare apel, astfel
    # încât înlocuirea lui (`transcription.transcribe_chunk = ...`) să rămână eficace în teste.
    return _openai.transcribe_chunks(api_key, chunks, progress, cancelled, transcribe_chunk)
