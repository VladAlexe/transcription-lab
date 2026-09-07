"""What a field holds after someone types into it.

Flet only sends a control's new value to Python when that control has a change listener.
Without one the Python object keeps the value it was built with, nothing raises, and the
code that reads `.value` later quietly uses the text from before. It has caused the same bug
three times here: a correction saved with Ctrl+Enter that kept the previous sentence, a
speaker name applied by clicking away that did nothing at all, and every field on the
Settings screen writing its starting value back when Save was pressed.

These tests type into the controls the way the client does — by firing `on_change` with the
new text — and then read them the way the application does.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flet as ft
import layout_audit
import strings as s
from app_state import AppState
from components.inputs import syncing
from components.speaker_panel import speaker_panel
from views import settings_view

noop = lambda *a, **k: None


def type_into(control, text) -> None:
    """What the client does: send the new value, then fire the change event."""
    control.value = text
    handler = getattr(control, "on_change", None)
    assert handler is not None, f"{control} has no change listener, so its value is never sent"
    handler(SimpleNamespace(control=control, data=text))


def leave(control) -> None:
    """Move the caret somewhere else. Flet's blur event carries no value with it."""
    handler = getattr(control, "on_blur", None)
    if handler is not None:
        handler(SimpleNamespace(control=control))


class SyncingTests(unittest.TestCase):
    def test_a_synced_control_keeps_what_was_typed(self) -> None:
        box = syncing(ft.TextField(value="before"))
        type_into(box, "after")
        self.assertEqual(box.value, "after")

    def test_it_keeps_a_handler_the_control_already_had(self) -> None:
        seen: list[str] = []
        box = ft.TextField(value="")
        box.on_change = lambda e: seen.append("original")
        syncing(box, then=lambda e: seen.append("extra"))
        type_into(box, "x")
        self.assertEqual(seen, ["original", "extra"])

    def test_it_returns_the_control_so_it_can_wrap_in_place(self) -> None:
        box = ft.TextField(value="")
        self.assertIs(syncing(box), box)


class SpeakerNameTests(unittest.TestCase):
    """The one the researcher hit: renamed a speaker ten times and it did not take."""

    def panel(self, applied: list):
        return speaker_panel({"SPEAKER_00": (34, 724.0), "SPEAKER_01": (12, 180.0)},
                             {"SPEAKER_00": "Speaker 1", "SPEAKER_01": "Speaker 2"},
                             {"SPEAKER_00": 0, "SPEAKER_01": 1},
                             lambda key, value: applied.append((key, value)),
                             True, {}, noop, noop)

    def name_field(self, panel, row: int = 0):
        return panel.controls[row].content.controls[0].controls[1]

    def test_pressing_enter_applies_the_typed_name(self) -> None:
        applied: list = []
        field = self.name_field(self.panel(applied))
        type_into(field, "Ana")
        field.on_submit(SimpleNamespace(control=field))
        self.assertEqual(applied, [("SPEAKER_00", "Ana")])

    def test_clicking_away_applies_it_too(self) -> None:
        """This is what failed. The blur event carries no value, so without a change
        listener the field was compared against itself, found unchanged, and dropped."""
        applied: list = []
        field = self.name_field(self.panel(applied))
        type_into(field, "Ana")
        leave(field)
        self.assertEqual(applied, [("SPEAKER_00", "Ana")])

    def test_leaving_a_name_untouched_still_rewrites_nothing(self) -> None:
        applied: list = []
        field = self.name_field(self.panel(applied))
        leave(field)
        self.assertEqual(applied, [])

    def test_the_tick_applies_what_is_in_the_box(self) -> None:
        applied: list = []
        panel = self.panel(applied)
        field = self.name_field(panel)
        tick = [c for c in panel.controls[0].content.controls[1].controls
                if isinstance(c, ft.IconButton)]
        self.assertEqual(len(tick), 1, "the visible way to apply a name")
        type_into(field, "Ana")
        tick[0].on_click(None)
        self.assertEqual(applied, [("SPEAKER_00", "Ana")])

    def test_the_name_field_reports_its_changes(self) -> None:
        self.assertIsNotNone(self.name_field(self.panel([])).on_change)


class SettingsValueTests(unittest.TestCase):
    """Save reads thirteen controls at once. All of them have to be current."""

    def screen(self, sent: dict):
        state = AppState()
        return state, settings_view.build(state, lambda *a: sent.update(args=a),
                                          noop, noop, noop)

    def inputs(self, screen) -> list:
        return [c for c in layout_audit.walk(screen)
                if isinstance(c, (ft.TextField, ft.Dropdown, ft.Switch))]

    def test_every_input_on_the_screen_reports_its_changes(self) -> None:
        """Any one that does not would hand Save the value the screen opened with."""
        _, screen = self.screen({})
        controls = self.inputs(screen)
        self.assertTrue(controls)
        for control in controls:
            with self.subTest(control=type(control).__name__, hint=getattr(control, "hint_text", "")):
                self.assertIsNotNone(control.on_change)

    def test_a_highlight_name_typed_in_reaches_save(self) -> None:
        """What the researcher was doing when the screen fell over, now checked end to end."""
        sent: dict = {}
        _, screen = self.screen(sent)
        boxes = [c for c in self.inputs(screen)
                 if getattr(c, "hint_text", "") == s.SETTINGS_HIGHLIGHT_SLOT.format(number="1")]
        self.assertEqual(len(boxes), 1)
        type_into(boxes[0], "Contested")
        button = [c for c in layout_audit.walk(screen)
                  if getattr(c, "content", None) == s.SETTINGS_SAVE][0]
        button.on_click(None)
        self.assertIn("Contested", sent["args"][14])

    def test_a_reviewer_name_typed_in_reaches_save(self) -> None:
        sent: dict = {}
        _, screen = self.screen(sent)
        box = [c for c in self.inputs(screen)
               if getattr(c, "hint_text", "") == s.SETTINGS_REVIEWER_HINT][0]
        type_into(box, "Vlad Alexe")
        button = [c for c in layout_audit.walk(screen)
                  if getattr(c, "content", None) == s.SETTINGS_SAVE][0]
        button.on_click(None)
        self.assertEqual(sent["args"][15], "Vlad Alexe")

    def test_a_language_chosen_reaches_save(self) -> None:
        sent: dict = {}
        _, screen = self.screen(sent)
        selects = [c for c in self.inputs(screen) if isinstance(c, ft.Dropdown)]
        language = [c for c in selects
                    if any(o.key == "nl" for o in (c.options or []))][0]
        type_into(language, "nl")
        button = [c for c in layout_audit.walk(screen)
                  if getattr(c, "content", None) == s.SETTINGS_SAVE][0]
        button.on_click(None)
        self.assertEqual(sent["args"][7], "nl")


class RowIsolationTests(unittest.TestCase):
    """A handler built in a loop must belong to its own row.

    A lambda that names `commit` looks it up when it fires, and by then the loop has moved
    on — so it is the LAST row's commit. Clicking away from the first speaker renamed the
    last one, with the first speaker's text. That is how two speakers ended up with the same
    name, and why Enter worked while clicking away did not: `on_submit=commit` binds the
    object, a lambda that mentions it does not.
    """

    def panel(self, applied: list):
        return speaker_panel(
            {"A": (5, 10.0), "B": (5, 10.0), "C": (5, 10.0)},
            {"A": "First", "B": "Second", "C": "Third"}, {"A": 0, "B": 1, "C": 2},
            lambda key, value: applied.append((key, value)), True, {}, noop, noop)

    def row(self, panel, index: int):
        block = panel.controls[index].content
        field = block.controls[0].controls[1]
        tick = [c for c in block.controls[1].controls if isinstance(c, ft.IconButton)][0]
        return field, tick

    def test_clicking_away_renames_the_speaker_you_were_editing(self) -> None:
        for index, key in enumerate("ABC"):
            with self.subTest(row=key):
                applied: list = []
                field, _ = self.row(self.panel(applied), index)
                type_into(field, "Renamed")
                leave(field)
                self.assertEqual(applied, [(key, "Renamed")])

    def test_the_tick_renames_the_speaker_it_sits_beside(self) -> None:
        for index, key in enumerate("ABC"):
            with self.subTest(row=key):
                applied: list = []
                field, tick = self.row(self.panel(applied), index)
                type_into(field, "Renamed")
                tick.on_click(None)
                self.assertEqual(applied, [(key, "Renamed")])

    def test_enter_renames_the_speaker_it_belongs_to(self) -> None:
        for index, key in enumerate("ABC"):
            with self.subTest(row=key):
                applied: list = []
                field, _ = self.row(self.panel(applied), index)
                type_into(field, "Renamed")
                field.on_submit(SimpleNamespace(control=field))
                self.assertEqual(applied, [(key, "Renamed")])

    def test_two_speakers_cannot_be_renamed_by_one_edit(self) -> None:
        """The exact accident: one field left, two names changed."""
        applied: list = []
        panel = self.panel(applied)
        field, _ = self.row(panel, 0)
        type_into(field, "Ana")
        leave(field)
        self.assertEqual(len({key for key, _ in applied}), 1)


if __name__ == "__main__":
    unittest.main()
