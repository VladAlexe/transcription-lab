"""Deleting a turn, stopping at the end of one, and marking words as unclear."""
from __future__ import annotations

import io
import unittest
import zipfile
from types import SimpleNamespace

import annotations as an
import document_export
import playback_sync
from app_controller import AppController
from tests.test_following import state

noop = lambda *a, **k: None


class DeleteTests(unittest.TestCase):
    def test_a_deleted_turn_is_gone_and_undo_puts_it_back_in_place(self) -> None:
        controller = AppController(state())
        segments = controller.state.transcript_segments
        doomed = segments[2]
        self.assertTrue(controller.delete_segment(2))
        self.assertNotIn(doomed, controller.state.transcript_segments)
        self.assertEqual(len(controller.state.transcript_segments), 5)
        controller.state.history.undo()
        self.assertIs(controller.state.transcript_segments[2], doomed)

    def test_the_resume_point_follows_the_turns_that_moved(self) -> None:
        controller = AppController(state())
        controller.state.last_reviewed_index = 4
        controller.delete_segment(1)
        self.assertEqual(controller.state.last_reviewed_index, 3)

    def test_nothing_happens_outside_the_transcript(self) -> None:
        controller = AppController(state())
        self.assertFalse(controller.delete_segment(9))
        self.assertEqual(len(controller.state.transcript_segments), 6)


class TurnByTurnTests(unittest.TestCase):
    """Turn i runs from 10i to 10i+8 seconds in the fixture; turn 1 is open."""

    def app(self, continuous: bool = False, position_ms: int = 0, playing: bool = False):
        import main
        calls: list[str] = []
        player = SimpleNamespace(playing=playing, position_ms=position_ms, ready=True)
        player.toggle = lambda: (calls.append("toggle"), setattr(player, "playing", not player.playing))
        player.seek = lambda seconds, play=True: (calls.append(f"seek {seconds:g}"),
                                                  setattr(player, "playing", True))
        app = SimpleNamespace(controller=AppController(state()), continuous_play=continuous,
                              selected_segment=1, player=player, _turn_started_at=0.0,
                              TURN_START_GRACE=main.DesktopApp.TURN_START_GRACE)
        for name in ("open_turn", "_stop_at_turn_end", "play_pause", "play_from"):
            setattr(app, name, getattr(main.DesktopApp, name).__get__(app))
        return app, calls

    def test_it_stops_where_the_open_turn_ends(self) -> None:
        app, calls = self.app(playing=True)
        app._stop_at_turn_end(17000)
        self.assertEqual(calls, [])
        app._stop_at_turn_end(18100)
        self.assertEqual(calls, ["toggle"])

    def test_play_after_the_end_starts_the_turn_over(self) -> None:
        app, calls = self.app(position_ms=18100)
        app.play_pause()
        self.assertEqual(calls, ["seek 10"])

    def test_play_from_elsewhere_starts_the_open_turn(self) -> None:
        app, calls = self.app(position_ms=42000)
        app.play_pause()
        self.assertEqual(calls, ["seek 10"])

    def test_play_inside_the_turn_resumes_where_it_was(self) -> None:
        app, calls = self.app(position_ms=13000)
        app.play_pause()
        self.assertEqual(calls, ["toggle"])

    def test_a_stale_position_right_after_starting_cannot_stop_it(self) -> None:
        app, calls = self.app(position_ms=18100)
        app.play_pause()                       # seeks to 10 s and plays
        app._stop_at_turn_end(18100)           # a report still in flight from before the seek
        self.assertEqual(calls, ["seek 10"])

    def test_straight_through_never_stops_and_play_just_toggles(self) -> None:
        app, calls = self.app(continuous=True, position_ms=18100, playing=True)
        app._stop_at_turn_end(18100)
        self.assertEqual(calls, [])
        app.play_pause()
        self.assertEqual(calls, ["toggle"])


class UnclearTests(unittest.TestCase):
    TEXT = "we went to the market on Tuesday"

    def marked(self):
        start = self.TEXT.index("market")
        return an.add([], start, start + len("market"), self.TEXT, an.UNCLEAR)

    def test_the_runs_carry_the_doubt(self) -> None:
        pieces = an.runs(self.TEXT, self.marked())
        self.assertEqual([p.text for p in pieces if p.unclear], ["market"])

    def test_plain_text_keeps_it_in_brackets(self) -> None:
        item = state(1).transcript_segments[0]
        item.corrected_text = self.TEXT
        item.annotations = self.marked()
        self.assertEqual(document_export.plain_text(item),
                         "we went to the [unclear: market] on Tuesday")

    def test_word_gets_a_wavy_underline(self) -> None:
        made = state(1)
        item = made.transcript_segments[0]
        item.corrected_text = self.TEXT
        item.annotations = self.marked()
        data = document_export.make_docx(made.selected_file_metadata, made.transcript_segments,
                                         {}, "2026-10-21")
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        self.assertIn('w:u w:val="wave"', xml)


if __name__ == "__main__":
    unittest.main()


class NewSpeakerTests(unittest.TestCase):
    def test_a_new_name_becomes_a_new_speaker_and_undo_removes_it(self) -> None:
        controller = AppController(state())
        key = controller.new_speaker(2, "Participant 4")
        self.assertEqual(controller.state.transcript_segments[2].speaker_id, key)
        self.assertEqual(controller.state.speaker_mapping[key], "Participant 4")
        controller.state.history.undo()
        self.assertNotIn(key, controller.state.speaker_mapping)
        self.assertNotEqual(controller.state.transcript_segments[2].speaker_id, key)

    def test_a_name_already_in_use_goes_to_that_speaker(self) -> None:
        controller = AppController(state())
        controller.state.speaker_mapping = {"SPEAKER_0": "Moderator", "SPEAKER_1": "SPEAKER_1"}
        self.assertEqual(controller.new_speaker(1, " moderator "), "SPEAKER_0")
        self.assertEqual(len(controller.state.speaker_mapping), 2)


class SplitTests(unittest.TestCase):
    def test_the_text_and_the_time_are_cut_at_the_cursor(self) -> None:
        controller = AppController(state())
        item = controller.state.transcript_segments[1]          # 10 s to 18 s
        item.corrected_text = "First voice here. Second voice there."
        cut = item.text.index("Second")
        self.assertTrue(controller.split_segment(1, cut))
        first, second = controller.state.transcript_segments[1:3]
        self.assertEqual(first.text, "First voice here.")
        self.assertEqual(second.text, "Second voice there.")
        self.assertEqual(first.absolute_start, 10)
        self.assertEqual(second.absolute_end, 18)
        self.assertAlmostEqual(first.absolute_end, second.absolute_start)
        self.assertTrue(10 < first.absolute_end < 18)
        self.assertEqual(len(controller.state.transcript_segments), 7)

    def test_marks_follow_their_half(self) -> None:
        controller = AppController(state())
        item = controller.state.transcript_segments[1]
        item.corrected_text = "First voice here. Second voice there."
        at = item.text.index("there")
        item.annotations = an.add([], at, at + 5, item.text, an.UNCLEAR)
        controller.split_segment(1, item.text.index("Second"))
        second = controller.state.transcript_segments[2]
        mark = second.annotations[0]
        self.assertEqual(second.text[mark.start:mark.end], "there")

    def test_undo_puts_the_one_turn_back(self) -> None:
        controller = AppController(state())
        original = controller.state.transcript_segments[1]
        controller.split_segment(1, 3)
        controller.state.history.undo()
        self.assertIs(controller.state.transcript_segments[1], original)
        self.assertEqual(len(controller.state.transcript_segments), 6)

    def test_a_cursor_at_either_end_splits_nothing(self) -> None:
        controller = AppController(state())
        text = controller.state.transcript_segments[1].text
        self.assertFalse(controller.split_segment(1, 0))
        self.assertFalse(controller.split_segment(1, len(text)))
