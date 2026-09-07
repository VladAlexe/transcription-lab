"""Edits that are actually kept, and comments that reach Word.

The complaint was that Ctrl+Enter saved some edits and not others. The cause was not the
handler: the correction box never told the application what had been typed into it. Flet
refreshes a control's value on the Python side only when an event arrives carrying it, and
the box reported focus and blur but not change. So pressing Ctrl+Enter with the caret still
in the box saved whatever the text had been at the last blur — which is why clicking away
first appeared to fix it.
"""
from __future__ import annotations

import io
import unittest
import zipfile
from types import SimpleNamespace

import flet as ft
import layout_audit
import strings as s
from app_controller import AppController
from app_state import AppState
from document_export import make_docx
from models import AudioInfo, TranscriptSegment
from views import speakers_view

noop = lambda *a, **k: None
INFO = AudioInfo("a.m4a", "a.m4a", 32, 60, "aac", 16000, 1, 32000)


def state(count: int = 4) -> AppState:
    made = AppState()
    made.selected_file_metadata = INFO
    made.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i % 2}", f"SPEAKER_{i % 2}", i * 10, i * 10 + 8,
                          i * 10, i * 10 + 8, f"Turn {i}.") for i in range(count)]
    return made


class TypingReachesTheApplicationTests(unittest.TestCase):
    """The one bug behind 'some save, some do not'."""

    def field(self) -> ft.TextField:
        panel = speakers_view.inspector(state(), 0, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop)
        found = layout_audit.find(panel, lambda c: isinstance(c, ft.TextField))
        self.assertEqual(len(found), 1)
        return found[0]

    def test_the_correction_box_reports_every_keystroke(self) -> None:
        self.assertIsNotNone(self.field().on_change,
                             "without this the value is whatever it was at the last blur")

    def test_typing_updates_the_value_the_application_reads(self) -> None:
        field = self.field()
        field.on_change(ft.Event(name="change", control=SimpleNamespace(value="Half a sen"),
                                 data="Half a sen"))
        self.assertEqual(field.value, "Half a sen")

    def test_it_still_reports_focus_so_space_does_not_pause(self) -> None:
        field = self.field()
        self.assertIsNotNone(field.on_focus)
        self.assertIsNotNone(field.on_blur)


class ControlEnterTests(unittest.TestCase):
    """Ctrl+Enter with the caret still in the box: the case that used to lose work."""

    def app(self, typed: str):
        import main
        controller = AppController(state())
        field = ft.TextField(value=controller.state.transcript_segments[0].text)
        field.on_change = lambda e: setattr(field, "value", e.control.value)
        app = SimpleNamespace(controller=controller, selected_segment=0,
                              refs={"rows": {}, "inspector_field": field},
                              typing=True, page=SimpleNamespace(run_task=noop),
                              _safe_update=lambda *a: True, render=noop,
                              _refresh_status=noop, _refresh_row_text=noop,
                              refresh_progress=lambda *a: True, reveal_turn=lambda *a, **k: True,
                              _last_autosave=0.0, _autosave_pending=False,
                              AUTOSAVE_INTERVAL=main.DesktopApp.AUTOSAVE_INTERVAL)
        app.save_target = lambda: ""
        app.autosave = lambda force=False: main.DesktopApp.autosave(app, force)
        app.commit_correction = lambda index=None: main.DesktopApp.commit_correction(app, index)
        app.set_checked = lambda index, value: main.DesktopApp.set_checked(app, index, value)
        app.select_segment = lambda index: setattr(app, "selected_segment", index)
        # What the researcher just typed, reported the way the live box now reports it.
        field.on_change(ft.Event(name="change", control=SimpleNamespace(value=typed), data=typed))
        return app

    def test_the_edit_is_kept_without_clicking_away_first(self) -> None:
        import main
        app = self.app("Turn zero, as actually spoken.")
        main.DesktopApp.mark_and_advance(app)
        self.assertEqual(app.controller.state.transcript_segments[0].text,
                         "Turn zero, as actually spoken.")

    def test_and_the_turn_is_marked_and_left_behind(self) -> None:
        import main
        app = self.app("Turn zero, as actually spoken.")
        main.DesktopApp.mark_and_advance(app)
        self.assertTrue(app.controller.state.transcript_segments[0].checked)
        self.assertEqual(app.selected_segment, 1)

    def test_it_works_over_and_over_down_the_transcript(self) -> None:
        """Five turns in a row, never leaving the keyboard."""
        import main
        app = self.app("First.")
        for index, text in enumerate(("First.", "Second.", "Third.")):
            app.refs["inspector_field"].on_change(
                ft.Event(name="change", control=SimpleNamespace(value=text), data=text))
            main.DesktopApp.mark_and_advance(app)
        saved = [item.text for item in app.controller.state.transcript_segments[:3]]
        self.assertEqual(saved, ["First.", "Second.", "Third."])
        self.assertTrue(all(item.checked for item in app.controller.state.transcript_segments[:3]))


class CommentTests(unittest.TestCase):
    """A note on a turn, in the margin of the Word file rather than inside the speech."""

    def test_a_note_is_stored_apart_from_the_transcript(self) -> None:
        controller = AppController(state())
        self.assertTrue(controller.annotate_segment(1, "  Check this figure.  "))
        segment = controller.state.transcript_segments[1]
        self.assertEqual(segment.note, "Check this figure.", "trimmed")
        self.assertEqual(segment.text, "Turn 1.", "the transcript itself is untouched")
        self.assertIsNone(segment.corrected_text)
        self.assertTrue(controller.state.dirty)

    def test_the_same_note_twice_is_not_a_change(self) -> None:
        controller = AppController(state())
        controller.annotate_segment(1, "Check this.")
        controller.state.dirty = False
        self.assertFalse(controller.annotate_segment(1, "Check this."))
        self.assertFalse(controller.state.dirty)

    def test_an_old_project_without_notes_still_opens(self) -> None:
        from models import TranscriptSegment as Segment
        stored = {"chunk_index": 0, "chunk_start_offset": 0.0, "original_speaker": "a",
                  "speaker_id": "A", "local_start": 0.0, "local_end": 1.0,
                  "absolute_start": 0.0, "absolute_end": 1.0, "original_text": "hi"}
        self.assertEqual(Segment.from_dict(stored).note, "")

    def comments_in(self, data: bytes) -> str:
        archive = zipfile.ZipFile(io.BytesIO(data))
        if "word/comments.xml" not in archive.namelist():
            return ""
        return archive.read("word/comments.xml").decode("utf-8")

    def test_a_note_becomes_a_real_word_comment(self) -> None:
        segment = state().transcript_segments[0]
        segment.note = "The figure sounds like forty, not fourteen."
        comments = self.comments_in(make_docx(INFO, [segment], {}, "2026-09-01"))
        self.assertIn("forty, not fourteen", comments)
        self.assertIn(s.DOC_COMMENT_AUTHOR, comments)

    def test_the_comment_is_not_in_the_transcript_body(self) -> None:
        segment = state().transcript_segments[0]
        segment.note = "Check this figure."
        archive = zipfile.ZipFile(io.BytesIO(make_docx(INFO, [segment], {}, "2026-09-01")))
        body = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Turn 0.", body)
        self.assertNotIn("Check this figure.", body, "a comment lives in the margin")

    def test_a_turn_with_no_note_adds_no_comment(self) -> None:
        segment = state().transcript_segments[0]
        self.assertEqual(self.comments_in(make_docx(INFO, [segment], {}, "2026-09-01")), "")

    def test_notes_survive_saving_and_reopening(self) -> None:
        import json, tempfile
        from pathlib import Path
        from document_export import project_payload
        controller = AppController(state())
        controller.annotate_segment(2, "Ask about this in the follow-up.")
        payload = project_payload(INFO, [], controller.state.transcript_segments, {}, "date")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.transcript.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            reopened = AppController()
            reopened.load_project(str(path))
            self.assertEqual(reopened.state.transcript_segments[2].note,
                             "Ask about this in the follow-up.")

    def test_the_panel_offers_a_way_to_add_one(self) -> None:
        panel = speakers_view.inspector(state(), 0, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop, on_note=noop, on_toggle_note=noop)
        tooltips = {c.tooltip for c in layout_audit.find(panel, lambda c: isinstance(c, ft.IconButton))}
        self.assertIn(s.NOTE_ADD, tooltips)

    def test_a_turn_that_has_one_shows_it_without_asking(self) -> None:
        made = state()
        made.transcript_segments[0].note = "Check this figure."
        panel = speakers_view.inspector(made, 0, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop, on_note=noop, on_toggle_note=noop)
        boxes = [c for c in layout_audit.find(panel, lambda c: isinstance(c, ft.TextField))
                 if c.label == s.NOTE_LABEL]
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].value, "Check this figure.")

    def test_the_box_stays_out_of_the_way_until_it_is_wanted(self) -> None:
        panel = speakers_view.inspector(state(), 0, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop, on_note=noop, on_toggle_note=noop)
        boxes = [c for c in layout_audit.find(panel, lambda c: isinstance(c, ft.TextField))
                 if c.label == s.NOTE_LABEL]
        self.assertEqual(boxes, [], "no note, no box")


class NewProjectTests(unittest.TestCase):
    def test_a_new_recording_forgets_the_previous_project_file(self) -> None:
        """Otherwise the next save writes the new interview over the old one."""
        import tempfile
        from pathlib import Path
        controller = AppController(state())
        controller.state.project_path = r"C:\research\first.transcript.json"
        with tempfile.TemporaryDirectory() as folder:
            recording = Path(folder) / "second.m4a"
            recording.write_bytes(b"0" * 64)
            try:
                controller.select_recording(str(recording))
            except Exception:
                pass                      # probing needs FFmpeg; the clearing happens first
        self.assertIsNone(controller.state.project_path)


if __name__ == "__main__": unittest.main()
