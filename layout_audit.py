"""Walks a built control tree and reports declared widths.

Flutter measures intrinsic width on its side, which a headless process cannot see. What it
CAN check is every width this code declares: if any of those exceeds the column that holds
them, the overflow is ours and is provable without a screen.
"""
from __future__ import annotations

from typing import Any, Iterator

import flet as ft

# Attributes that can hold nested controls in the parts of Flet this app uses.
_CHILD_ATTRIBUTES = ("content", "controls", "actions", "leading", "trailing", "title", "subtitle")


def walk(control: Any) -> Iterator[ft.Control]:
    if not isinstance(control, ft.Control):
        return
    yield control
    for name in _CHILD_ATTRIBUTES:
        value = getattr(control, name, None)
        if isinstance(value, (list, tuple)):
            for item in value:
                yield from walk(item)
        else:
            yield from walk(value)


def declared_widths(control: Any, skip_root: bool = True) -> list[tuple[str, float]]:
    """Every (control name, declared width) pair inside the tree, widest first."""
    found: list[tuple[str, float]] = []
    for index, item in enumerate(walk(control)):
        if skip_root and index == 0:
            continue
        width = getattr(item, "width", None)
        if isinstance(width, (int, float)):
            found.append((type(item).__name__, float(width)))
    return sorted(found, key=lambda pair: pair[1], reverse=True)


def widest(control: Any, skip_root: bool = True) -> tuple[str, float]:
    found = declared_widths(control, skip_root)
    return found[0] if found else ("none", 0.0)


def wrapped_rows_with_expanding_children(control: Any) -> list[str]:
    """Rows that both wrap and hold an expanding child — a combination that renders nothing.

    Flet turns `Row(wrap=True)` into a Flutter `Wrap`, and a `Wrap` cannot lay out a flexible
    child: the child is given no width and disappears. This is how the API key field vanished
    from the Transcription screen, so it is checked automatically rather than by eye.
    """
    offenders: list[str] = []
    for item in walk(control):
        if not isinstance(item, ft.Row) or not getattr(item, "wrap", False):
            continue
        for child in item.controls or []:
            if getattr(child, "expand", None):
                offenders.append(f"{type(item).__name__}(wrap=True) holds "
                                 f"{type(child).__name__}(expand={child.expand})")
    return offenders


def find(control: Any, predicate) -> list[ft.Control]:
    return [item for item in walk(control) if predicate(item)]


def report(label: str, content_width: float, control: Any) -> str:
    name, width = widest(control)
    verdict = "fits" if width <= content_width else "OVERFLOW"
    return (f"[content:{label}] column={content_width:.0f} widest_declared_child={width:.0f} "
            f"({name}) -> {verdict}")
