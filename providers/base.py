"""The interface every transcription provider implements.

A provider is handed a whole recording and returns turns whose speaker labels are stable
across the ENTIRE file. A provider that fragments the recording internally stays
responsible for stitching its own results back together.

Each provider declares what it can do, and the interface reads that to disable features
that would need data which does not exist, and to tell the researcher honestly what to
expect before they spend anything.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Callable, Iterable

from models import TranscriptSegment, Word

# (message for the activity log, progress 0..1, or None when the stage cannot be measured)
ProgressCallback = Callable[[str, float | None], None]

# Signals a cancellation asked for by the user; providers check it between stages.
CancelCallback = Callable[[], bool]


class ProviderError(RuntimeError):
    """An error already phrased for the researcher, raised by any provider.

    `transient` marks the failures worth retrying — a dropped connection, a gateway blip, a
    rate limit. A two-hour job must not die because one packet went missing.
    """

    def __init__(self, message: str, transient: bool = False) -> None:
        super().__init__(message)
        self.transient = transient


@dataclass(frozen=True)
class ProviderCapabilities:
    """What a provider can actually deliver. The interface adapts itself to these."""

    supports_diarization: bool = False
    supports_word_timestamps: bool = False
    supports_confidence: bool = False
    global_speakers: bool = False

    def summary(self) -> str:
        if not self.supports_diarization:
            return "This provider returns no speaker labels; you will name and split speakers manually."
        parts = ["global speakers" if self.global_speakers else "speakers separated per fragment"]
        if self.supports_word_timestamps: parts.append("word timestamps")
        if self.supports_confidence: parts.append("confidence scores")
        complete = self.global_speakers and self.supports_word_timestamps and self.supports_confidence
        return f"{'Full' if complete else 'Partial'}: {', '.join(parts)}."


def feature_state(capabilities: ProviderCapabilities) -> dict[str, bool]:
    """Turn capabilities into the interface features that are live.

    One place decides, so no screen has to reinterpret each flag on its own.
    """
    return {
        # Naming speakers only means anything if the provider actually returns labels.
        "speaker_naming": capabilities.supports_diarization,
        # Reconciling across fragments is only needed when the labels are NOT global.
        "speaker_reconciliation": capabilities.supports_diarization and not capabilities.global_speakers,
        "manual_speaker_split": not capabilities.supports_diarization,
        "word_timestamps": capabilities.supports_word_timestamps,
        "confidence_display": capabilities.supports_confidence,
    }


@dataclass(frozen=True)
class ProviderInfo:
    key: str
    label: str
    model: str
    key_label: str
    missing_key: str
    transfer_note: str
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    note: str = ""
    # The generic provider needs both the endpoint address and the model name.
    needs_endpoint: bool = False
    # True when the provider receives the whole recording in one upload, which is the case
    # that benefits from a compact copy. The OpenAI path fragments and re-encodes locally.
    uploads_whole_file: bool = True


class TranscriptionProvider(ABC):
    """The contract each provider implements."""

    info: ClassVar[ProviderInfo]

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "ro", expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        """Transcribe the whole recording at `audio_path`.

        The segments returned must carry:
          * a GLOBAL `speaker_id`, consistent for the length of the file, if the provider
            diarizes at all;
          * `words` with per-word timings, when the provider offers them;
          * `confidence` per turn, when the provider offers it.

        `expected_speakers` is how many participants the researcher expects; `0` means
        "let the provider decide". A provider that does not accept it ignores it rather
        than failing.
        """

    def capabilities(self) -> ProviderCapabilities:
        """What the last run actually delivered.

        By default this is what was declared; a provider whose response varies (the generic
        endpoint) narrows it once it has seen what the server returned.
        """
        return self.info.capabilities


def format_elapsed(seconds: float) -> str:
    """mm:ss for short waits, h:mm:ss once a job has been running for over an hour."""
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def emit_progress(progress_cb: ProgressCallback | None, message: str, fraction: float | None) -> None:
    if progress_cb:
        progress_cb(message, fraction)


def speaker_label(number: Any) -> str:
    """A global, readable label for a speaker the provider numbered."""
    try: return f"Speaker {int(number) + 1}"
    except (TypeError, ValueError): return f"Speaker {number}"


def whole_file_segment(number: Any, text: str, start: float, end: float,
                       words: Iterable[Word] | None = None,
                       confidence: float | None = None) -> TranscriptSegment:
    """Build a turn for the providers that process the whole file.

    With no fragmenting, `chunk_index` and the offset are both 0: local times and absolute
    times are the same thing.
    """
    return TranscriptSegment(0, 0.0, str(number), speaker_label(number), start, end, start, end,
                             text, None, False, list(words or []), confidence)


# A turn ends at a speaker change, or at a silence longer than this. Providers that report
# short utterances would otherwise shatter a conversation into one-word bubbles.
MAX_TURN_GAP = 1.2
# Timestamps arrive as floats, so a gap of exactly MAX_TURN_GAP can compute to 1.2000000000000002.
# Splitting on that would be an arbitrary coin flip between two identical recordings.
_GAP_EPSILON = 1e-6


def group_by_speaker(items: Iterable[tuple[Any, Word]],
                     max_gap: float = MAX_TURN_GAP) -> list[TranscriptSegment]:
    """Group consecutive words by the same speaker into a single turn.

    Used by the providers that report word or token level detail with no ready-made turns.
    It breaks when the speaker changes, or on a pause longer than `max_gap`.
    """
    segments: list[TranscriptSegment] = []
    current: list[Word] = []
    number: Any = None
    for speaker, word in items:
        if number is None: number = speaker
        gap = word.start - current[-1].end if current else 0.0
        if current and (speaker != number or gap > max_gap + _GAP_EPSILON):
            built = _from_words(number, current)
            if built: segments.append(built)
            current = []; number = speaker
        current.append(word)
    if current:
        built = _from_words(number if number is not None else 0, current)
        if built: segments.append(built)
    return segments


def merge_turns(segments: list[TranscriptSegment],
                max_gap: float = MAX_TURN_GAP) -> list[TranscriptSegment]:
    """Join consecutive turns by the same speaker into one.

    Providers that return one utterance per short phrase leave the transcript shattered into
    one-word turns. A turn is closed only by a speaker change or by a silence longer than
    `max_gap`, so `absolute_start` / `absolute_end` and the word list of the merged turn still
    describe the real span — click-to-seek and export stay aligned.

    Not applied to providers whose segments carry per-fragment identity (their labels are only
    valid inside one fragment) nor to providers that return a single default speaker (merging
    would collapse the whole transcript into one turn).
    """
    if not segments: return []
    merged: list[TranscriptSegment] = []
    group: list[TranscriptSegment] = []

    def flush() -> None:
        if not group: return
        first, last = group[0], group[-1]
        if len(group) == 1:
            merged.append(first); return
        text = " ".join(item.original_text.strip() for item in group if item.original_text.strip()).strip()
        words: list[Word] = []
        for item in group: words.extend(item.words)
        # Weight each confidence by how long its segment lasted, so a two-second sentence
        # counts for more than a half-second interjection.
        weights = [(item.confidence, max(0.0, item.absolute_end - item.absolute_start))
                   for item in group if item.confidence is not None]
        total = sum(weight for _, weight in weights)
        confidence = (sum(value * weight for value, weight in weights) / total if total
                      else (sum(value for value, _ in weights) / len(weights) if weights else None))
        merged.append(whole_file_segment(first.original_speaker, text, first.absolute_start,
                                         last.absolute_end, words, confidence))

    for item in segments:
        if group:
            previous = group[-1]
            gap = item.absolute_start - previous.absolute_end
            if item.speaker_id != previous.speaker_id or gap > max_gap + _GAP_EPSILON:
                flush(); group = []
        group.append(item)
    flush()
    return merged


def _from_words(number: Any, words: list[Word]) -> TranscriptSegment | None:
    text = " ".join(word.text.strip() for word in words if word.text.strip()).strip()
    if not text: return None
    scores = [word.confidence for word in words if word.confidence is not None]
    confidence = sum(scores) / len(scores) if scores else None
    return whole_file_segment(number, text, words[0].start, words[-1].end, words, confidence)
