"""Find and replace across the whole transcript: matching rules, one undo, text only."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import flet as ft
import layout_audit
import strings as s
from app_controller import AppController
from app_state import AppState
from document_export import project_payload
from find_replace import (Options, build_pattern, count_matches, matching_turns, replace_all, undo)
from models import AudioInfo, TranscriptSegment, Word
from views import speakers_view

noop = lambda *a, **k: None


def turn(index: int, text: str, start: float = 0.0) -> TranscriptSegment:
    return TranscriptSegment(0, 0.0, str(index), f"Speaker {index + 1}", start, start + 5,
                             start, start + 5, text, None, False,
                             [Word(start, start + 1, text.split()[0] if text else "", .9)], .9)


def transcript() -> list[TranscriptSegment]:
    return [turn(0, "Primaria a raspuns tarziu", 0),
            turn(1, "primaria nu a raspuns deloc", 10),
            turn(2, "Am scris la Primariat si la primaria mare", 20),
            turn(3, "Nimic despre subiect aici", 30)]


class MatchingTests(unittest.TestCase):
    def test_counting_is_case_insensitive_by_default(self) -> None:
        self.assertEqual(count_matches(transcript(), "primaria", Options()), 4)

    def test_case_sensitive_narrows_the_count(self) -> None:
        segments = transcript()
        # "Primaria" and "Primariat" both start with a capital P; only case is being filtered.
        self.assertEqual(count_matches(segments, "Primaria", Options(case_sensitive=True)), 2)
        self.assertEqual(count_matches(segments, "primaria", Options(case_sensitive=True)), 2)
        self.assertEqual(count_matches(segments, "Primaria",
                                       Options(case_sensitive=True, whole_word=True)), 1)

    def test_whole_word_excludes_longer_words(self) -> None:
        segments = transcript()
        # "Primariat" contains "primaria" but is a different word.
        self.assertEqual(count_matches(segments, "primaria", Options()), 4)
        self.assertEqual(count_matches(segments, "primaria", Options(whole_word=True)), 3)

    def test_both_options_together(self) -> None:
        segments = transcript()
        self.assertEqual(count_matches(segments, "primaria",
                                       Options(case_sensitive=True, whole_word=True)), 2)

    def test_an_empty_term_matches_nothing(self) -> None:
        self.assertIsNone(build_pattern("", Options()))
        self.assertEqual(count_matches(transcript(), "", Options()), 0)
        self.assertEqual(count_matches(transcript(), "   ".strip(), Options()), 0)

    def test_the_term_is_literal_not_a_regular_expression(self) -> None:
        segments = [turn(0, "a.b and axb")]
        self.assertEqual(count_matches(segments, "a.b", Options()), 1, "the dot is a dot")

    def test_a_punctuation_term_still_works_with_whole_word_on(self) -> None:
        segments = [turn(0, "ehm... yes")]
        self.assertEqual(count_matches(segments, "...", Options(whole_word=True)), 1)

    def test_which_turns_match(self) -> None:
        self.assertEqual(matching_turns(transcript(), "primaria", Options()), [0, 1, 2])
        self.assertEqual(matching_turns(transcript(), "nothing here", Options()), [])


class ReplaceTests(unittest.TestCase):
    def test_replacing_across_every_turn(self) -> None:
        segments = transcript()
        record = replace_all(segments, "primaria", "Primăria", Options())
        self.assertEqual(record.matches, 4)
        self.assertEqual(record.turns, 3)
        self.assertEqual(segments[0].text, "Primăria a raspuns tarziu")
        self.assertEqual(segments[1].text, "Primăria nu a raspuns deloc")
        self.assertEqual(segments[3].text, "Nimic despre subiect aici", "untouched turn")

    def test_the_count_promised_is_the_count_delivered(self) -> None:
        for options in (Options(), Options(case_sensitive=True), Options(whole_word=True)):
            with self.subTest(options=options):
                segments = transcript()
                promised = count_matches(segments, "primaria", options)
                record = replace_all(segments, "primaria", "X", options)
                self.assertEqual(record.matches, promised)

    def test_replacing_writes_only_corrected_text(self) -> None:
        segments = transcript()
        before = [(item.original_text, item.absolute_start, item.absolute_end,
                   item.speaker_id, [w.text for w in item.words]) for item in segments]
        replace_all(segments, "primaria", "Primăria", Options())
        after = [(item.original_text, item.absolute_start, item.absolute_end,
                  item.speaker_id, [w.text for w in item.words]) for item in segments]
        self.assertEqual(before, after,
                         "timings, speaker ids, words and the original text must be untouched")
        self.assertEqual(segments[0].corrected_text, "Primăria a raspuns tarziu")

    def test_replacing_back_to_the_original_clears_the_correction(self) -> None:
        segments = [turn(0, "hello world")]
        replace_all(segments, "world", "there", Options())
        self.assertEqual(segments[0].corrected_text, "hello there")
        replace_all(segments, "there", "world", Options())
        self.assertIsNone(segments[0].corrected_text, "identical to the original is not a correction")

    def test_replacing_builds_on_an_existing_correction(self) -> None:
        segments = [turn(0, "one two")]
        segments[0].corrected_text = "one three"
        replace_all(segments, "three", "four", Options())
        self.assertEqual(segments[0].text, "one four")

    def test_no_matches_changes_nothing(self) -> None:
        segments = transcript()
        record = replace_all(segments, "absent", "x", Options())
        self.assertFalse(record.applied)
        self.assertEqual(record.matches, 0)
        self.assertTrue(all(item.corrected_text is None for item in segments))


class UndoTests(unittest.TestCase):
    def test_one_undo_restores_every_turn(self) -> None:
        segments = transcript()
        original = [item.text for item in segments]
        record = replace_all(segments, "primaria", "Primăria", Options())
        self.assertNotEqual([item.text for item in segments], original)
        restored = undo(segments, record)
        self.assertEqual(restored, 3)
        self.assertEqual([item.text for item in segments], original)

    def test_undo_restores_a_previous_correction_rather_than_wiping_it(self) -> None:
        segments = [turn(0, "one two")]
        segments[0].corrected_text = "one three"
        record = replace_all(segments, "three", "four", Options())
        undo(segments, record)
        self.assertEqual(segments[0].corrected_text, "one three", "the earlier edit survives")

    def test_the_controller_offers_a_single_undo(self) -> None:
        controller = AppController()
        controller.state.transcript_segments = transcript()
        original = [item.text for item in controller.state.transcript_segments]
        record = controller.replace_all("primaria", "Primăria", Options())
        self.assertTrue(record.applied)
        self.assertIsNotNone(controller.state.last_replacement)
        self.assertTrue(controller.state.dirty)
        self.assertEqual(controller.undo_replace(), 3)
        self.assertEqual([item.text for item in controller.state.transcript_segments], original)
        self.assertIsNone(controller.state.last_replacement)
        self.assertEqual(controller.undo_replace(), 0, "only one step back is offered")


class PersistenceTests(unittest.TestCase):
    def test_a_replacement_survives_save_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            recording = Path(folder) / "a.m4a"
            recording.write_bytes(b"0" * 32)
            controller = AppController()
            controller.state.selected_file_metadata = AudioInfo(str(recording), "a.m4a", 32, 40,
                                                                "aac", 16000, 1, 32000)
            controller.state.transcript_segments = transcript()
            controller.replace_all("primaria", "Primăria", Options())
            payload = project_payload(controller.state.selected_file_metadata, [],
                                      controller.state.transcript_segments, {}, "date", {}, True, 2)
            path = Path(folder) / "p.transcript.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            reopened = AppController()
            reopened.load_project(str(path))
            self.assertEqual(reopened.state.transcript_segments[0].text, "Primăria a raspuns tarziu")
            self.assertEqual(reopened.state.transcript_segments[0].original_text,
                             "Primaria a raspuns tarziu", "the original is still recorded")


class ReachabilityTests(unittest.TestCase):
    """The feature has to be clickable, not merely present in a module."""

    def state(self) -> AppState:
        state = AppState()
        state.transcript_segments = transcript()
        return state

    def texts(self, control) -> list[str]:
        """Labels the researcher can actually read: text controls and button captions."""
        found = [c.value for c in layout_audit.walk(control) if isinstance(c, ft.Text) and c.value]
        found += [c.content for c in layout_audit.walk(control)
                  if isinstance(getattr(c, "content", None), str) and c.content]
        return found

    def test_the_review_screen_offers_a_find_and_replace_control(self) -> None:
        screen = speakers_view.build(self.state(), noop, noop, noop, None, 0, noop,
                                     {"rows": {}, "speakers": {}}, 960, noop, noop, noop, noop)
        self.assertIn(s.FIND_REPLACE, self.texts(screen),
                      "there must be a visible way to open find and replace")

    def test_the_bar_shows_a_live_count_before_anything_is_replaced(self) -> None:
        from components.find_replace_bar import find_replace_bar
        bar = find_replace_bar("primaria", "Primăria", False, False, 4, 3, False,
                               noop, noop, noop, noop, {}, noop, 960.0)
        self.assertIn(s.FIND_COUNT.format(count=4, turns=3), self.texts(bar))

    def test_the_bar_reports_no_matches_and_disables_replace(self) -> None:
        from components.find_replace_bar import find_replace_bar
        bar = find_replace_bar("absent", "x", False, False, 0, 0, False,
                               noop, noop, noop, noop, {}, noop)
        self.assertIn(s.FIND_COUNT_NONE, self.texts(bar))
        buttons = [c for c in layout_audit.walk(bar) if isinstance(c, ft.Button)]
        self.assertTrue(all(button.disabled for button in buttons),
                        "replace all must be unavailable with nothing to replace")

    def test_the_bar_offers_undo_only_after_a_replacement(self) -> None:
        from components.find_replace_bar import find_replace_bar
        without = find_replace_bar("a", "b", False, False, 1, 1, False, noop, noop, noop, noop, {}, noop)
        self.assertNotIn(s.FIND_UNDO, self.texts(without))
        with_undo = find_replace_bar("a", "b", False, False, 1, 1, True, noop, noop, noop, noop, {}, noop)
        self.assertIn(s.FIND_UNDO, self.texts(with_undo))

    def test_both_boxes_report_what_was_typed(self) -> None:
        """The replacement box used to report nothing, so Replace all ran with an empty
        replacement and quietly deleted the term instead of changing it."""
        from components.find_replace_bar import find_replace_bar
        seen: list[tuple] = []
        refs: dict = {}
        find_replace_bar("a", "b", False, False, 1, 1, False,
                         lambda *args: seen.append(args), noop, noop, noop, refs, noop, 960.0)
        for key, typed in (("find_term", "primaria"), ("find_replacement", "Primăria")):
            field = refs[key]
            field.value = typed
            field.on_change(None)
        self.assertEqual(seen[-1], ("primaria", "Primăria", False, False),
                         "both boxes, both toggles, every keystroke")

    def test_replace_all_is_reachable_the_moment_there_is_something_to_replace(self) -> None:
        """It is built disabled on an empty term and the panel is not rebuilt per keystroke,
        so the live recount has to be able to wake the button as well as the count."""
        from components.find_replace_bar import find_replace_bar
        refs: dict = {}
        find_replace_bar("", "", False, False, 0, 0, False, noop, noop, noop, noop, refs,
                         noop, 960.0)
        self.assertIn("find_apply", refs, "the recount needs a handle on the button")
        self.assertTrue(refs["find_apply"].disabled, "nothing typed, nothing to replace")
        refs.clear()
        find_replace_bar("primaria", "X", False, False, 4, 3, False, noop, noop, noop, noop,
                         refs, noop, 960.0)
        self.assertFalse(refs["find_apply"].disabled)
        self.assertEqual(refs["find_apply"].content, s.FIND_REPLACE_ALL)

    def test_the_count_and_the_button_are_written_from_one_source(self) -> None:
        from components.find_replace_bar import match_summary
        self.assertEqual(match_summary("", 0, 0)[0], s.FIND_COUNT_EMPTY)
        self.assertEqual(match_summary("x", 0, 0)[0], s.FIND_COUNT_NONE)
        self.assertEqual(match_summary("x", 4, 3)[0], s.FIND_COUNT.format(count=4, turns=3))

    def test_the_search_boxes_report_focus_so_space_does_not_pause_audio(self) -> None:
        from components.find_replace_bar import find_replace_bar
        seen: list[bool] = []
        bar = find_replace_bar("", "", False, False, 0, 0, False, noop, noop, noop, noop, {},
                               seen.append)
        fields = layout_audit.find(bar, lambda c: isinstance(c, ft.TextField))
        self.assertEqual(len(fields), 2)
        for field in fields:
            self.assertIsNotNone(field.on_focus)
            self.assertIsNotNone(field.on_blur)


if __name__ == "__main__": unittest.main()
