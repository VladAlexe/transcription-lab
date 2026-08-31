from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError
from models import AudioChunk, TranscriptSegment

MODEL = "gpt-4o-transcribe-diarize"
class TranscriptionError(RuntimeError): pass


def _value(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def parse_response(response: Any, chunk: AudioChunk) -> list[TranscriptSegment]:
    items = _value(response, "segments")
    if items is None and hasattr(response, "model_dump"): items = response.model_dump().get("segments")
    if not items: raise TranscriptionError(f"Răspunsul API pentru fragmentul {chunk.index} este gol.")
    result: list[TranscriptSegment] = []
    for item in items:
        speaker, start, end, text = (_value(item, x) for x in ("speaker", "start", "end", "text"))
        if None in (speaker, start, end, text): continue
        local_start, local_end = float(start), float(end); original = str(speaker)
        result.append(TranscriptSegment(chunk.index, chunk.start, original,
            f"Fragment {chunk.index:02d} · Speaker {original}", local_start, local_end,
            chunk.start + local_start, chunk.start + local_end, str(text), None,
            chunk.index > 1 and local_start < chunk.overlap_seconds))
    if not result: raise TranscriptionError(f"Fragmentul {chunk.index} nu conține intervenții valide.")
    return result


def _friendly(exc: Exception) -> str:
    status, text = getattr(exc, "status_code", None), str(exc).lower()
    if status == 401 or "api key" in text: return "Cheia API este invalidă sau nu are permisiunile necesare."
    if status == 413 or "too large" in text: return "Fragmentul audio este prea mare pentru API. Reduceți limita sigură."
    if status == 429 or "quota" in text or "billing" in text or "credit" in text:
        return "Creditul sau cota API este insuficientă. Facturarea ChatGPT și API sunt separate."
    if isinstance(exc, APITimeoutError): return "Cererea OpenAI a expirat. Încercați din nou."
    if isinstance(exc, APIConnectionError): return "Conexiunea la OpenAI nu a putut fi realizată."
    return f"Cererea OpenAI a eșuat: {exc}"


def transcribe_chunk(api_key: str, chunk: AudioChunk, attempts: int = 3) -> list[TranscriptSegment]:
    client = OpenAI(api_key=api_key)
    for attempt in range(1, attempts + 1):
        try:
            with Path(chunk.path).open("rb") as audio:
                response = client.audio.transcriptions.create(model=MODEL, file=audio,
                    response_format="diarized_json", chunking_strategy="auto", language="ro")
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
    raise TranscriptionError("Transcrierea nu a putut fi finalizată.")


def transcribe_chunks(api_key: str, chunks: list[AudioChunk], progress: Callable[[int, int, str], None] | None = None,
                      cancelled: Callable[[], bool] | None = None) -> list[TranscriptSegment]:
    result: list[TranscriptSegment] = []
    for pos, chunk in enumerate(chunks, 1):
        if cancelled and cancelled(): raise TranscriptionError("Transcrierea a fost anulată înaintea următorului fragment.")
        if progress: progress(pos, len(chunks), f"Se transcrie fragmentul {pos} din {len(chunks)}.")
        result.extend(transcribe_chunk(api_key, chunk))
    return sorted(result, key=lambda s: (s.absolute_start, s.absolute_end, s.chunk_index))
