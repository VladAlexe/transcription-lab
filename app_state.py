from __future__ import annotations
import tempfile
from dataclasses import dataclass, field
from models import AudioChunk, AudioInfo, MediaToolPaths, TranscriptSegment


@dataclass
class PreparationSettings:
    preserve_original: bool = True
    safe_chunk_mb: float = 23.0
    fallback_bitrate_kbps: int = 48
    overlap_seconds: float = 0.0
    retain_review_audio: bool = True
    include_source_path_json: bool = False
    diagnostic_logging: bool = False
    appearance: str = "light"
    user_media_tool_path: str = ""


@dataclass
class ExportMetadata:
    title: str = "Transcriere interviu de grup"
    project_id: str = ""
    interview_date: str = ""
    notes: str = ""
    include_timestamps: bool = True
    include_notice: bool = True
    include_original_labels: bool = True


@dataclass
class AppState:
    selected_file_path: str | None = None
    selected_file_metadata: AudioInfo | None = None
    api_key: str = field(default="", repr=False)
    settings: PreparationSettings = field(default_factory=PreparationSettings)
    generated_chunks: list[AudioChunk] = field(default_factory=list)
    transcription_progress: float = 0.0
    transcript_segments: list[TranscriptSegment] = field(default_factory=list)
    chunk_metadata: list[dict] = field(default_factory=list)
    speaker_mapping: dict[str, str] = field(default_factory=dict)
    export_paths: dict[str, str] = field(default_factory=dict)
    export_metadata: ExportMetadata = field(default_factory=ExportMetadata)
    current_workflow_step: int = 0
    error_state: str | None = None
    cancellation_flag: bool = False
    processing: bool = False
    dirty: bool = False
    project_path: str | None = None
    generated_at: str = ""
    activity_log: list[str] = field(default_factory=list)
    technical_details: list[str] = field(default_factory=list)
    temporary_directory: tempfile.TemporaryDirectory[str] | None = field(default=None, repr=False)
    preview_cache: list[str] = field(default_factory=list)
    media_tools: MediaToolPaths = field(default_factory=MediaToolPaths)
    first_run: bool = True
    project_saved: bool = False

    def cleanup_temporary(self) -> None:
        if self.temporary_directory:
            self.temporary_directory.cleanup(); self.temporary_directory = None
        self.preview_cache.clear(); self.generated_chunks.clear()

    def reset(self) -> None:
        tools=self.media_tools; first_run=self.first_run
        self.cleanup_temporary(); fresh = AppState(settings=self.settings,media_tools=tools,first_run=first_run)
        self.__dict__.update(fresh.__dict__)
