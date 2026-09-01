"""Optional transcription range: parsing, validation, and timestamp re-anchoring.

The researcher may transcribe only part of a recording. The clip itself is cut by
`audio_processing.extract_range`; everything here is pure and testable.

The rule that matters for research integrity: a transcript of minutes 12–35 must report
positions in the ORIGINAL recording, so `shift_segments` re-anchors every absolute time
by the range start once the provider has returned clip-relative results.
"""
from __future__ import annotations

from dataclasses import dataclass

import strings as s
from models import TranscriptSegment


class TimeRangeError(ValueError):
    """Message already written for the interface."""


@dataclass(frozen=True)
class TimeRange:
    start: float
    end: float

    @property
    def duration(self) -> float: return max(0.0, self.end - self.start)


def parse_timecode(text: str) -> float | None:
    """`mm:ss`, `hh:mm:ss`, or bare seconds. Empty input means "not set"."""
    cleaned = (text or "").strip()
    if not cleaned: return None
    parts = cleaned.split(":")
    if len(parts) > 3: raise TimeRangeError(s.RANGE_ERROR_FORMAT)
    try:
        values = [float(part.strip()) for part in parts]
    except ValueError:
        raise TimeRangeError(s.RANGE_ERROR_FORMAT) from None
    if any(value < 0 for value in values): raise TimeRangeError(s.RANGE_ERROR_FORMAT)
    if len(values) > 1 and any(value >= 60 for value in values[1:]):
        raise TimeRangeError(s.RANGE_ERROR_FORMAT)
    total = 0.0
    for value in values: total = total * 60 + value
    return total


def format_timecode(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def resolve(start_text: str, end_text: str, duration: float) -> TimeRange | None:
    """Validate the two inputs against the probed duration.

    Returns None when the whole file is meant, or raises `TimeRangeError` with a message
    ready to display.
    """
    start = parse_timecode(start_text)
    end = parse_timecode(end_text)
    if start is None and end is None: return None
    total = max(0.0, float(duration or 0))
    begin = 0.0 if start is None else start
    finish = total if end is None else end
    # One second of slack: the displayed duration is rounded, so typing it back must not fail.
    if total and (begin > total or finish > total + 1.0):
        raise TimeRangeError(s.RANGE_ERROR_BOUNDS.format(total=format_timecode(total)))
    if total: finish = min(finish, total)
    if finish <= begin: raise TimeRangeError(s.RANGE_ERROR_ORDER)
    if finish - begin < 1.0: raise TimeRangeError(s.RANGE_ERROR_EMPTY)
    if begin <= 0 and (end is None or abs(finish - total) < .05): return None
    return TimeRange(begin, finish)


def describe(selection: TimeRange | None, duration: float) -> str:
    if selection is None:
        return s.RANGE_FULL.format(duration=format_timecode(duration))
    return s.RANGE_PARTIAL.format(start=format_timecode(selection.start), end=format_timecode(selection.end),
                                  duration=format_timecode(selection.duration), total=format_timecode(duration))


def shift_segments(segments: list[TranscriptSegment], offset: float) -> list[TranscriptSegment]:
    """Re-anchor clip-relative results onto the original recording's timeline."""
    if not offset: return segments
    for item in segments:
        item.absolute_start += offset
        item.absolute_end += offset
        item.chunk_start_offset += offset
        for word in item.words:
            word.start += offset
            word.end += offset
    return segments
