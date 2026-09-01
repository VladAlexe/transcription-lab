"""Follow the audio through the transcript, and the small text tools that go with it.

Every function here is pure: given segments and a position, say what should be highlighted,
what is worth a second listen, and what the text becomes. Capability differences are handled
by degrading, never by failing — a provider that gave no word timings still gets a highlight,
just at turn level.
"""
from __future__ import annotations

from dataclasses import dataclass

from models import TranscriptSegment

# Below this, a word is worth a second listen. Providers report 0..1; anything without a
# score is simply never marked.
LOW_CONFIDENCE = 0.65


@dataclass(frozen=True)
class Position:
    """Where playback is, in transcript terms."""
    turn: int | None = None
    word: int | None = None

    @property
    def known(self) -> bool: return self.turn is not None


@dataclass(frozen=True)
class Mark:
    """A place worth revisiting: a low-confidence word, or a whole turn when words are absent."""
    turn: int
    word: int | None
    start: float
    confidence: float

    @property
    def word_level(self) -> bool: return self.word is not None


def locate(segments: list[TranscriptSegment], seconds: float) -> Position:
    """The turn playing at `seconds`, and the word inside it when the provider timed words.

    Between turns the previous turn stays highlighted: during a pause the reader's eye should
    not be thrown back to nothing.
    """
    if not segments:
        return Position()
    turn: int | None = None
    for index, item in enumerate(segments):
        if item.absolute_start <= seconds:
            turn = index
        else:
            break
    if turn is None:
        # Before the first turn: nothing is playing yet.
        return Position()
    return Position(turn, _locate_word(segments[turn], seconds))


def _locate_word(segment: TranscriptSegment, seconds: float) -> int | None:
    """None when the provider gave no word timings — the caller falls back to the turn."""
    words = getattr(segment, "words", None) or []
    if not words:
        return None
    found: int | None = None
    for index, word in enumerate(words):
        if word.start <= seconds:
            found = index
        else:
            break
    if found is None:
        return 0 if seconds >= segment.absolute_start else None
    return found


def low_confidence_marks(segments: list[TranscriptSegment],
                         threshold: float = LOW_CONFIDENCE) -> list[Mark]:
    """Everything below the threshold, word by word where possible, otherwise by turn."""
    marks: list[Mark] = []
    for index, segment in enumerate(segments):
        words = getattr(segment, "words", None) or []
        scored = [(position, word) for position, word in enumerate(words) if word.confidence is not None]
        if scored:
            marks.extend(Mark(index, position, word.start, float(word.confidence))
                         for position, word in scored if word.confidence < threshold)
            continue
        if segment.confidence is not None and segment.confidence < threshold:
            marks.append(Mark(index, None, segment.absolute_start, float(segment.confidence)))
    return marks


def next_mark(marks: list[Mark], after: float) -> Mark | None:
    """The next place to check after the current position, wrapping to the first."""
    if not marks:
        return None
    for mark in marks:
        if mark.start > after + 1e-6:
            return mark
    return marks[0]


def rewind_target(position_ms: int, rewind_seconds: float) -> int:
    """Where pausing should leave the cursor, so resuming catches the start of the word."""
    return max(0, int(position_ms) - int(round(max(0.0, rewind_seconds) * 1000)))


def format_stamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


def insert_timestamp(text: str, cursor: int | None, seconds: float) -> tuple[str, int]:
    """Put a citation stamp at the cursor and return the text plus the new cursor.

    Plain text in `corrected_text`, so it saves, exports and re-opens like anything the
    researcher typed. A cursor of None means the end, which is where an unfocused field sits.
    """
    body = text or ""
    position = len(body) if cursor is None else max(0, min(int(cursor), len(body)))
    stamp = format_stamp(seconds)
    before, after = body[:position], body[position:]
    # Keep it readable without inventing punctuation: one space unless there already is one.
    if before and not before.endswith((" ", "\n")):
        stamp = " " + stamp
    if after and not after.startswith((" ", "\n")):
        stamp = stamp + " "
    return before + stamp + after, position + len(stamp)
