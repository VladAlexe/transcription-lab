"""Marking a phrase inside a turn: bold, three highlighters, and an anchored comment."""
from __future__ import annotations
import sys, unittest, zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import annotations as an
from app_controller import AppController
from app_state import DEFAULT_HIGHLIGHT_LABELS
from document_export import make_docx, project_payload
from models import AudioInfo, TranscriptSegment

LINE = "Deci avem prima ediție de Someș Delivery 2015, după care la două luni."
PHRASE = LINE.index("Someș Delivery"), LINE.index("Someș Delivery") + len("Someș Delivery")


def turn(text: str = LINE) -> TranscriptSegment:
    return TranscriptSegment(0, 0.0, "SPEAKER_00", "SPEAKER_00", 0.0, 5.0, 0.0, 5.0, text)


def controller_with(text: str = LINE) -> AppController:
    app = AppController()
    app.state.transcript_segments = [turn(text)]
    return app


class RangeTests(unittest.TestCase):
    def test_a_backwards_selection_marks_the_same_words(self) -> None:
        """Dragging right to left gives base > extent; it is the same phrase."""
        forward = an.add([], PHRASE[0], PHRASE[1], LINE, an.BOLD)
        backward = an.add([], PHRASE[1], PHRASE[0], LINE, an.BOLD)
        self.assertEqual((forward[0].start, forward[0].end), (backward[0].start, backward[0].end))

    def test_an_empty_selection_marks_nothing(self) -> None:
        self.assertEqual(an.add([], 5, 5, LINE, an.HIGHLIGHT), [])

    def test_the_marked_phrase_is_remembered_with_the_mark(self) -> None:
        marks = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        self.assertEqual(marks[0].quote, "Someș Delivery")

    def test_marking_again_replaces_rather_than_stacking_the_colour(self) -> None:
        """Two highlights over the same words would be one under the other, unreadable."""
        marks = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "1")
        marks = an.add(marks, *PHRASE, LINE, an.HIGHLIGHT, "3")
        highlights = [m for m in marks if m.kind == an.HIGHLIGHT]
        self.assertEqual([m.slot for m in highlights], ["3"])

    def test_bold_and_a_highlight_and_a_comment_coexist_on_one_phrase(self) -> None:
        marks = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        marks = an.add(marks, *PHRASE, LINE, an.BOLD)
        marks = an.add(marks, *PHRASE, LINE, an.COMMENT, note="Which edition?")
        self.assertEqual(sorted({m.kind for m in marks}), [an.BOLD, an.COMMENT, an.HIGHLIGHT])


class RunTests(unittest.TestCase):
    def test_the_text_is_split_at_the_edges_of_the_mark(self) -> None:
        marks = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "1")
        pieces = an.runs(LINE, marks)
        self.assertEqual([p.text for p in pieces],
                         [LINE[:PHRASE[0]], "Someș Delivery", LINE[PHRASE[1]:]])
        self.assertEqual([p.slot for p in pieces], ["", "1", ""])

    def test_the_runs_rejoin_into_exactly_the_original_text(self) -> None:
        """The preview and the Word paragraph are built from these; losing a character
        anywhere would put a different sentence in the document."""
        marks = an.add(an.add([], 5, 12, LINE, an.BOLD), *PHRASE, LINE, an.HIGHLIGHT, "3")
        self.assertEqual("".join(p.text for p in an.runs(LINE, marks)), LINE)

    def test_unmarked_text_is_one_run(self) -> None:
        self.assertEqual(len(an.runs(LINE, [])), 1)

    def test_neighbouring_stretches_with_the_same_formatting_merge(self) -> None:
        """Otherwise adjacent marks would become two Word runs saying the same thing."""
        marks = [an.Annotation(0, 5, an.BOLD, quote=LINE[:5]),
                 an.Annotation(5, 10, an.BOLD, quote=LINE[5:10])]
        self.assertEqual([p.text for p in an.runs(LINE, marks)], [LINE[:10], LINE[10:]])

    def test_a_mark_beyond_the_end_of_the_text_cannot_produce_a_short_paragraph(self) -> None:
        marks = [an.Annotation(1000, 1010, an.BOLD, quote="gone")]
        self.assertEqual("".join(p.text for p in an.runs(LINE, marks)), LINE)


class ReanchorTests(unittest.TestCase):
    def test_a_mark_follows_its_phrase_when_words_are_inserted_before_it(self) -> None:
        marks = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "1")
        edited = LINE.replace("Deci avem", "Deci am avut")
        moved = an.reanchor(marks, LINE, edited)
        self.assertEqual(edited[moved[0].start:moved[0].end], "Someș Delivery")

    def test_a_mark_is_dropped_when_its_phrase_is_gone(self) -> None:
        """Silently re-anchoring to whatever now sits there would mark the wrong words."""
        marks = an.add([], *PHRASE, LINE, an.COMMENT, note="Check")
        self.assertEqual(an.reanchor(marks, LINE, LINE.replace("Someș Delivery", "X")), [])

    def test_saving_an_edit_moves_the_marks_with_it(self) -> None:
        app = controller_with()
        app.mark_selection(0, *PHRASE, an.HIGHLIGHT, "2")
        app.correct_segment(0, LINE.replace("Deci avem", "Deci am avut"))
        mark = app.state.transcript_segments[0].annotations[0]
        self.assertEqual(app.state.transcript_segments[0].text[mark.start:mark.end],
                         "Someș Delivery")


class ControllerTests(unittest.TestCase):
    def test_marking_a_phrase_makes_the_project_unsaved(self) -> None:
        app = controller_with()
        self.assertTrue(app.mark_selection(0, *PHRASE, an.BOLD))
        self.assertTrue(app.state.dirty)

    def test_clearing_takes_every_kind_off_the_range(self) -> None:
        app = controller_with()
        app.mark_selection(0, *PHRASE, an.BOLD)
        app.mark_selection(0, *PHRASE, an.HIGHLIGHT, "1")
        app.mark_selection(0, *PHRASE, an.COMMENT, note="Check")
        self.assertTrue(app.clear_marks(0, *PHRASE))
        self.assertEqual(app.state.transcript_segments[0].annotations, [])

    def test_clearing_leaves_a_mark_on_other_words_alone(self) -> None:
        app = controller_with()
        app.mark_selection(0, 0, 4, an.BOLD)
        app.mark_selection(0, *PHRASE, an.HIGHLIGHT, "1")
        app.clear_marks(0, *PHRASE)
        self.assertEqual([m.kind for m in app.state.transcript_segments[0].annotations], [an.BOLD])

    def test_one_comment_can_be_taken_back_without_touching_the_others(self) -> None:
        app = controller_with()
        app.mark_selection(0, 0, 4, an.COMMENT, note="One")
        app.mark_selection(0, *PHRASE, an.COMMENT, note="Two")
        first = app.state.transcript_segments[0].annotations[0]
        self.assertTrue(app.drop_mark(0, first))
        self.assertEqual([m.note for m in app.state.transcript_segments[0].annotations], ["Two"])

    def test_an_index_that_does_not_exist_is_refused_rather_than_raising(self) -> None:
        app = controller_with()
        self.assertFalse(app.mark_selection(9, 0, 4, an.BOLD))
        self.assertFalse(app.clear_marks(9, 0, 4))


class WordExportTests(unittest.TestCase):
    """The point of the whole feature: the marking has to arrive in the document."""

    def build(self, segment: TranscriptSegment, labels=DEFAULT_HIGHLIGHT_LABELS) -> zipfile.ZipFile:
        info = AudioInfo("interview.mp3", "interview.mp3", 10, 5.0, "mp3", 44100, 1)
        data = make_docx(info, [segment], {"SPEAKER_00": "Ana"}, "2026-09-04",
                         highlight_labels=list(labels))
        return zipfile.ZipFile(BytesIO(data))

    def test_a_highlighted_phrase_carries_a_coloured_band_in_word(self) -> None:
        """Word's highlighter has fifteen fixed colours and none of the three is among them,
        so the marking is run shading — the same band behind the words, in the exact colour
        the researcher picked rather than the nearest one Word happens to stock."""
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        body = self.build(item).read("word/document.xml").decode()
        self.assertIn("w:shd", body)

    def test_the_ink_on_a_dark_highlight_is_light_enough_to_read(self) -> None:
        """Smoky Rose is dark enough that Word's default black on it is 3.1:1."""
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        body = self.build(item).read("word/document.xml").decode()
        self.assertIn('w:val="FFFFFF"', body)

    def test_each_colour_reaches_word_as_the_exact_palette_fill(self) -> None:
        """Amber Earth, Smoky Rose and Muted Teal, as given — not approximated."""
        for slot, expected in (("1", 'w:fill="E8871E"'), ("2", 'w:fill="945D5E"'),
                               ("3", 'w:fill="759588"')):
            item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, slot)
            body = self.build(item).read("word/document.xml").decode()
            self.assertIn(expected, body, f"colour {slot} did not reach Word")

    def test_bold_lands_on_the_marked_run_and_not_the_paragraph(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.BOLD)
        # The header labels and the speaker line are bold as well, so what proves the phrase
        # was singled out is one more bold run than the same document without the mark.
        plain = self.build(turn()).read("word/document.xml").decode()
        body = self.build(item).read("word/document.xml").decode()
        self.assertEqual(body.count("<w:b/>"), plain.count("<w:b/>") + 1)

    def test_a_comment_is_anchored_to_the_phrase_not_the_whole_turn(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.COMMENT, note="Which one?")
        archive = self.build(item)
        self.assertIn("commentRangeStart", archive.read("word/document.xml").decode())
        self.assertIn("Which one?", archive.read("word/comments.xml").decode())

    def test_the_turn_reads_exactly_as_before_it_was_marked(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "1")
        body = self.build(item).read("word/document.xml").decode()
        for word in ("Deci", "Someș", "Delivery", "luni"): self.assertIn(word, body)

    def test_the_colour_key_is_printed_with_the_names_from_settings(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        body = self.build(item, ["Key quote", "Contested", "Follow up"]).read("word/document.xml").decode()
        self.assertIn("Contested", body)

    def test_the_key_lists_only_the_colours_actually_used(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        body = self.build(item, ["Key quote", "Contested", "Follow up"]).read("word/document.xml").decode()
        self.assertNotIn("Key quote", body)

    def test_a_transcript_with_no_highlights_prints_no_key(self) -> None:
        body = self.build(turn()).read("word/document.xml").decode()
        self.assertNotIn("Highlight key", body)

    def test_an_unnamed_colour_still_appears_in_the_key(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "3")
        body = self.build(item, ["", "", ""]).read("word/document.xml").decode()
        self.assertIn("Colour 3", body)

    def test_a_whole_turn_note_and_a_phrase_comment_both_survive(self) -> None:
        item = turn(); item.note = "Long pause here."
        item.annotations = an.add([], *PHRASE, LINE, an.COMMENT, note="Which one?")
        comments = self.build(item).read("word/comments.xml").decode()
        self.assertIn("Long pause here.", comments)
        self.assertIn("Which one?", comments)


class PersistenceTests(unittest.TestCase):
    def test_marks_survive_saving_and_reopening_the_project(self) -> None:
        item = turn()
        item.annotations = an.add(an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2"),
                                  *PHRASE, LINE, an.COMMENT, note="Which one?")
        payload = project_payload(None, [], [item], {}, "2026-09-04")
        back = TranscriptSegment.from_dict(payload["segments"][0])
        self.assertEqual(sorted(m.kind for m in back.annotations), [an.COMMENT, an.HIGHLIGHT])
        self.assertEqual(back.annotations[0].quote, "Someș Delivery")

    def test_the_colour_key_is_saved_with_the_project(self) -> None:
        """A code the reader loses on reopening is not a code."""
        payload = project_payload(None, [], [turn()], {}, "2026-09-04",
                                  highlight_labels=["Key quote", "Contested", "Follow up"])
        self.assertEqual(payload["highlight_legend"], ["Key quote", "Contested", "Follow up"])

    def test_a_project_saved_before_marking_existed_still_opens(self) -> None:
        old = {"chunk_index": 0, "chunk_start_offset": 0.0, "original_speaker": "SPEAKER_00",
               "speaker_id": "SPEAKER_00", "local_start": 0.0, "local_end": 1.0,
               "absolute_start": 0.0, "absolute_end": 1.0, "original_text": LINE}
        self.assertEqual(TranscriptSegment.from_dict(old).annotations, [])

    def test_a_corrupt_mark_in_the_file_does_not_stop_the_project_opening(self) -> None:
        data = {"chunk_index": 0, "chunk_start_offset": 0.0, "original_speaker": "S",
                "speaker_id": "S", "local_start": 0.0, "local_end": 1.0, "absolute_start": 0.0,
                "absolute_end": 1.0, "original_text": LINE,
                "annotations": [{"start": 3, "end": 8, "unknown_key": True}, "rubbish"]}
        self.assertEqual(len(TranscriptSegment.from_dict(data).annotations), 1)


class PanelTests(unittest.TestCase):
    """The panel has to offer the marking without becoming another screen."""

    def panel(self, item: TranscriptSegment, words_mode: bool = False):
        from app_state import AppState
        from views import speakers_view
        state = AppState(); state.transcript_segments = [item]
        state.speaker_mapping = {"SPEAKER_00": "Ana"}
        nothing = lambda *a: None
        return speakers_view.inspector(state, 0, nothing, nothing, nothing, {},
            on_seek=nothing, words_mode=words_mode,
            on_words_mode=(lambda: None) if words_mode else None,
            on_mark=nothing, on_selection_comment=nothing, on_clear_marks=nothing,
            on_drop_mark=nothing, highlight_labels=list(DEFAULT_HIGHLIGHT_LABELS))

    def flatten(self, control, seen=None) -> list:
        seen = [] if seen is None else seen
        seen.append(control)
        for name in ("controls", "actions"):
            for child in getattr(control, name, None) or []: self.flatten(child, seen)
        for name in ("content", "label", "title"):
            child = getattr(control, name, None)
            if hasattr(child, "_c") or hasattr(child, "controls"): self.flatten(child, seen)
        return seen

    def test_the_marking_bar_is_offered_on_a_turn(self) -> None:

        tooltips = [getattr(c, "tooltip", "") for c in self.flatten(self.panel(turn()))]
        self.assertIn("Bold", tooltips)
        self.assertIn("Comment on selection", tooltips)

    def test_the_three_highlighters_carry_the_names_from_settings(self) -> None:
        tooltips = [getattr(c, "tooltip", "") or "" for c in self.flatten(self.panel(turn()))]
        for name in DEFAULT_HIGHLIGHT_LABELS:
            self.assertTrue(any(name in tip for tip in tooltips), f"{name} is not offered")

    def test_the_preview_appears_only_once_something_is_marked(self) -> None:
        plain = [getattr(c, "value", "") for c in self.flatten(self.panel(turn()))]
        self.assertNotIn("As it will appear in Word", plain)
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "1")
        marked = [getattr(c, "value", "") for c in self.flatten(self.panel(item))]
        self.assertIn("As it will appear in Word", marked)

    def test_the_preview_paints_the_phrase_in_the_colour_word_will_use(self) -> None:

        from components.marking import preview
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "2")
        spans = preview(item.text, item.annotations, None).content.spans
        painted = [sp for sp in spans if sp.style.bgcolor]
        self.assertEqual([sp.text for sp in painted], ["Someș Delivery"])
        self.assertEqual(painted[0].style.bgcolor, "#945D5E")
        self.assertEqual(painted[0].style.color, "#FFFFFF")

    def test_a_comment_on_a_phrase_is_readable_without_opening_word(self) -> None:
        item = turn(); item.annotations = an.add([], *PHRASE, LINE, an.COMMENT, note="Which one?")
        shown = [getattr(c, "value", "") for c in self.flatten(self.panel(item))]
        self.assertIn("Which one?", shown)

    def test_the_word_ribbon_offers_no_marking_because_it_has_no_selection(self) -> None:
        """Its words are buttons that seek the recording; there is nothing to select."""
        item = turn()
        from models import Word
        item.words = [Word(0.0, 0.5, "Deci")]
        tooltips = [getattr(c, "tooltip", "") for c in self.flatten(self.panel(item, words_mode=True))]
        self.assertNotIn("Bold", tooltips)


class EditingTests(unittest.TestCase):
    def test_an_edit_that_removes_the_marked_phrase_is_reported_not_silent(self) -> None:
        """A mark the researcher believes is still there and will not find in the exported
        document is worse than one they were told went away."""
        import strings as s
        self.assertIn("{count}", s.MARK_DETACHED)
        app = controller_with()
        app.mark_selection(0, *PHRASE, an.HIGHLIGHT, "1")
        before = len(app.state.transcript_segments[0].annotations)
        app.correct_segment(0, LINE.replace("Someș Delivery", "Cluj Delivery"))
        self.assertEqual(before - len(app.state.transcript_segments[0].annotations), 1)

    def test_an_edit_elsewhere_in_the_turn_keeps_every_mark(self) -> None:
        app = controller_with()
        app.mark_selection(0, *PHRASE, an.HIGHLIGHT, "1")
        app.mark_selection(0, *PHRASE, an.COMMENT, note="Which one?")
        app.correct_segment(0, LINE.replace("două luni", "trei luni"))
        self.assertEqual(len(app.state.transcript_segments[0].annotations), 2)


class LayoutTests(unittest.TestCase):
    """The bar sits inside a 420px panel and must not push it wider."""

    def bar(self):
        import flet as ft
        from components.marking import marking_bar
        nothing = lambda *a: None
        return marking_bar(ft.TextField(), [], list(DEFAULT_HIGHLIGHT_LABELS),
                           nothing, nothing, nothing).controls[0]

    def test_the_buttons_fit_the_panel_with_room_for_the_selected_phrase(self) -> None:
        import design_tokens as t
        from components.marking import SWATCH
        buttons = 3 * t.ICON_BUTTON + 3 * SWATCH + 7 * t.S4
        self.assertLess(buttons, t.INSPECTOR_WIDTH - 2 * t.INSPECTOR_PADDING)

    def test_the_button_row_carries_no_wrapping_text_of_its_own(self) -> None:
        """A sentence sharing the row with six buttons is a sentence read as an ellipsis."""
        self.assertEqual([c for c in self.bar().controls if getattr(c, "max_lines", None) == 1], [])

    def test_nothing_can_be_marked_until_something_is_selected(self) -> None:
        self.assertTrue(all(c.disabled for c in self.bar().controls
                            if hasattr(c, "disabled") and c.disabled is not None
                            and getattr(c, "on_click", None)))


class ClearTests(unittest.TestCase):
    """The button beside "3 marked" has to be able to take those three off."""

    def test_clearing_with_nothing_selected_covers_the_whole_turn(self) -> None:
        """Applying a mark rebuilds the panel, so by the time the researcher reaches for
        Clear there is no selection left — and a Clear that needs one does nothing."""
        app = controller_with()
        app.mark_selection(0, 0, 4, an.BOLD)
        app.mark_selection(0, *PHRASE, an.HIGHLIGHT, "3")
        self.assertTrue(app.clear_marks(0, 0, len(app.state.transcript_segments[0].text)))
        self.assertEqual(app.state.transcript_segments[0].annotations, [])

    def test_the_clear_button_is_live_whenever_the_turn_carries_a_mark(self) -> None:
        import flet as ft
        from components.marking import marking_bar
        nothing = lambda *a: None
        marks = an.add([], *PHRASE, LINE, an.HIGHLIGHT, "1")
        row = marking_bar(ft.TextField(), marks, None, nothing, nothing, nothing).controls[0]
        live = [c for c in row.controls if getattr(c, "tooltip", "") and not c.disabled]
        self.assertEqual([c.tooltip for c in live], ["Clear every mark on this turn"])

    def test_the_hint_is_on_its_own_line_so_it_is_never_truncated(self) -> None:
        import flet as ft
        from components.marking import marking_bar
        nothing = lambda *a: None
        bar = marking_bar(ft.TextField(), [], None, nothing, nothing, nothing)
        self.assertEqual(len(bar.controls), 2)
        self.assertEqual(bar.controls[1].value, "Select text above, then mark it.")
