"""Review tools that must work for every provider, degrading instead of failing.

Word timings, confidence scores and diarization are all optional; a screen that assumes them
would break on the OpenAI path and on any custom endpoint.
"""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

import design_tokens as t
import flet as ft
import layout_audit
import strings as s
from app_state import AppState
from audio_player import AudioPlayer
from components.audio_transport import SPEEDS
from components.transcript_list import paint_turn, transcript_item
from models import TranscriptSegment, Word
from playback_sync import Position, format_stamp, insert_timestamp, locate, rewind_target
from providers import ProviderCapabilities
from views import speakers_view

noop = lambda *a, **k: None


def timed_turn(index: int, start: float, words: list[tuple[str, float, float]],
               confidence: float | None = .9) -> TranscriptSegment:
    entries = [Word(begin, end, text, confidence) for text, begin, end in words]
    return TranscriptSegment(0, 0.0, str(index % 2), f"Speaker {index % 2 + 1}",
                             start, entries[-1].end if entries else start + 1,
                             start, entries[-1].end if entries else start + 1,
                             " ".join(text for text, _, _ in words), None, False, entries, confidence)


def untimed_turn(index: int, start: float, end: float, text: str,
                 confidence: float | None = None) -> TranscriptSegment:
    """What OpenAI and the generic endpoint produce: text and a span, no words."""
    return TranscriptSegment(0, 0.0, str(index % 2), f"Speaker {index % 2 + 1}",
                             start, end, start, end, text, None, False, [], confidence)


TIMED = [timed_turn(0, 0.0, [("Bună", 0.0, 0.6), ("ziua", 0.6, 1.2), ("tuturor", 1.2, 2.0)]),
         timed_turn(1, 3.0, [("Mulțumim", 3.0, 3.8), ("mult", 3.8, 4.4)])]
UNTIMED = [untimed_turn(0, 0.0, 2.0, "Bună ziua tuturor"),
           untimed_turn(1, 3.0, 4.4, "Mulțumim mult")]


class SyncedHighlightTests(unittest.TestCase):
    def test_word_level_when_the_provider_timed_words(self) -> None:
        self.assertEqual(locate(TIMED, 0.1), Position(0, 0))
        self.assertEqual(locate(TIMED, 0.7), Position(0, 1))
        self.assertEqual(locate(TIMED, 1.5), Position(0, 2))
        self.assertEqual(locate(TIMED, 3.9), Position(1, 1))

    def test_turn_level_fallback_when_words_are_absent(self) -> None:
        """The OpenAI path: still highlighted, just not per word."""
        for seconds, turn in ((0.1, 0), (1.9, 0), (3.5, 1), (4.4, 1)):
            found = locate(UNTIMED, seconds)
            self.assertEqual(found.turn, turn)
            self.assertIsNone(found.word, "no words means no word index, never a crash")

    def test_before_the_first_turn_nothing_is_highlighted(self) -> None:
        found = locate(TIMED, -1)
        self.assertFalse(found.known)
        self.assertIsNone(found.turn)

    def test_a_pause_between_turns_keeps_the_previous_turn_lit(self) -> None:
        self.assertEqual(locate(TIMED, 2.5).turn, 0)

    def test_an_empty_transcript_is_safe(self) -> None:
        self.assertEqual(locate([], 5.0), Position())

    def test_painting_uses_spans_only_when_words_exist(self) -> None:
        refs: dict = {}
        transcript_item(0, TIMED[0], {}, "#000000", False, 400, noop, refs)
        parts = refs[0]
        paint_turn(parts, TIMED[0], 1, True)
        self.assertIsNotNone(parts["body"].spans)
        self.assertEqual(len(parts["body"].spans), 3)
        self.assertIsNone(parts["body"].value)
        self.assertEqual(parts["container"].bgcolor, t.primary_soft())

    def test_painting_an_untimed_turn_falls_back_to_plain_text(self) -> None:
        refs: dict = {}
        transcript_item(0, UNTIMED[0], {}, "#000000", False, 400, noop, refs)
        parts = refs[0]
        paint_turn(parts, UNTIMED[0], None, True)
        self.assertIsNone(parts["body"].spans, "no words: no spans, and no crash")
        self.assertEqual(parts["body"].value, UNTIMED[0].text)
        self.assertEqual(parts["container"].bgcolor, t.primary_soft())

    def test_leaving_a_turn_clears_its_highlight(self) -> None:
        refs: dict = {}
        transcript_item(0, TIMED[0], {}, "#000000", False, 400, noop, refs)
        parts = refs[0]
        paint_turn(parts, TIMED[0], 1, True)
        paint_turn(parts, TIMED[0], None, False)
        self.assertIsNone(parts["container"].bgcolor)
        self.assertEqual(parts["body"].value, TIMED[0].text)


class AutoRewindTests(unittest.TestCase):
    class _FakeAudio:
        src = None
        def update(self): ...
        async def play(self, position=0): ...
        async def pause(self): ...
        async def resume(self): ...
        async def seek(self, position): ...

    def player(self, rewind: float):
        self._temp = tempfile.TemporaryDirectory(prefix="rewind_")
        self.addCleanup(self._temp.cleanup)
        recording = Path(self._temp.name) / "a.m4a"
        recording.write_bytes(b"0" * 64)
        calls: list[tuple[str, tuple]] = []
        player = AudioPlayer(self._FakeAudio(), lambda fn, *a: calls.append((fn.__name__, a)))
        player.bind(str(recording))
        player.auto_rewind = rewind
        player.seek(30.0)          # starts playback at 30s
        player.position_ms = 30_000
        calls.clear()
        return player, calls

    def test_pausing_stops_exactly_where_it_was(self) -> None:
        """Seeking backwards at the moment of pausing sent a lower position to the interface,
        which followed it: Ctrl+W sometimes jumped to the previous turn instead of stopping,
        and always looked as though the audio had run on for another second first."""
        player, calls = self.player(1.5)
        player.toggle()
        self.assertEqual([name for name, _ in calls], ["pause"])
        self.assertEqual(player.position_ms, 30_000)

    def test_the_step_back_is_taken_when_playback_starts_again(self) -> None:
        player, calls = self.player(1.5)
        player.toggle()
        calls.clear()
        player.toggle()
        self.assertEqual(calls[0], ("seek", (28_500,)), "1.5s back from 30.0s")
        self.assertEqual(calls[1][0], "resume")
        self.assertEqual(player.position_ms, 28_500)

    def test_the_amount_is_configurable(self) -> None:
        player, calls = self.player(3.0)
        player.toggle(); calls.clear(); player.toggle()
        self.assertEqual(calls[0], ("seek", (27_000,)))

    def test_it_is_owed_once_and_not_again(self) -> None:
        """Two pauses in a row must not stack up three seconds of pre-roll."""
        player, calls = self.player(1.5)
        player.toggle(); player.toggle()          # pause, resume: the debt is paid
        calls.clear()
        player.toggle(); player.toggle()          # pause, resume again
        seeks = [call for call in calls if call[0] == "seek"]
        self.assertEqual(len(seeks), 1)

    def test_moving_deliberately_cancels_what_was_owed(self) -> None:
        """Skipping, scrubbing or clicking a turn already put the cursor where it was meant
        to be; stepping back from there would take the audio somewhere nobody asked for."""
        player, calls = self.player(1.5)
        player.toggle()                            # paused at 30.0s, 1.5s owed
        player.seek(50.0, play=False)
        player.position_ms = 50_000
        calls.clear()
        player.toggle()
        self.assertEqual([name for name, _ in calls], ["resume"])
        self.assertEqual(player.position_ms, 50_000)

    def test_zero_disables_it(self) -> None:
        player, calls = self.player(0.0)
        player.toggle(); calls.clear(); player.toggle()
        self.assertEqual([name for name, _ in calls], ["resume"], "no seek when disabled")
        self.assertEqual(player.position_ms, 30_000)

    def test_it_never_rewinds_past_the_start(self) -> None:
        self.assertEqual(rewind_target(500, 1.5), 0)
        self.assertEqual(rewind_target(0, 5.0), 0)

    def test_resuming_still_resumes_rather_than_reloading(self) -> None:
        player, calls = self.player(1.5)
        player.toggle()
        calls.clear()
        player.toggle()
        self.assertEqual([name for name, _ in calls][-1], "resume")

    def test_the_setting_carries_its_default(self) -> None:
        settings = AppState().settings
        self.assertTrue(settings.auto_rewind_enabled)
        self.assertEqual(settings.auto_rewind_seconds, 1.5)


class TimestampInsertionTests(unittest.TestCase):
    def test_the_stamp_lands_at_the_cursor(self) -> None:
        text, cursor = insert_timestamp("before after", 6, 3725)
        self.assertEqual(text, "before [01:02:05] after")
        # The cursor lands immediately after what was inserted, ready to keep typing.
        self.assertEqual(text[:cursor], "before [01:02:05]")
        self.assertEqual(text[cursor:], " after")

    def test_the_format_is_hh_mm_ss(self) -> None:
        self.assertEqual(format_stamp(0), "[00:00:00]")
        self.assertEqual(format_stamp(45.9), "[00:00:45]")
        self.assertEqual(format_stamp(3725), "[01:02:05]")
        self.assertEqual(format_stamp(7837.5), "[02:10:37]")

    def test_no_cursor_appends_at_the_end(self) -> None:
        text, cursor = insert_timestamp("a turn", None, 61)
        self.assertEqual(text, "a turn [00:01:01]")
        self.assertEqual(cursor, len(text))

    def test_an_empty_field_gets_a_bare_stamp(self) -> None:
        text, cursor = insert_timestamp("", 0, 5)
        self.assertEqual(text, "[00:00:05]")
        self.assertEqual(cursor, len(text))

    def test_the_cursor_is_clamped_to_the_text(self) -> None:
        text, _ = insert_timestamp("short", 999, 1)
        self.assertTrue(text.endswith("[00:00:01]"))
        text, _ = insert_timestamp("short", -5, 1)
        self.assertTrue(text.startswith("[00:00:01]"))

    def test_existing_spacing_is_not_doubled(self) -> None:
        text, _ = insert_timestamp("word ", 5, 1)
        self.assertEqual(text, "word [00:00:01]")

    def test_the_stamp_is_plain_text_so_it_exports(self) -> None:
        segment = untimed_turn(0, 0.0, 2.0, "original")
        text, _ = insert_timestamp(segment.text, None, 90)
        segment.corrected_text = text
        self.assertEqual(segment.text, "original [00:01:30]")
        self.assertIn("[00:01:30]", segment.to_dict()["corrected_text"])


class SpeedTests(unittest.TestCase):
    def test_the_offered_speeds(self) -> None:
        """Half speed to pick a word out of a mumble, double to skim what needs no check."""
        self.assertEqual(SPEEDS, (0.5, 0.75, 1.0, 1.25, 1.5, 2.0))
        self.assertIn(1.0, SPEEDS, "normal is always one of them")


if __name__ == "__main__": unittest.main()


