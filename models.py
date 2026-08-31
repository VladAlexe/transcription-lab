from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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
    def from_dict(cls, data: dict[str, Any]) -> "AudioChunk": return cls(**data)


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
        clean = dict(data)
        clean.pop("final_speaker", None)
        return cls(**clean)
