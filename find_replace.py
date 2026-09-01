"""Find and replace across every turn of the open transcript.

Text only. Timestamps, speaker ids and word timings are never touched — a replacement
rewrites `corrected_text` and nothing else, so playback, seek and export stay aligned with
the audio exactly as before.

Everything here is pure so the matching rules can be tested without a window.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from models import TranscriptSegment


@dataclass(frozen=True)
class Options:
    case_sensitive: bool = False
    whole_word: bool = False


@dataclass
class Replacement:
    """One replace-all, and everything needed to undo it in a single step."""
    term: str
    replacement: str
    matches: int = 0
    # (segment index, the corrected_text it had before). None means it had no correction.
    changes: list[tuple[int, str | None]] = field(default_factory=list)

    @property
    def turns(self) -> int: return len(self.changes)

    @property
    def applied(self) -> bool: return bool(self.changes)


def build_pattern(term: str, options: Options) -> re.Pattern | None:
    """A literal search, escaped. Returns None for an empty term rather than matching all."""
    if not term:
        return None
    body = re.escape(term)
    if options.whole_word:
        # \b only means anything next to a word character; a term like "..." would never match.
        if term[:1].isalnum() or term[:1] == "_":
            body = r"\b" + body
        if term[-1:].isalnum() or term[-1:] == "_":
            body = body + r"\b"
    return re.compile(body, 0 if options.case_sensitive else re.IGNORECASE)


def count_matches(segments: list[TranscriptSegment], term: str, options: Options) -> int:
    """How many replacements a replace-all would make, for the live counter."""
    pattern = build_pattern(term, options)
    if pattern is None:
        return 0
    return sum(len(pattern.findall(item.text or "")) for item in segments)


def matching_turns(segments: list[TranscriptSegment], term: str, options: Options) -> list[int]:
    pattern = build_pattern(term, options)
    if pattern is None:
        return []
    return [index for index, item in enumerate(segments) if pattern.search(item.text or "")]


def replace_all(segments: list[TranscriptSegment], term: str, replacement: str,
                options: Options) -> Replacement:
    """Apply across every turn and return the record that undoes it."""
    record = Replacement(term, replacement)
    pattern = build_pattern(term, options)
    if pattern is None:
        return record
    for index, item in enumerate(segments):
        current = item.text or ""
        updated, count = pattern.subn(replacement, current)
        if not count or updated == current:
            continue
        record.matches += count
        record.changes.append((index, item.corrected_text))
        # Matching correct_segment: text identical to the original is not a correction.
        item.corrected_text = None if updated == item.original_text else updated
    return record


def undo(segments: list[TranscriptSegment], record: Replacement) -> int:
    """Put back exactly what was there before. Returns how many turns were restored."""
    restored = 0
    for index, previous in record.changes:
        if 0 <= index < len(segments):
            segments[index].corrected_text = previous
            restored += 1
    return restored
