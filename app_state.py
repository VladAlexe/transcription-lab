from __future__ import annotations
import tempfile
from dataclasses import dataclass, field
from models import AudioChunk, AudioInfo, MediaToolPaths, TranscriptSegment
from providers import DEFAULT_PROVIDER, ProviderCapabilities, provider_capabilities

# One key per provider; every one of them lives only in the memory of this process.
KEY_FIELDS = {"gladia": "gladia_api_key", "soniox": "soniox_api_key", "deepgram": "deepgram_api_key",
              "openai": "api_key", "compatible": "compatible_api_key"}


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
    provider: str = DEFAULT_PROVIDER
    language: str = "ro"
    expected_speakers: int = 0  # 0 lets the provider work the number out for itself
    # Above this size the recording is re-encoded to a compact copy before being uploaded.
    # A single multi-hundred-megabyte request is what stalls on an ordinary connection.
    upload_compress_above_mb: float = 64.0
    upload_bitrate_kbps: int = 32
    # Pausing steps back this far so resuming catches the start of the word (0 disables).
    auto_rewind_enabled: bool = True
    auto_rewind_seconds: float = 1.5


@dataclass
class ExportMetadata:
    title: str = ""          # empty means the default title from strings.py
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
    deepgram_api_key: str = field(default="", repr=False)
    gladia_api_key: str = field(default="", repr=False)
    soniox_api_key: str = field(default="", repr=False)
    compatible_api_key: str = field(default="", repr=False)
    # The generic endpoint's address and model: in memory, never saved and never exported.
    compatible_base_url: str = field(default="", repr=False)
    compatible_model: str = field(default="", repr=False)
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
    # Optional sub-range of the recording; None on both means the whole file.
    range_start: float | None = None
    range_end: float | None = None
    # Where the researcher had got to. Saved with the project, so reopening resumes there.
    last_reviewed_index: int | None = None
    show_only_unchecked: bool = False
    # Run provenance, saved into the project for reproducibility.
    transcription_provider: str = ""
    transcription_model: str = ""
    run_capabilities: ProviderCapabilities | None = None
    # The recording a saved project refers to, and whether it still needs reconnecting.
    audio_path: str = ""
    audio_filename: str = ""
    audio_bytes: int = 0
    audio_missing: bool = False
    audio_banner_dismissed: bool = False
    # The last replace-all, kept so it can be undone in one step.
    last_replacement: object | None = None
    activity_log: list[str] = field(default_factory=list)
    technical_details: list[str] = field(default_factory=list)
    temporary_directory: tempfile.TemporaryDirectory[str] | None = field(default=None, repr=False)
    preview_cache: list[str] = field(default_factory=list)
    media_tools: MediaToolPaths = field(default_factory=MediaToolPaths)
    first_run: bool = True
    project_saved: bool = False

    @property
    def active_api_key(self) -> str:
        """The selected provider's key. Keys live only in the memory of this process."""
        return str(getattr(self, KEY_FIELDS.get(self.settings.provider, "api_key"), ""))

    def set_active_api_key(self, value: str) -> None:
        setattr(self, KEY_FIELDS.get(self.settings.provider, "api_key"), value)

    @property
    def effective_capabilities(self) -> ProviderCapabilities:
        """What the last run actually delivered; before there is one, what the selected
        provider declares it can do."""
        return self.run_capabilities or provider_capabilities(self.settings.provider)

    def cleanup_temporary(self) -> None:
        if self.temporary_directory:
            self.temporary_directory.cleanup(); self.temporary_directory = None
        self.preview_cache.clear(); self.generated_chunks.clear()

    def reset(self) -> None:
        tools=self.media_tools; first_run=self.first_run
        self.cleanup_temporary(); fresh = AppState(settings=self.settings,media_tools=tools,first_run=first_run)
        self.__dict__.update(fresh.__dict__)
