"""Taking one step back.

Every correction on the review screen writes straight into the transcript and, shortly
after, into the project file. That is the right default — nothing is ever lost to a
forgotten save — but on its own it left no way out of a mistake. Rename two speakers to the
same thing, or press Ctrl+Enter over a sentence you meant to keep, and the previous value
was simply gone: the document had already been rewritten.

A step is recorded as *what it takes to put things back*, not as a description of what
changed. Restoring is therefore exact and never has to work out what happened in between.
The closure captures the old value at the moment of the change, so it cannot go stale.

There is no redo. One level of regret is the one people reach for under pressure, and a
redo stack that has to survive the next edit is a second thing to get wrong.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator

# Deep enough to cover a session's worth of small corrections, bounded so a long review
# cannot hold every intermediate state of a large transcript in memory.
LIMIT = 60


@dataclass(frozen=True)
class Step:
    """One reversible change: what to call it, and how to put it back."""
    label: str
    restore: Callable[[], None]


class History:
    """A bounded stack of steps, newest last."""

    def __init__(self, limit: int = LIMIT) -> None:
        self._steps: list[Step] = []
        self._limit = limit
        self._collecting: list[Step] | None = None

    def __len__(self) -> int:
        return len(self._steps)

    @property
    def pending(self) -> str | None:
        """What the next undo would put back, for the button's tooltip. None when empty."""
        return self._steps[-1].label if self._steps else None

    def record(self, label: str, restore: Callable[[], None]) -> None:
        """Remember how to reverse a change that is about to happen."""
        step = Step(label, restore)
        if self._collecting is not None:
            self._collecting.append(step)
            return
        self._steps.append(step)
        if len(self._steps) > self._limit:
            del self._steps[0]

    @contextmanager
    def group(self, label: str) -> Iterator[None]:
        """Collapse everything recorded inside into a single step.

        Ctrl+Enter saves the correction, marks the turn reviewed and opens the next one.
        That is one act to the person doing it, so it has to be one press of undo — not
        three, with the transcript in a half-restored state in between.

        A group opened inside a group is ignored rather than nested: the outermost act is
        the one a person would name, and nesting only makes the label wrong.
        """
        if self._collecting is not None:
            yield
            return
        self._collecting = []
        try:
            yield
        finally:
            collected, self._collecting = self._collecting, None
        if not collected:
            return

        def restore_all(steps: list[Step] = collected) -> None:
            # Backwards: the last change is the first to be put back, so intermediate
            # values are never restored on top of each other in the wrong order.
            for step in reversed(steps):
                step.restore()

        self.record(label, restore_all)

    def undo(self) -> str | None:
        """Put the most recent change back. Returns its label, or None when there is none."""
        if not self._steps:
            return None
        step = self._steps.pop()
        step.restore()
        return step.label

    def clear(self) -> None:
        """Forget everything. Opening another project makes these steps meaningless — they
        close over segments that are no longer in the transcript."""
        self._steps.clear()
        self._collecting = None
