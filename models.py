from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, field
from typing import Any


def _tolerant(cls: type, data: dict[str, Any], fallbacks: dict[str, Any]) -> dict[str, Any]:
    """Păstrează doar câmpurile reale, ignoră cheile necunoscute și completează obligatoriile lipsă.

    Astfel, proiectele `.transcript.json` salvate cu versiuni mai vechi sau mai noi ale aplicației
    se deschid în continuare, indiferent ce chei conțin.
    """
    declared = cls.__dataclass_fields__
    clean = {key: value for key, value in data.items() if key in declared}
    for name, spec in declared.items():
        if name in clean: continue
        if spec.default is MISSING and spec.default_factory is MISSING: clean[name] = fallbacks[name]
    return clean


@dataclass
class MediaToolPaths:
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    source_type: str = "unavailable"
    version: str = ""
    is_valid: bool = False


@dataclass
class AudioInfo:
    path: str
    filename: str
    size_bytes: int
    duration: float
    codec: str
    sample_rate: int
    channels: int
    bitrate: int | None = None

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioInfo": return cls(**data)


@dataclass
class AudioChunk:
    index: int
    path: str
    start: float
    duration: float
    size_bytes: int
    method: str
    overlap_seconds: float = 0.0

    def to_dict(self, include_path: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not include_path: data.pop("path", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioChunk": return cls(**_tolerant(cls, data, _CHUNK_FALLBACKS))


@dataclass
class Word:
    """Un cuvânt cu marcaje temporale, oferit de furnizorii care raportează la acest nivel."""
    start: float
    end: float
    text: str
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Word": return cls(**_tolerant(cls, data, _WORD_FALLBACKS))


@dataclass
class TranscriptSegment:
    chunk_index: int
    chunk_start_offset: float
    original_speaker: str
    speaker_id: str
    local_start: float
    local_end: float
    absolute_start: float
    absolute_end: float
    original_text: str
    corrected_text: str | None = None
    in_overlap: bool = False
    words: list[Word] = field(default_factory=list)
    confidence: float | None = None
    # Review progress. Defaulted, so a project saved before this existed simply loads with
    # nothing checked rather than refusing to open.
    checked: bool = False

    @property
    def text(self) -> str: return self.corrected_text if self.corrected_text is not None else self.original_text

    @property
    def speaker(self) -> str: return self.speaker_id

    @property
    def start(self) -> float: return self.absolute_start

    @property
    def end(self) -> float: return self.absolute_end

    def to_dict(self, final_speaker: str | None = None) -> dict[str, Any]:
        data = asdict(self)
        data["final_speaker"] = final_speaker or self.speaker_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptSegment":
        # `final_speaker` și orice altă cheie necunoscută sunt eliminate de `_tolerant`.
        clean = _tolerant(cls, data, _SEGMENT_FALLBACKS)
        clean["words"] = [item if isinstance(item, Word) else Word.from_dict(item)
                          for item in clean.get("words") or [] if isinstance(item, (Word, dict))]
        return cls(**clean)


_WORD_FALLBACKS: dict[str, Any] = {"start": 0.0, "end": 0.0, "text": ""}
_CHUNK_FALLBACKS: dict[str, Any] = {"index": 0, "path": "", "start": 0.0, "duration": 0.0,
                                    "size_bytes": 0, "method": ""}
_SEGMENT_FALLBACKS: dict[str, Any] = {"chunk_index": 0, "chunk_start_offset": 0.0, "original_speaker": "",
                                      "speaker_id": "", "local_start": 0.0, "local_end": 0.0,
                                      "absolute_start": 0.0, "absolute_end": 0.0, "original_text": ""}
