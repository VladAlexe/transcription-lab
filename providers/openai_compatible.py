"""Furnizor generic pentru orice endpoint compatibil OpenAI.

Cercetătorul indică adresa de bază, numele modelului și cheia proprie; aplicația trimite
`POST {base_url}/audio/transcriptions` cu `response_format=verbose_json`.

Acest furnizor NU diarizează: tot textul primește o singură etichetă implicită de vorbitor,
iar delimitarea și denumirea vorbitorilor rămân în sarcina cercetătorului. Răspunsul poate fi
oricât de sărac — dacă serverul întoarce doar text simplu, se emite câte o intervenție per
paragraf, ca restul aplicației să funcționeze mai departe.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models import TranscriptSegment, Word
from providers.base import (CancelCallback, ProgressCallback, ProviderCapabilities, ProviderError, ProviderInfo,
                            TranscriptionProvider, emit_progress, whole_file_segment)
from providers.http import UPLOAD_TIMEOUT, upload_file

SERVICE = "the configured endpoint"
DEFAULT_MODEL = "whisper-1"
DEFAULT_LANGUAGE = "ro"
UPLOAD_SHARE = .85
# Fără diarizare, toate intervențiile aparțin aceluiași vorbitor implicit.
DEFAULT_SPEAKER = 0


def endpoint(base_url: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned: raise ProviderError("Enter the base URL of the OpenAI-compatible endpoint.")
    if cleaned.endswith("/audio/transcriptions"): return cleaned
    return f"{cleaned}/audio/transcriptions"


def _number(raw: Any, default: float = 0.0) -> float:
    try: return float(raw)
    except (TypeError, ValueError): return default


def _word(raw: dict[str, Any]) -> Word:
    start = _number(raw.get("start")); end = _number(raw.get("end"), start)
    return Word(start, end, str(raw.get("word") or raw.get("text") or ""), None)


def _paragraphs(text: str) -> list[str]:
    blocks = [block.strip() for block in text.replace("\r\n", "\n").split("\n\n")]
    cleaned = [block for block in blocks if block]
    if cleaned: return cleaned
    stripped = text.strip()
    return [stripped] if stripped else []


def parse_response(payload: dict[str, Any]) -> tuple[list[TranscriptSegment], bool]:
    """Returnează intervențiile și dacă răspunsul chiar conținea marcaje temporale."""
    raw_segments = payload.get("segments")
    if isinstance(raw_segments, list) and raw_segments:
        segments: list[TranscriptSegment] = []
        for raw in raw_segments:
            if not isinstance(raw, dict): continue
            text = str(raw.get("text") or "").strip()
            if not text: continue
            start = _number(raw.get("start")); end = _number(raw.get("end"), start)
            words = [_word(item) for item in raw.get("words") or [] if isinstance(item, dict)]
            segments.append(whole_file_segment(DEFAULT_SPEAKER, text, start, end, words, None))
        if segments:
            # Ordinea este păstrată de sortarea stabilă chiar și când toate marcajele sunt egale.
            return sorted(segments, key=lambda s: (s.absolute_start, s.absolute_end)), True

    text = str(payload.get("text") or "").strip()
    blocks = _paragraphs(text)
    if not blocks: raise ProviderError("The endpoint returned no transcribed text.")
    # Fără marcaje: intervalele rămân zero, iar interfața anunță lipsa lor.
    return [whole_file_segment(DEFAULT_SPEAKER, block, 0.0, 0.0, [], None) for block in blocks], False


class OpenAICompatibleProvider(TranscriptionProvider):
    """Orice server care expune `/audio/transcriptions` în stil OpenAI."""

    info = ProviderInfo(
        key="compatible",
        label="OpenAI-compatible endpoint (your own)",
        model=DEFAULT_MODEL,
        key_label="Endpoint API key",
        missing_key="Enter the API key for the configured endpoint.",
        transfer_note="The original is never modified. A complete copy of the recording is sent to the address you configured.",
        capabilities=ProviderCapabilities(supports_diarization=False, supports_word_timestamps=True,
                                          supports_confidence=False, global_speakers=False),
        note="The address, model, and key stay in process memory only; they are never saved or exported.",
        needs_endpoint=True)

    def __init__(self, api_key: str, base_url: str = "", model: str = DEFAULT_MODEL,
                 cancelled: CancelCallback | None = None) -> None:
        self.api_key = api_key; self.base_url = base_url; self.model = (model or DEFAULT_MODEL).strip()
        self.cancelled = cancelled
        # Se restrânge după prima rulare, dacă serverul nu a returnat marcaje temporale.
        self._observed = self.info.capabilities

    def capabilities(self) -> ProviderCapabilities:
        return self._observed

    def transcribe(self, audio_path: str, language: str = DEFAULT_LANGUAGE, expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        # `expected_speakers` nu are efect: endpoint-ul generic nu diarizează.
        if not self.api_key.strip(): raise ProviderError(self.info.missing_key)
        path = Path(audio_path)
        if not path.is_file(): raise ProviderError("The selected recording is no longer available.")
        url = endpoint(self.base_url)

        fields = {"model": self.model, "response_format": "verbose_json"}
        if language: fields["language"] = language
        # Synchronous like Deepgram: upload and transcription share one request, so it needs
        # the long timeout, and upload_file already retries a dropped connection.
        payload = upload_file(SERVICE, url, {"Authorization": f"Bearer {self.api_key}"}, path, "file", fields,
                              progress_cb, self.cancelled, "Uploading the recording to the endpoint", UPLOAD_SHARE,
                              "The endpoint is processing the recording.", timeout=UPLOAD_TIMEOUT)

        segments, timestamped = parse_response(payload)
        self._observed = ProviderCapabilities(supports_diarization=False, supports_word_timestamps=timestamped,
                                              supports_confidence=False, global_speakers=False)
        emit_progress(progress_cb, "Transcript without diarization: one default speaker." if not timestamped
                      else "Transcript with timestamps, without speaker labels.", .98)
        return segments
