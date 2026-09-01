"""Reviewing a long interview across several sittings.

The questions these answer are the ones a researcher asks out loud: how much have I done,
what is next, and where was I when I closed the laptop. Everything checked here has to
survive being saved and reopened, because that is the whole point of it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import flet as ft
import design_tokens as t
import layout_audit
import review_progress as r
import strings as s
from app_controller import AppController
from app_state import AppState
from components.review_strip import label_for, review_strip
from components.transcript_list import transcript_item, transcript_list
from document_export import project_payload
from models import AudioInfo, TranscriptSegment, Word
from views import speakers_view

noop = lambda *a, **k: None


def turn(index: int, checked: bool = False) -> TranscriptSegment:
    item = TranscriptSegment(0, 0.0, f"raw{index % 2}", f"SPEAKER_{index % 2}", index * 10,
                             index * 10 + 8, index * 10, index * 10 + 8,
                             f"Turn number {index}.", None, False,
                             [Word(index * 10, index * 10 + 1, "Turn", .9)], .9)
    item.checked = checked
    return item


def transcript(pattern: str = "xx..x") -> list[TranscriptSegment]:
    """'x' is checked, '.' is not — so a test reads its own fixture."""
    return [turn(i, char == "x") for i, char in enumerate(pattern)]


class ProgressTests(unittest.TestCase):
    def test_counting(self) -> None:
        progress = r.progress(transcript("xx..x"))
        self.assertEqual((progress.checked, progress.total), (3, 5))
        self.assertEqual(progress.percent, 60)
        self.assertAlmostEqual(progress.fraction, .6)

    def test_an_empty_transcript_is_not_finished(self) -> None:
        progress = r.progress([])
        self.assertEqual(progress.percent, 0)
        self.assertFalse(progress.complete)
        self.assertEqual(progress.fraction, 0.0)

    def test_it_never_reads_a_hundred_percent_while_work_remains(self) -> None:
        nearly = transcript("x" * 999 + ".")
        self.assertEqual(r.progress(nearly).percent, 99)
        self.assertFalse(r.progress(nearly).complete)

    def test_it_never_reads_zero_once_work_has_started(self) -> None:
        started = transcript("x" + "." * 999)
        self.assertEqual(r.progress(started).percent, 1)

    def test_the_label_says_what_the_brief_asked_for(self) -> None:
        self.assertEqual(label_for(r.Progress(142, 536)), "142 / 536 checked, 26%")
        self.assertEqual(label_for(r.Progress(0, 536)), s.PROGRESS_NONE)
        self.assertEqual(label_for(r.Progress(536, 536)), s.PROGRESS_COMPLETE.format(total=536))


class NextTests(unittest.TestCase):
    def test_it_finds_the_next_one_still_to_do(self) -> None:
        self.assertEqual(r.next_unchecked(transcript("xx..x"), 0), 2)
        self.assertEqual(r.next_unchecked(transcript("xx..x"), 2), 3)

    def test_it_wraps_so_a_skipped_turn_is_not_lost(self) -> None:
        self.assertEqual(r.next_unchecked(transcript(".xxxx"), 1), 0,
                         "a turn skipped early comes back at the end")

    def test_nothing_left_returns_nothing(self) -> None:
        self.assertIsNone(r.next_unchecked(transcript("xxx"), 0))
        self.assertIsNone(r.next_unchecked([], None))

    def test_from_the_start_when_no_turn_is_open(self) -> None:
        self.assertEqual(r.next_unchecked(transcript("x..") , None), 1)


class FilterTests(unittest.TestCase):
    def test_unfiltered_is_every_turn_in_order(self) -> None:
        self.assertEqual(r.visible_order(transcript("xx..x")), [0, 1, 2, 3, 4])

    def test_filtered_keeps_real_transcript_indices(self) -> None:
        self.assertEqual(r.visible_order(transcript("xx..x"), True), [2, 3])

    def test_a_filtered_row_still_points_at_its_real_turn(self) -> None:
        segments = transcript("xx..x")
        picked: list[int] = []
        refs: dict = {}
        transcript_list(segments, r.visible_order(segments, True), {}, {}, None, 0, 80,
                        picked.append, noop, refs, 400)
        self.assertEqual(refs["page_order"], [2, 3])
        rows = sorted(k for k in refs if isinstance(k, int))
        self.assertEqual(rows, [2, 3], "rows are keyed by position in the interview")
        refs[3]["container"].on_click(None)
        self.assertEqual(picked, [3], "selecting row two of the filter selects turn three")

    def test_the_filtered_list_says_so_when_it_is_empty(self) -> None:
        segments = transcript("xxx")
        listing = transcript_list(segments, r.visible_order(segments, True), {}, {}, None, 0, 80,
                                  noop, noop, {}, 400)
        shown = [c.value for c in layout_audit.walk(listing) if isinstance(c, ft.Text) and c.value]
        self.assertIn(s.ALL_CHECKED, shown)


class MarkerTests(unittest.TestCase):
    """A reviewed turn is marked on its left edge, and an unreviewed one shows nothing."""

    def row(self, checked: bool) -> ft.Control:
        return transcript_item(0, turn(0, checked), {}, t.speaker_color(0), False, 400, noop, {})

    def test_a_checked_turn_carries_a_thin_sage_bar(self) -> None:
        marked = self.row(True)
        self.assertEqual(marked.border.left.color, t.primary())
        self.assertEqual(marked.border.left.width, t.CHECK_RULE)
        self.assertLessEqual(t.CHECK_RULE, 4, "thin: a marker, not a block")

    def test_an_unchecked_turn_shows_nothing_at_all(self) -> None:
        plain = self.row(False)
        self.assertEqual(plain.border.left.color, ft.Colors.TRANSPARENT)
        self.assertIsNone(plain.bgcolor)

    def test_the_marker_is_distinct_from_every_other_row_signal(self) -> None:
        """Reviewed is an edge. Being heard and being open are fills. Nothing shares."""
        marked, plain = self.row(True), self.row(False)
        self.assertEqual(marked.bgcolor, plain.bgcolor,
                         "checking a turn must not tint it like playback")
        self.assertNotEqual(marked.border.left.color, plain.border.left.color)


class InspectorToggleTests(unittest.TestCase):
    def state(self, pattern: str = "..") -> AppState:
        state = AppState()
        state.transcript_segments = transcript(pattern)
        return state

    def panel(self, state: AppState, index: int = 0, **kwargs):
        return speakers_view.inspector(state, index, noop, noop, noop, {}, None, noop, noop,
                                       noop, noop, **kwargs)

    def checkbox(self, panel) -> ft.Checkbox:
        found = [c for c in layout_audit.walk(panel)
                 if isinstance(c, ft.Checkbox) and c.label == s.MARK_CHECKED]
        self.assertEqual(len(found), 1, "one toggle, in the panel for the open turn")
        return found[0]

    def test_the_toggle_shows_the_turn_state(self) -> None:
        self.assertFalse(self.checkbox(self.panel(self.state(".."))).value)
        self.assertTrue(self.checkbox(self.panel(self.state("x."))).value)

    def test_the_toggle_reports_the_turn_and_the_new_value(self) -> None:
        seen: list[tuple[int, bool]] = []
        panel = self.panel(self.state(".."), 1,
                           on_checked=lambda index, value: seen.append((index, value)))
        box = self.checkbox(panel)
        box.value = True
        box.on_change(ft.Event(name="change", control=box, data="true"))
        self.assertEqual(seen, [(1, True)])

    def test_the_toggle_is_dead_rather_than_missing_without_a_handler(self) -> None:
        self.assertTrue(self.checkbox(self.panel(self.state())).disabled)


class SingleTextTests(unittest.TestCase):
    """The panel used to print the same sentence three times."""

    def state(self, corrected: str | None = None) -> AppState:
        state = AppState()
        item = turn(0)
        item.corrected_text = corrected
        state.transcript_segments = [item]
        return state

    def panel(self, state: AppState, **kwargs):
        return speakers_view.inspector(state, 0, noop, noop, noop, {}, None, noop, noop, noop,
                                       noop, noop, **kwargs)

    def occurrences(self, panel, text: str) -> int:
        found = 0
        for control in layout_audit.walk(panel):
            if isinstance(control, ft.TextField) and control.value == text:
                found += 1
            elif isinstance(control, ft.Text) and control.value == text:
                found += 1
            elif isinstance(control, ft.Text) and control.spans:
                if "".join(span.text or "" for span in control.spans).strip() == text.strip():
                    found += 1
        return found

    def test_the_text_appears_exactly_once(self) -> None:
        self.assertEqual(self.occurrences(self.panel(self.state()), "Turn number 0."), 1)

    def test_words_mode_replaces_the_editor_rather_than_joining_it(self) -> None:
        panel = self.panel(self.state(), words_mode=True, on_words_mode=noop)
        self.assertEqual(len(layout_audit.find(panel, lambda c: isinstance(c, ft.TextField))), 0,
                         "one slot, two modes")

    def test_the_original_is_not_shown_until_the_text_has_been_changed(self) -> None:
        clean = self.panel(self.state(), on_show_original=noop)
        shown = [c.content for c in layout_audit.walk(clean) if isinstance(getattr(c, "content", None), str)]
        self.assertNotIn(s.SHOW_ORIGINAL, shown, "nothing was changed, so there is nothing to compare")

    def test_a_changed_turn_offers_the_original_and_still_shows_it_once(self) -> None:
        state = self.state("Turn number nought.")
        offered = [c.content for c in layout_audit.walk(self.panel(state, on_show_original=noop))
                   if isinstance(getattr(c, "content", None), str)]
        self.assertIn(s.SHOW_ORIGINAL, offered)
        opened = self.panel(state, show_original=True, on_show_original=noop)
        self.assertEqual(self.occurrences(opened, "Turn number 0."), 1, "the original, once")
        self.assertEqual(self.occurrences(opened, "Turn number nought."), 1, "the edit, once")


class StripTests(unittest.TestCase):
    def strip(self, checked: int = 142, total: int = 536, only: bool = False,
              resume: bool = True) -> ft.Control:
        return review_strip(r.Progress(checked, total), only, noop,
                            noop if resume else None, "00:41:12", {})

    def test_it_shows_a_track_and_the_count(self) -> None:
        control = self.strip()
        bars = layout_audit.find(control, lambda c: isinstance(c, ft.ProgressBar))
        self.assertEqual(len(bars), 1)
        self.assertAlmostEqual(bars[0].value, 142 / 536)
        self.assertLessEqual(bars[0].bar_height, 6, "slim, not a component in its own right")
        shown = [c.value for c in layout_audit.walk(control) if isinstance(c, ft.Text) and c.value]
        self.assertIn("142 / 536 checked, 26%", shown)

    def test_the_only_sage_here_is_the_filled_track(self) -> None:
        """The screen keeps one primary accent, and it is Continue to export."""
        control = self.strip()
        filled = [c for c in layout_audit.walk(control)
                  if isinstance(c, ft.Button) and getattr(c, "bgcolor", None) == t.primary()]
        self.assertEqual(filled, [])

    def test_the_filter_is_a_plain_toggle(self) -> None:
        boxes = layout_audit.find(self.strip(only=True), lambda c: isinstance(c, ft.Checkbox))
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].label, s.ONLY_UNCHECKED)
        self.assertTrue(boxes[0].value)

    def test_resume_appears_only_when_there_is_somewhere_to_go(self) -> None:
        offered = [c.content for c in layout_audit.walk(self.strip())
                   if isinstance(getattr(c, "content", None), str)]
        self.assertIn(s.RESUME, offered)
        absent = [c.content for c in layout_audit.walk(self.strip(resume=False))
                  if isinstance(getattr(c, "content", None), str)]
        self.assertNotIn(s.RESUME, absent)


class ResumeTests(unittest.TestCase):
    def test_it_prefers_where_you_actually_stopped(self) -> None:
        self.assertEqual(r.resume_index(transcript("x..x."), 3), 3)

    def test_it_falls_back_to_the_first_unchecked_turn(self) -> None:
        self.assertEqual(r.resume_index(transcript("xx..x"), None), 2)

    def test_a_stale_position_does_not_throw_the_researcher_somewhere_random(self) -> None:
        self.assertEqual(r.resume_index(transcript("xx..x"), 99), 2,
                         "the transcript was re-run and the saved index no longer exists")
        self.assertIsNone(r.resume_index([], 3))


class PersistenceTests(unittest.TestCase):
    def project(self, controller: AppController) -> dict:
        return project_payload(controller.state.selected_file_metadata, [],
                               controller.state.transcript_segments,
                               controller.state.speaker_mapping, "date", {}, True, 2, "", "",
                               None, None, controller.state.last_reviewed_index)

    def loaded(self, payload: dict) -> AppController:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.transcript.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            reopened = AppController()
            reopened.load_project(str(path))
            return reopened

    def controller(self) -> AppController:
        controller = AppController()
        controller.state.selected_file_metadata = AudioInfo("a.m4a", "a.m4a", 32, 40, "aac",
                                                            16000, 1, 32000)
        controller.state.transcript_segments = transcript("xx..x")
        controller.state.last_reviewed_index = 3
        return controller

    def test_checked_turns_survive_save_and_reopen(self) -> None:
        reopened = self.loaded(self.project(self.controller()))
        self.assertEqual([item.checked for item in reopened.state.transcript_segments],
                         [True, True, False, False, True])

    def test_the_position_survives_too(self) -> None:
        self.assertEqual(self.loaded(self.project(self.controller())).state.last_reviewed_index, 3)

    def test_the_payload_records_the_count_for_a_human_reading_the_file(self) -> None:
        self.assertEqual(self.project(self.controller())["review"]["checked_turns"], 3)

    def test_a_project_saved_before_any_of_this_still_opens(self) -> None:
        payload = self.project(self.controller())
        payload.pop("review")
        for segment in payload["segments"]:
            segment.pop("checked")
        reopened = self.loaded(payload)
        self.assertEqual(len(reopened.state.transcript_segments), 5)
        self.assertTrue(all(not item.checked for item in reopened.state.transcript_segments))
        self.assertIsNone(reopened.state.last_reviewed_index)

    def test_a_stale_saved_position_is_dropped_on_load(self) -> None:
        payload = self.project(self.controller())
        payload["review"]["last_reviewed_turn_index"] = 500
        self.assertIsNone(self.loaded(payload).state.last_reviewed_index)

    def test_marking_a_turn_makes_the_project_dirty(self) -> None:
        controller = AppController()
        controller.state.transcript_segments = transcript("...")
        self.assertTrue(r.set_checked(controller.state.transcript_segments, 1, True))
        self.assertFalse(r.set_checked(controller.state.transcript_segments, 1, True),
                         "already there, so nothing to save")
        self.assertFalse(r.set_checked(controller.state.transcript_segments, 99, True))


if __name__ == "__main__": unittest.main()
