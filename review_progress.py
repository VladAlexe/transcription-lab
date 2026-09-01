"""How far through the transcript the researcher has got.

Reviewing a two-hour group interview is a long, interruptible job. Everything here exists to
answer three questions without the researcher having to hold them in their head: how much is
done, what is the next thing that is not, and where was I when I stopped.

All of it is pure. Given the segments and a position it returns numbers and indices; nothing
in this module knows what a control is.
"""
from __future__ import annotations

from dataclasses import dataclass

from models import TranscriptSegment


@dataclass(frozen=True)
class Progress:
    checked: int
    total: int

    @property
    def fraction(self) -> float:
        """0.0 to 1.0, for the bar. An empty transcript is not 100% reviewed."""
        return (self.checked / self.total) if self.total else 0.0

    @property
    def percent(self) -> int:
        """Rounded for display. Never rounds up to 100 while anything is left unchecked."""
        if not self.total:
            return 0
        value = int(round(self.fraction * 100))
        if value >= 100 and self.checked < self.total:
            return 99
        if value <= 0 and self.checked:
            return 1
        return value

    @property
    def complete(self) -> bool: return bool(self.total) and self.checked >= self.total


def progress(segments: list[TranscriptSegment]) -> Progress:
    return Progress(sum(1 for item in segments if item.checked), len(segments))


def next_unchecked(segments: list[TranscriptSegment], after: int | None = None) -> int | None:
    """The next turn still to review, wrapping once. None when everything is checked.

    Wrapping matters: a researcher who skipped a hard turn early on should be brought back
    to it at the end rather than told they are finished.
    """
    total = len(segments)
    if not total:
        return None
    start = 0 if after is None else after + 1
    for offset in range(total):
        index = (start + offset) % total
        if not segments[index].checked:
            return index
    return None


def visible_order(segments: list[TranscriptSegment], only_unchecked: bool = False) -> list[int]:
    """Which turns the list shows, as indices into the full transcript.

    Indices rather than segments, so a filtered list still selects, seeks, edits and saves
    against the real position in the interview.
    """
    if not only_unchecked:
        return list(range(len(segments)))
    return [index for index, item in enumerate(segments) if not item.checked]


def resume_index(segments: list[TranscriptSegment], stored: int | None = None) -> int | None:
    """Where "Resume" goes: the saved position, or the first thing still unreviewed.

    A stored index that no longer exists — the transcript was re-run, or turns were merged —
    falls back rather than throwing the researcher somewhere arbitrary.
    """
    if not segments:
        return None
    if stored is not None and 0 <= stored < len(segments):
        return stored
    return next_unchecked(segments, None)


def set_checked(segments: list[TranscriptSegment], index: int, value: bool) -> bool:
    """Returns whether anything actually changed, so callers can skip a needless save."""
    if not (0 <= index < len(segments)) or segments[index].checked == value:
        return False
    segments[index].checked = value
    return True
