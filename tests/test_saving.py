"""Saving a project: once you have said where, it stops asking.

The first save has to ask — there is nowhere to put the file yet. Every save after that has
exactly one right answer, so asking again is a question with no information in it. These
tests drive the real handler and check the bytes that land on disk.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import strings as s
from app_controller import AppController
from app_state import AppState
from models import AudioInfo, TranscriptSegment

noop = lambda *a, **k: None


def populated() -> AppState:
    state = AppState()
    state.selected_file_metadata = AudioInfo("a.m4a", "a.m4a", 32, 40, "aac", 16000, 1, 32000)
    state.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i}", f"SPEAKER_{i % 2}", i * 5, i * 5 + 4,
                          i * 5, i * 5 + 4, f"Turn {i}.") for i in range(3)]
    return state


class SaveTargetTests(unittest.TestCase):
    def app(self, project_path: str | None = None):
        import main
        controller = AppController(populated())
        controller.state.project_path = project_path
        told: list[str] = []
        asked: list[bool] = []
        stand_in = SimpleNamespace(controller=controller, refs={}, page=None,
                                   _safe_update=lambda *a: True,
                                   _refresh_status=noop, render=noop)
        stand_in.save_target = lambda: main.DesktopApp.save_target(stand_in)
        stand_in._refresh_save_button = lambda: main.DesktopApp._refresh_save_button(stand_in)
        stand_in.page = SimpleNamespace(run_task=lambda *a: asked.append(True))
        stand_in.told, stand_in.asked = told, asked
        return stand_in, told, asked

    def test_a_project_with_no_file_yet_has_no_target(self) -> None:
        app, _, _ = self.app(None)
        self.assertEqual(app.save_target(), "")

    def test_a_saved_project_remembers_where_it_lives(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "study.transcript.json")
            app, _, _ = self.app(path)
            self.assertEqual(app.save_target(), path)

    def test_a_target_whose_folder_has_gone_falls_back_to_asking(self) -> None:
        """A project opened from a USB stick that is no longer plugged in."""
        app, _, _ = self.app(r"Z:\removed\study.transcript.json")
        self.assertEqual(app.save_target(), "")


class DirectSaveTests(unittest.TestCase):
    def app(self, project_path: str | None):
        import main
        controller = AppController(populated())
        controller.state.project_path = project_path
        messages: list[str] = []
        asked: list[bool] = []
        stand_in = SimpleNamespace(controller=controller, refs={},
                                   _safe_update=lambda *a: True, _refresh_status=noop,
                                   render=noop,
                                   page=SimpleNamespace(run_task=lambda *a: asked.append(True)))
        stand_in.save_target = lambda: main.DesktopApp.save_target(stand_in)
        stand_in._refresh_save_button = lambda: main.DesktopApp._refresh_save_button(stand_in)
        stand_in._save_project = noop
        return stand_in, messages, asked

    def save(self, app, messages):
        import main
        original = main.notification
        main.notification = lambda page, message: messages.append(message)
        try:
            main.DesktopApp.save_project(app)
        finally:
            main.notification = original

    def test_the_first_save_asks_where(self) -> None:
        app, messages, asked = self.app(None)
        self.save(app, messages)
        self.assertEqual(asked, [True], "the dialog is opened exactly once")
        self.assertEqual(messages, [])

    def test_every_save_after_that_writes_straight_back(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "study.transcript.json"
            app, messages, asked = self.app(str(path))
            app.controller.state.dirty = True
            self.save(app, messages)
            self.assertEqual(asked, [], "no dialog once the file is known")
            self.assertTrue(path.is_file())
            self.assertEqual(messages, [s.SAVED_TO.format(name="study.transcript.json")])
            self.assertFalse(app.controller.state.dirty, "and the project is clean again")

    def test_what_it_writes_is_a_real_project(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "study.transcript.json"
            app, messages, _ = self.app(str(path))
            self.save(app, messages)
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(payload["project_format"], "transcript-project-v1")
            self.assertEqual(len(payload["segments"]), 3)

    def test_saving_twice_overwrites_the_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "study.transcript.json"
            app, messages, asked = self.app(str(path))
            self.save(app, messages)
            app.controller.state.transcript_segments[0].corrected_text = "Corrected."
            self.save(app, messages)
            self.assertEqual(asked, [])
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 1, "one file, not two")
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(payload["segments"][0]["corrected_text"], "Corrected.")

    def test_the_button_says_where_it_will_write(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "study.transcript.json"
            app, messages, _ = self.app(str(path))
            from components.buttons import secondary_button
            app.refs["save_button"] = secondary_button(s.SAVE_PROJECT, noop)
            self.save(app, messages)
            tooltip = app.refs["save_button"].tooltip
            self.assertIn("study.transcript.json", tooltip)
            self.assertIn("Ctrl+Shift+S", tooltip, "and how to send it somewhere else")


if __name__ == "__main__": unittest.main()
