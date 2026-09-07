"""Keeping a control's value in step with what was typed into it.

Flet only sends a control's new value to Python when that control has a change listener. A
`TextField` without one keeps, on the Python side, whatever value it was built with — so
code that reads `.value` later reads the value from before the person typed. Nothing raises.
The field looks right on screen and the wrong text is used.

This has now caused the same bug three times in this application: a correction saved with
Ctrl+Enter that kept the previous sentence, a speaker name applied by clicking away that
silently did nothing, and every field on the Settings screen writing back its starting value
when Save was pressed. The shape is always identical, which is why it is one function now
rather than a line remembered at each call site.

`syncing` is what every input in the application is built through. Attach it once and
`.value` is true at all times, whichever way the field is left — Enter, a button, or the
caret simply moving somewhere else.
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar

Control = TypeVar("Control")


def syncing(control: Control, then: Callable[[Any], None] | None = None) -> Control:
    """Make `control.value` follow what is typed, and return the control.

    Any handler already on the control is kept and called after the value is written, so
    this can be applied to an input that already reports changes somewhere.
    """
    existing = getattr(control, "on_change", None)

    def changed(event: Any) -> None:
        # The event carries the new value; the control object does not have it yet unless
        # Flet applied it first. Writing it here makes both true whatever the version does.
        value = getattr(getattr(event, "control", None), "value", None)
        if value is None:
            value = getattr(event, "data", None)
        if value is not None:
            control.value = value
        if existing is not None:
            existing(event)
        if then is not None:
            then(event)

    control.on_change = changed
    return control
