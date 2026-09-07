"""The reviewer's name: on the document, and on every comment in it."""
from __future__ import annotations
import sys, unittest, zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import annotations as an
import strings as s
from app_controller import AppController
from app_state import AppState
from document_export import make_docx, project_payload
from models import AudioInfo, TranscriptSegment

LINE = "Deci avem prima ediție de Someș Delivery 2015."
PHRASE = LINE.index("Someș"), LINE.index("Someș") + 14
INFO = AudioInfo(r"C:\R\iv.m4a", "iv.m4a", 100, 60.0, "aac", 48000, 2)


def turn() -> TranscriptSegment:
    return TranscriptSegment(0, 0.0, "A", "A", 0.0, 5.0, 0.0, 5.0, LINE)


def document(item: TranscriptSegment, reviewer: str) -> zipfile.ZipFile:
    return zipfile.ZipFile(BytesIO(make_docx(INFO, [item], {"A": "Ana"}, "2026-09-04",
                                             comment_author=reviewer)))


class DocumentTests(unittest.TestCase):
    def test_the_name_signs_a_comment_on_a_phrase(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.COMMENT, note="Which one?")
        self.assertIn("Vlad Alexe", document(item, "Vlad Alexe").read("word/comments.xml").decode())

    def test_the_name_signs_a_note_on_a_whole_turn(self) -> None:
        item = turn(); item.note = "Long pause here."
        self.assertIn("Vlad Alexe", document(item, "Vlad Alexe").read("word/comments.xml").decode())

    def test_the_name_is_printed_with_the_document_metadata(self) -> None:
        body = document(turn(), "Vlad Alexe").read("word/document.xml").decode()
        self.assertIn(s.DOC_REVIEWER, body)
        self.assertIn("Vlad Alexe", body)

    def test_no_name_means_the_document_claims_nothing_about_who_checked_it(self) -> None:
        """Better silent than signed by a placeholder that names nobody."""
        self.assertNotIn(s.DOC_REVIEWER, document(turn(), "").read("word/document.xml").decode())

    def test_comments_are_still_signed_when_no_name_was_given(self) -> None:
        item = turn(); item.note = "Long pause here."
        self.assertIn(s.DOC_COMMENT_AUTHOR, document(item, "").read("word/comments.xml").decode())

    def test_surrounding_whitespace_is_not_a_name(self) -> None:
        self.assertNotIn(s.DOC_REVIEWER, document(turn(), "   ").read("word/document.xml").decode())


class ProjectTests(unittest.TestCase):
    def test_the_name_is_saved_with_the_project(self) -> None:
        payload = project_payload(None, [], [turn()], {}, "2026-09-04", reviewer="Vlad Alexe")
        self.assertEqual(payload["review"]["reviewer"], "Vlad Alexe")

    def test_reopening_a_project_restores_the_name_that_reviewed_it(self) -> None:
        app = AppController()
        app.state.settings.reviewer = "Vlad Alexe"
        payload = project_payload(None, [], [turn()], {}, "2026-09-04",
                                  reviewer=app.state.settings.reviewer)
        fresh = AppController()
        review = payload["review"]
        self.assertEqual(review.get("reviewer"), "Vlad Alexe")
        fresh.state.settings.reviewer = review["reviewer"]
        self.assertEqual(fresh.state.settings.reviewer, "Vlad Alexe")

    def test_a_project_saved_before_this_existed_still_opens(self) -> None:
        payload = project_payload(None, [], [turn()], {}, "2026-09-04")
        self.assertEqual(payload["review"]["reviewer"], "")


class SettingsTests(unittest.TestCase):
    def test_the_name_is_offered_in_settings(self) -> None:
        import layout_audit
        import flet as ft
        from views import settings_view
        noop = lambda *a, **k: None
        screen = settings_view.build(AppState(), noop, noop, noop)
        shown = [getattr(c, "value", "") for c in layout_audit.walk(screen)]
        self.assertIn(s.SETTINGS_REVIEWER, shown)

    def test_the_field_shows_the_name_already_set(self) -> None:
        import layout_audit
        import flet as ft
        from views import settings_view
        noop = lambda *a, **k: None
        app = AppState(); app.settings.reviewer = "Vlad Alexe"
        screen = settings_view.build(app, noop, noop, noop)
        values = [c.value for c in layout_audit.walk(screen) if isinstance(c, ft.TextField)]
        self.assertIn("Vlad Alexe", values)
