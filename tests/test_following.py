"""Knowing where you are, and not losing what you typed.

Three things a two-hour transcript makes hard, all of them about orientation rather than
features. The panel has to follow the audio, or you are reading one turn while hearing
another. Checked and corrected have to be one act, or ticking a box throws a sentence away.
And the project has to write itself back, or an afternoon of marking depends on remembering.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import flet as ft
import layout_audit
import review_progress
import strings as s
from app_controller import AppController
from app_state import AppState
from components.audio_transport import audio_transport
from models import AudioInfo, TranscriptSegment

noop = lambda *a, **k: None


def state(count: int = 6) -> AppState:
    made = AppState()
    made.selected_file_metadata = AudioInfo("a.m4a", "a.m4a", 32, 40, "aac", 16000, 1, 32000)
    made.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i % 2}", f"SPEAKER_{i % 2}", i * 10, i * 10 + 8,
                          i * 10, i * 10 + 8, f"Turn {i}.") for i in range(count)]
    return made


class FollowTests(unittest.TestCase):
    """The open turn moves with the audio, unless a field has focus."""

    def app(self, following: bool = True, typing: bool = False, selected: int | None = 0):
        import main
        controller = AppController(state())
        rebuilt: list[int] = []
        app = SimpleNamespace(
            controller=controller, refs={"rows": {}, "inspector_host": ft.Container()},
            follow_playback=following, typing=typing, selected_segment=selected,
            _safe_update=lambda *a: True, render=noop,
            build_inspector=lambda index=None: rebuilt.append(index) or ft.Container())
        app.follow_to = lambda index: main.DesktopApp.follow_to(app, index)
        app.rebuilt = rebuilt
        return app

    def test_following_opens_the_turn_that_is_playing(self) -> None:
        app = self.app()
        app.follow_to(3)
        self.assertEqual(app.selected_segment, 3)
        self.assertEqual(app.rebuilt, [3], "the panel is rebuilt for the new turn")

    def test_following_never_touches_the_audio(self) -> None:
        """`select_segment` seeks to the start of a turn, which during playback would drag
        the recording backwards every time it crossed a boundary."""
        import ast, inspect, main
        tree = ast.parse(inspect.getsource(main.DesktopApp.follow_to).strip())
        calls = {ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertNotIn("self.player.seek", calls)
        self.assertNotIn("self.select_segment", calls)
        self.assertIn("self.build_inspector", calls, "it does open the turn")

    def test_the_same_turn_twice_is_not_work(self) -> None:
        app = self.app(selected=2)
        app.follow_to(2)
        self.assertEqual(app.rebuilt, [])

    def test_the_toggle_reports_which_way_it_is(self) -> None:
        import main
        app = SimpleNamespace(follow_playback=True, refs={}, _safe_update=lambda *a: True,
                              render=noop)
        app.refs["player_follow"] = ft.IconButton(ft.Icons.MY_LOCATION)
        main.DesktopApp.toggle_follow(app)
        self.assertFalse(app.follow_playback)
        self.assertEqual(app.refs["player_follow"].tooltip, s.FOLLOW_OFF)
        main.DesktopApp.toggle_follow(app)
        self.assertTrue(app.follow_playback)
        self.assertEqual(app.refs["player_follow"].tooltip, s.FOLLOW_ON)

    def test_the_player_carries_the_control(self) -> None:
        from audio_player import AudioPlayer
        player = AudioPlayer(None, lambda fn, *a: fn(*a))
        refs: dict = {}
        audio_transport(player, refs, noop, noop, noop, True)
        self.assertIn("player_follow", refs)
        self.assertEqual(refs["player_follow"].tooltip, s.FOLLOW_ON)

    def test_the_panel_says_which_turn_of_how_many(self) -> None:
        from views import speakers_view
        panel = speakers_view.inspector(state(536), 142, noop, noop, noop, {})
        shown = [c.value for c in layout_audit.walk(panel) if isinstance(c, ft.Text) and c.value]
        self.assertIn(s.INSPECTOR_POSITION.format(index=143, total=536), shown)


class CheckedAndCorrectedTests(unittest.TestCase):
    """Whichever of the two the researcher reaches for, the edit in front of them is kept."""

    def app(self, folder: str | None = None, text: str = "Turn 0."):
        import main
        controller = AppController(state())
        if folder:
            controller.state.project_path = str(Path(folder) / "study.transcript.json")
        field = ft.TextField(value=text)
        app = SimpleNamespace(
            controller=controller, refs={"rows": {}, "inspector_field": field},
            selected_segment=0, page=SimpleNamespace(run_task=noop),
            _safe_update=lambda *a: True, render=noop, _refresh_status=noop,
            _refresh_row_text=noop, refresh_progress=lambda *a: True,
            _last_autosave=0.0, _autosave_pending=False,
            AUTOSAVE_INTERVAL=main.DesktopApp.AUTOSAVE_INTERVAL)
        app.field = field
        app.save_target = lambda: main.DesktopApp.save_target(app)
        app.autosave = lambda force=False: main.DesktopApp.autosave(app, force)
        app.commit_correction = lambda index=None: main.DesktopApp.commit_correction(app, index)
        app.set_checked = lambda index, value: main.DesktopApp.set_checked(app, index, value)
        app.reveal_turn = lambda index, allow_page_change=True: True
        return app

    def test_ticking_checked_keeps_the_sentence_in_the_box(self) -> None:
        app = self.app(text="Turn zero, corrected.")
        app.set_checked(0, True)
        segment = app.controller.state.transcript_segments[0]
        self.assertEqual(segment.text, "Turn zero, corrected.", "the edit was not thrown away")
        self.assertTrue(segment.checked)

    def test_an_untouched_box_is_not_a_correction(self) -> None:
        app = self.app()
        app.set_checked(0, True)
        self.assertIsNone(app.controller.state.transcript_segments[0].corrected_text)

    def test_saving_a_correction_also_marks_it_reviewed(self) -> None:
        import main
        app = self.app()
        app.set_checked = lambda index, value: main.DesktopApp.set_checked(app, index, value)
        main.DesktopApp.save_correction(app, 0, "Turn zero, corrected.")
        segment = app.controller.state.transcript_segments[0]
        self.assertEqual(segment.text, "Turn zero, corrected.")
        self.assertTrue(segment.checked, "saving a correction is saying you checked it")

    def test_control_enter_saves_marks_and_moves_on(self) -> None:
        import main
        app = self.app(text="Turn zero, corrected.")
        app.select_segment = lambda index: setattr(app, "selected_segment", index)
        main.DesktopApp.mark_and_advance(app)
        segments = app.controller.state.transcript_segments
        self.assertEqual(segments[0].text, "Turn zero, corrected.")
        self.assertTrue(segments[0].checked)
        self.assertEqual(app.selected_segment, 1, "and the next unchecked turn is open")


class AutosaveTests(unittest.TestCase):
    def app(self, folder: str | None):
        return CheckedAndCorrectedTests.app(CheckedAndCorrectedTests(), folder)

    def test_marking_a_turn_writes_the_project_back(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            app = self.app(folder)
            app.set_checked(0, True)
            written = Path(folder) / "study.transcript.json"
            self.assertTrue(written.is_file(), "no dialog, no button, just written")
            self.assertFalse(app.controller.state.dirty)

    def test_a_project_with_no_file_yet_is_never_written_behind_your_back(self) -> None:
        app = self.app(None)
        app.set_checked(0, True)
        self.assertTrue(app.controller.state.dirty, "it waits to be told where")

    def test_a_fast_pass_does_not_write_on_every_turn(self) -> None:
        """A 3 MB transcript takes about 70 ms to write; on every turn that is a stutter."""
        with tempfile.TemporaryDirectory() as folder:
            app = self.app(folder)
            app.set_checked(0, True)
            first = (Path(folder) / "study.transcript.json").stat().st_mtime_ns
            for index in range(1, 5):
                app.set_checked(index, True)
            self.assertEqual((Path(folder) / "study.transcript.json").stat().st_mtime_ns, first,
                             "the rest were throttled")
            self.assertTrue(app._autosave_pending, "and are remembered as owing a write")

    def test_what_was_throttled_is_flushed_on_the_way_out(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            app = self.app(folder)
            app.set_checked(0, True)
            app.set_checked(1, True)
            self.assertTrue(app.controller.state.dirty)
            self.assertTrue(app.autosave(force=True))
            self.assertFalse(app.controller.state.dirty, "nothing is left owing")

    def test_the_window_closing_forces_that_flush(self) -> None:
        import ast, inspect, main
        tree = ast.parse(inspect.getsource(main.DesktopApp.window_event).strip())
        forced = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and ast.unparse(node.func) == "self.autosave"
                  and any(kw.arg == "force" for kw in node.keywords)]
        self.assertTrue(forced, "closing has to flush whatever the throttle held back")


if __name__ == "__main__": unittest.main()
