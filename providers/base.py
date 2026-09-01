"""Interfața comună a furnizorilor de transcriere.

Un furnizor primește o înregistrare întreagă și returnează intervenții ale căror
etichete de vorbitor sunt stabile pe TOT fișierul. Furnizorii care fragmentează
intern înregistrarea rămân responsabili de reunificarea rezultatelor.

Fiecare furnizor își declară capabilitățile, iar interfața le citește pentru a dezactiva
funcțiile care ar avea nevoie de date inexistente și pentru a spune cinstit utilizatorului
la ce să se aștepte.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Callable, Iterable

from models import TranscriptSegment, Word

# (mesaj pentru jurnalul de activitate, progres 0..1 sau None când etapa nu poate fi cuantificată)
ProgressCallback = Callable[[str, float | None], None]

# Semnalează anularea cerută de utilizator; furnizorii o consultă între etape.
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
    """Ce poate livra efectiv un furnizor. Interfața se adaptează după aceste valori."""

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
    """Traduce capabilitățile în funcții active ale interfeței.

    Punct unic de decizie, ca ecranele să nu reinterpreteze fiecare steag pe cont propriu.
    """
    return {
        # Denumirea vorbitorilor are sens doar dacă furnizorul chiar returnează etichete.
        "speaker_naming": capabilities.supports_diarization,
        # Reconcilierea între fragmente este necesară doar când etichetele NU sunt globale.
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
    # Furnizorul generic are nevoie și de adresa endpoint-ului și de numele modelului.
    needs_endpoint: bool = False
    # True when the provider receives the whole recording in one upload, which is the case
    # that benefits from a compact copy. The OpenAI path fragments and re-encodes locally.
    uploads_whole_file: bool = True


class TranscriptionProvider(ABC):
    """Contractul pe care îl implementează fiecare furnizor."""

    info: ClassVar[ProviderInfo]

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "ro", expected_speakers: int = 0,
                   progress_cb: ProgressCallback | None = None) -> list[TranscriptSegment]:
        """Transcrie întreaga înregistrare de la `audio_path`.

        Segmentele returnate trebuie să poarte:
          * `speaker_id` GLOBAL, consistent pe toată durata fișierului, dacă furnizorul diarizează;
          * `words` cu marcaje temporale pentru fiecare cuvânt, când furnizorul le oferă;
          * `confidence` la nivel de intervenție, când furnizorul îl oferă.

        `expected_speakers` este numărul de participanți anticipat de cercetător;
        `0` înseamnă „lasă furnizorul să decidă". Furnizorii care nu îl acceptă îl
        ignoră fără să eșueze.
        """

    def capabilities(self) -> ProviderCapabilities:
        """Capabilitățile efective ale ultimei rulări.

        Implicit sunt cele declarate; furnizorii al căror răspuns variază (endpoint generic)
        le restrâng după ce văd ce a returnat serverul.
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
    """Etichetă globală, lizibilă, pentru un vorbitor numerotat de furnizor."""
    try: return f"Speaker {int(number) + 1}"
    except (TypeError, ValueError): return f"Speaker {number}"


def whole_file_segment(number: Any, text: str, start: float, end: float,
                       words: Iterable[Word] | None = None,
                       confidence: float | None = None) -> TranscriptSegment:
    """Construiește o intervenție pentru furnizorii care procesează fișierul întreg.

    Fără fragmentare, `chunk_index` este 0 și offsetul 0: timpii locali coincid cu cei absoluți.
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
    """Grupează cuvinte consecutive ale aceluiași vorbitor într-o singură intervenție.

    Folosit de furnizorii care raportează la nivel de cuvânt/token, fără intervenții gata formate.
    Se rupe la schimbarea vorbitorului sau la o pauză mai lungă decât `max_gap`.
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
    """Reunește intervențiile consecutive ale aceluiași vorbitor într-o singură replică.

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
