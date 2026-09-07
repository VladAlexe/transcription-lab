"""Marking part of a turn: a comment, bold, or one of three highlights.

A note on a whole turn answers "this turn needs attention". A researcher quoting an
interview needs the other thing: *this phrase*, right here. So an annotation is a character
range inside the turn's text, and every one of the three kinds survives into the Word file
as the thing a reader expects — a real highlight, real bold, and a comment anchored to the
phrase rather than to the paragraph.

Everything here is pure. Given text and ranges it returns runs; nothing knows what a control
is, which is what lets the same function drive the on-screen preview and the exporter, so
the two cannot disagree about what was marked.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

BOLD = "bold"
HIGHLIGHT = "highlight"
COMMENT = "comment"
KINDS = (BOLD, HIGHLIGHT, COMMENT)

# Three slots, named by the researcher in Settings. Three because a colour code people can
# hold in their head is three or four long; a palette of fifteen is a palette, not a code.
SLOTS = ("1", "2", "3")

# The three highlighter colours, taken from the application's own palette: Amber Earth,
# Smoky Rose and Muted Teal. Word's highlighter has fifteen fixed colours and none of these
# is among them, so all three are written as run shading — a `w:shd` fill, which takes any
# RGB and renders as the same coloured band behind the words. The cost is that Word's "find
# highlighted text" does not see them; the gain is the colours the researcher chose from,
# consistently, rather than three approximations from a stock set.
#
# The second value is the ink. Smoky Rose is dark enough that near-black on it is 3.1:1 —
# unreadable — so it takes white; the other two take the palette's Carbon Black at 5:1 and
# better. Screen and document use the same pairing.
HIGHLIGHTS: dict[str, tuple[str, str]] = {
    "1": ("E8871E", "23231A"),   # Amber Earth
    "2": ("945D5E", "FFFFFF"),   # Smoky Rose
    "3": ("759588", "23231A"),   # Muted Teal
}


def ink(slot: str) -> str:
    """The text colour that stays readable on a slot's fill, as `#RRGGBB`."""
    return "#" + HIGHLIGHTS.get(slot, HIGHLIGHTS["1"])[1]


def colour(slot: str) -> str:
    """The RGB for a slot, as `#RRGGBB`."""
    return "#" + HIGHLIGHTS.get(slot, HIGHLIGHTS["1"])[0]


@dataclass
class Annotation:
    """One marked range. `quote` is what it was anchored to, so an edit can re-find it."""
    start: int
    end: int
    kind: str = HIGHLIGHT
    slot: str = "1"
    note: str = ""
    quote: str = ""

    @property
    def valid(self) -> bool:
        return self.kind in KINDS and self.end > self.start >= 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        known = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__}
        known.setdefault("start", 0)
        known.setdefault("end", 0)
        return cls(**known)


def normalise(start: int, end: int, text: str) -> tuple[int, int]:
    """A selection dragged right to left arrives backwards; clamp it to the text as well."""
    low, high = sorted((int(start), int(end)))
    return max(0, min(low, len(text))), max(0, min(high, len(text)))


def add(existing: list[Annotation], start: int, end: int, text: str, kind: str = HIGHLIGHT,
        slot: str = "1", note: str = "") -> list[Annotation]:
    """Mark a range, replacing any earlier mark of the same kind that it overlaps.

    Two highlights over the same words would be one colour on top of another with no way to
    tell which won; marking again simply re-marks. Kinds are independent, so a phrase can be
    bold and highlighted and carry a comment at once.
    """
    low, high = normalise(start, end, text)
    if high <= low or kind not in KINDS:
        return list(existing)
    kept = [a for a in existing
            if a.kind != kind or a.end <= low or a.start >= high]
    kept.append(Annotation(low, high, kind, slot, note, text[low:high]))
    return sorted(kept, key=lambda a: (a.start, a.end, a.kind))


def remove(existing: list[Annotation], start: int, end: int, text: str,
           kind: str | None = None) -> list[Annotation]:
    """Clear marks overlapping a range. With no kind, clears every kind."""
    low, high = normalise(start, end, text)
    return [a for a in existing
            if (kind is not None and a.kind != kind) or a.end <= low or a.start >= high]


def at(existing: list[Annotation], position: int) -> list[Annotation]:
    return [a for a in existing if a.start <= position < a.end]


@dataclass
class Run:
    """A stretch of text over which the formatting does not change."""
    text: str
    bold: bool = False
    slot: str = ""                       # highlight slot, empty when not highlighted
    comments: list[str] = field(default_factory=list)

    @property
    def marked(self) -> bool:
        return bool(self.bold or self.slot or self.comments)


def runs(text: str, existing: list[Annotation]) -> list[Run]:
    """Split the text where any annotation starts or ends.

    One function for the preview on screen and for the Word exporter, so what a researcher
    sees before saving is the same division the document is built from.
    """
    marks = [a for a in (existing or []) if a.valid and a.start < len(text)]
    if not text:
        return []
    if not marks:
        return [Run(text)]
    edges = {0, len(text)}
    for mark in marks:
        edges.add(max(0, min(mark.start, len(text))))
        edges.add(max(0, min(mark.end, len(text))))
    ordered = sorted(edges)
    result: list[Run] = []
    for left, right in zip(ordered, ordered[1:]):
        if right <= left:
            continue
        covering = [a for a in marks if a.start <= left and a.end >= right]
        run = Run(text[left:right],
                  bold=any(a.kind == BOLD for a in covering),
                  slot=next((a.slot for a in covering if a.kind == HIGHLIGHT), ""),
                  comments=[a.note for a in covering if a.kind == COMMENT and a.note])
        # Merge with the previous run when nothing about the formatting changed.
        if result and (result[-1].bold, result[-1].slot, result[-1].comments) == \
                      (run.bold, run.slot, run.comments):
            result[-1].text += run.text
        else:
            result.append(run)
    return result


def reanchor(existing: list[Annotation], old: str, new: str) -> list[Annotation]:
    """Follow the marks through an edit of the text.

    Character offsets stop meaning anything the moment a word is inserted before them, so
    each mark is re-found by the text it was anchored to. One that no longer appears is
    dropped rather than left pointing at whatever now occupies those positions — a comment
    silently re-anchored to the wrong phrase is worse than a comment that went away.
    """
    if old == new:
        return list(existing)
    kept: list[Annotation] = []
    # Claimed positions are tracked per kind. Bold, a highlight and a comment routinely sit
    # on the same phrase, so one shared list would let the first of them claim the only
    # occurrence and send the other two hunting for a second one that does not exist.
    used: dict[str, list[tuple[int, int]]] = {kind: [] for kind in KINDS}
    for mark in sorted(existing, key=lambda a: a.start):
        quote = mark.quote or old[mark.start:mark.end]
        if not quote:
            continue
        taken = used.setdefault(mark.kind, [])
        search = 0
        while True:
            found = new.find(quote, search)
            if found < 0:
                break
            if all(found >= b or found + len(quote) <= a for a, b in taken):
                taken.append((found, found + len(quote)))
                kept.append(Annotation(found, found + len(quote), mark.kind, mark.slot,
                                       mark.note, quote))
                break
            search = found + 1
    return sorted(kept, key=lambda a: (a.start, a.end, a.kind))
