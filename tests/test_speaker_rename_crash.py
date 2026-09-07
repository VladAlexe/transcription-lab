"""Applying a speaker name, which crashed the released application.

    TypeError: '>=' not supported between instances of 'str' and 'int'
      main.py, in _refresh_speaker:  if index>=len(state.transcript_segments)

The row registry is keyed by transcript index, and `_refresh_speaker` walks those keys
comparing each to the segment count. The transcript list was writing its own handles —
`listing`, `page_offset`, `page_order` — into that same dictionary, so the first string key
it reached ended the click. Two tests: the registry stays clean, and the walk survives even
if it ever does not.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import flet as ft
from app_state import AppState
from components.transcript_list import transcript_list
from models import TranscriptSegment
from views import speakers_view

noop = lambda *a, **k: None


def state(count: int = 6) -> AppState:
    made = AppState()
    made.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i % 2}", f"SPEAKER_{i % 2}", i * 9, i * 9 + 7,
                          i * 9, i * 9 + 7, f"Turn {i}.") for i in range(count)]
    made.speaker_mapping = {"SPEAKER_0": "SPEAKER_0", "SPEAKER_1": "SPEAKER_1"}
    return made


class RegistryTests(unittest.TestCase):
    def built(self) -> dict:
        refs: dict = {}
        speakers_view.build(state(), noop, noop, noop, 1, noop, refs, 960)
        return refs

    def test_the_review_screen_keys_its_rows_by_transcript_index_only(self) -> None:
        refs = self.built()
        self.assertTrue(refs["rows"])
        self.assertEqual([k for k in refs["rows"] if not isinstance(k, int)], [])

    def test_the_list_handles_are_where_main_actually_looks_for_them(self) -> None:
        """`scroll_to_turn` reads these at the top level. While they were nested inside
        `rows`, it silently found nothing and the transcript never followed playback."""
        refs = self.built()
        self.assertIsNotNone(refs.get("listing"))
        self.assertEqual(refs.get("page_offset"), 0)
        self.assertIsInstance(refs.get("page_order"), list)


class RenameTests(unittest.TestCase):
    """The exact click that crashed, driven through the real handler."""

    def app(self, rows: dict) -> SimpleNamespace:
        import main
        from app_controller import AppController
        controller = AppController(state())
        stand_in = SimpleNamespace(
            controller=controller, refs={"rows": rows, "speakers": {}},
            _safe_update=lambda *a: True, render=noop,
            _refresh_inspector_if_showing=noop, _refresh_status=noop)
        # Bind the two real methods under test to the stand-in.
        stand_in.visible_rows = lambda: main.DesktopApp.visible_rows(stand_in)
        stand_in._refresh_speaker = lambda speaker: main.DesktopApp._refresh_speaker(stand_in, speaker)
        return stand_in

    def rows_from_a_real_screen(self) -> dict:
        refs: dict = {}
        speakers_view.build(state(), noop, noop, noop, 1, noop, refs, 960)
        return refs["rows"]

    def test_applying_a_name_no_longer_raises(self) -> None:
        import main
        app = self.app(self.rows_from_a_real_screen())
        main.DesktopApp.map_speaker(app, "SPEAKER_0", "Moderator")
        self.assertEqual(app.controller.state.speaker_mapping["SPEAKER_0"], "Moderator")

    def test_the_rows_of_that_speaker_pick_up_the_new_name(self) -> None:
        import main
        rows = self.rows_from_a_real_screen()
        app = self.app(rows)
        main.DesktopApp.map_speaker(app, "SPEAKER_1", "Ana Popescu")
        renamed = [parts["speaker"].value for index, parts in rows.items()
                   if isinstance(index, int) and index % 2 == 1]
        self.assertTrue(renamed)
        self.assertEqual(set(renamed), {"Ana Popescu"})

    def test_a_stray_string_key_can_no_longer_end_the_click(self) -> None:
        """Belt and braces: even if something writes a named handle in there again."""
        import main
        rows = self.rows_from_a_real_screen()
        rows["listing"] = ft.Container()
        rows["page_offset"] = 0
        app = self.app(rows)
        main.DesktopApp.map_speaker(app, "SPEAKER_0", "Moderator")
        self.assertEqual(app.controller.state.speaker_mapping["SPEAKER_0"], "Moderator")


class SaveButtonTests(unittest.TestCase):
    """Saving the project has to be reachable at any moment, from any screen."""

    def bar(self, segments: int = 3, on_save=noop) -> dict:
        from components.top_bar import top_bar
        made = AppState()
        made.transcript_segments = state(segments).transcript_segments if segments else []
        refs: dict = {}
        top_bar(made, noop, noop, noop, refs, noop, noop, noop, False, on_save)
        return refs

    def test_the_top_bar_carries_a_labelled_save_button(self) -> None:
        import strings as s
        button = self.bar()["save_button"]
        self.assertEqual(button.content, s.SAVE_PROJECT)
        self.assertFalse(button.disabled)

    def test_it_says_so_when_there_is_nothing_to_save(self) -> None:
        import strings as s
        button = self.bar(segments=0)["save_button"]
        self.assertTrue(button.disabled)
        self.assertEqual(button.tooltip, s.SAVE_PROJECT_EMPTY)

    def test_pressing_it_saves(self) -> None:
        saved: list[bool] = []
        self.bar(on_save=lambda: saved.append(True))["save_button"].on_click(None)
        self.assertEqual(saved, [True])

    def test_it_names_the_shortcut_that_does_the_same_thing(self) -> None:
        import strings as s
        self.assertIn("Ctrl+S", self.bar()["save_button"].tooltip)

    def test_the_screen_accent_is_not_spent_on_it(self) -> None:
        """One filled sage button per screen, and it is never this one."""
        import design_tokens as t
        self.assertNotEqual(getattr(self.bar()["save_button"], "bgcolor", None), t.primary())


if __name__ == "__main__": unittest.main()
