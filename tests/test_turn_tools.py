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


class StopAtTurnEndTests(unittest.TestCase):
    """Turn i runs from 10i to 10i+8 seconds in the fixture."""

    def app(self, continuous: bool = False):
        import main
        toggles: list[bool] = []
        player = SimpleNamespace(playing=True)
        player.toggle = lambda: (toggles.append(True), setattr(player, "playing", False))
        app = SimpleNamespace(controller=AppController(state()), continuous_play=continuous,
                              _stopped_turn=None, player=player,
                              active=playback_sync.Position(0))
        app.check = lambda ms: main.DesktopApp._stop_at_turn_end(
            app, playback_sync.locate(app.controller.state.transcript_segments, ms / 1000), ms)
        return app, toggles

    def test_it_pauses_where_the_turn_ends(self) -> None:
        app, toggles = self.app()
        app.check(7000)
        self.assertEqual(toggles, [])
        app.check(8100)
        self.assertEqual(toggles, [True])
        self.assertEqual(app._stopped_turn, 0)

    def test_play_again_carries_on_into_the_next_turn(self) -> None:
        app, toggles = self.app()
        app.check(8100)
        app.player.playing = True
        app.check(8300)                       # still past turn 0's end: no second stop
        self.assertEqual(toggles, [True])

    def test_straight_through_never_stops(self) -> None:
        app, toggles = self.app(continuous=True)
        app.check(8100)
        self.assertEqual(toggles, [])


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
