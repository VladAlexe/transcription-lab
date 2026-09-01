"""Playback, seek precision, and reconnecting a saved project to its recording.

The transport methods in flet-audio are coroutines dispatched through `page.run_task`, so the
fakes here record `(method name, arguments)` instead of awaiting anything. That is enough to
prove seek is asked for the right millisecond.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app_controller import AppController
from audio_player import MAX_PRE_ROLL_SECONDS, PRE_ROLL_SECONDS, AudioPlayer, duration_to_ms, to_milliseconds
from document_export import project_payload
from models import AudioInfo, TranscriptSegment, Word


class _FakeAudio:
    """Stands in for flet_audio.Audio: same attribute and the same coroutine method names."""

    def __init__(self) -> None:
        self.src: str | None = None
        self.updated = 0

    def update(self) -> None: self.updated += 1
    async def play(self, position=0): ...
    async def pause(self): ...
    async def resume(self): ...
    async def seek(self, position): ...


def player_with_recording(tmp: Path, pre_roll: float = PRE_ROLL_SECONDS):
    """A bound player plus the list of transport calls it dispatched."""
    audio = _FakeAudio()
    calls: list[tuple[str, tuple]] = []
    recording = tmp / "WP1.m4a"
    recording.write_bytes(b"0" * 2048)

    def runner(function, *args): calls.append((function.__name__, args))

    player = AudioPlayer(audio, runner, pre_roll=pre_roll)
    player.bind(str(recording))
    return player, calls, recording


class SeekPrecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="player_")
        self.tmp = Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)

    def test_clicking_a_turn_seeks_to_its_exact_absolute_start_in_ms(self) -> None:
        player, calls, _ = player_with_recording(self.tmp)
        turn = TranscriptSegment(0, 0.0, "0", "Speaker 1", 0, 0, 1543.219, 1550.0, "Text")
        milliseconds = player.seek(turn.absolute_start)
        self.assertEqual(milliseconds, 1543219)
        # First interaction opens the source at the position; audioplayers needs play() first.
        self.assertEqual(calls[0], ("play", (1543219,)))
        # A later click on another turn issues a real seek.
        player.seek(42.5)
        self.assertIn(("seek", (42500,)), calls)

    def test_clicking_a_word_seeks_to_that_word_start(self) -> None:
        player, calls, _ = player_with_recording(self.tmp)
        word = Word(start=1550.004, end=1550.4, text="cuvânt", confidence=.9)
        self.assertEqual(player.seek(word.start), 1550004)
        self.assertEqual(calls[0], ("play", (1550004,)))

    def test_there_is_no_one_second_lead_in_any_more(self) -> None:
        self.assertEqual(PRE_ROLL_SECONDS, 0.0)
        self.assertLessEqual(MAX_PRE_ROLL_SECONDS, 0.25)
        player, _, _ = player_with_recording(self.tmp)
        self.assertEqual(player.seek(60.0), 60000, "seek must land on the real timestamp")

    def test_a_configured_pre_roll_is_clamped_to_the_maximum(self) -> None:
        player, _, _ = player_with_recording(self.tmp, pre_roll=1.0)
        self.assertEqual(player.pre_roll, MAX_PRE_ROLL_SECONDS)
        self.assertEqual(player.seek(60.0), 60000 - int(MAX_PRE_ROLL_SECONDS * 1000))

    def test_seeking_never_goes_below_zero(self) -> None:
        player, _, _ = player_with_recording(self.tmp, pre_roll=0.25)
        self.assertEqual(player.seek(0.0), 0)

    def test_millisecond_conversion_rounds_rather_than_truncates(self) -> None:
        self.assertEqual(to_milliseconds(1.2345), 1234)
        self.assertEqual(to_milliseconds(1.2346), 1235)
        self.assertEqual(to_milliseconds(-5), 0)

    def test_durations_from_flet_are_converted(self) -> None:
        class _Duration:
            days = 0; hours = 1; minutes = 5; seconds = 3; milliseconds = 250; microseconds = 0
        self.assertEqual(duration_to_ms(_Duration()), 3903250)
        self.assertEqual(duration_to_ms(None), 0)
        self.assertEqual(duration_to_ms(1500), 1500)

    def test_nothing_is_dispatched_when_no_audio_is_bound(self) -> None:
        audio = _FakeAudio(); calls: list = []
        player = AudioPlayer(audio, lambda fn, *a: calls.append(fn.__name__))
        self.assertIsNone(player.seek(12.0))
        player.toggle()
        self.assertEqual(calls, [], "an unbound player must stay silent, not crash")

    def test_play_pause_uses_one_control(self) -> None:
        player, calls, _ = player_with_recording(self.tmp)
        player.toggle()
        self.assertTrue(player.playing)
        self.assertEqual(calls[-1][0], "play")
        player.toggle()
        self.assertFalse(player.playing)
        self.assertEqual(calls[-1][0], "pause")
        player.toggle()
        self.assertEqual(calls[-1][0], "resume")

    def test_binding_a_missing_file_fails_cleanly(self) -> None:
        player = AudioPlayer(_FakeAudio(), lambda fn, *a: None)
        self.assertFalse(player.bind(str(self.tmp / "not_here.m4a")))
        self.assertFalse(player.bind(""))
        self.assertFalse(player.ready)


class ServiceRecreationTests(unittest.TestCase):
    """Assigning `src` to an attached service is ignored by the backend; it must be replaced.

    Measured: with the source set at construction the player reports on_loaded and a real
    duration and play() resolves; mutated after attach, nothing loads and play() hangs.
    """

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="recreate_")
        self.tmp = Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)
        self.first = self.tmp / "one.m4a"; self.first.write_bytes(b"0" * 512)
        self.second = self.tmp / "two.m4a"; self.second.write_bytes(b"0" * 512)
        self.built: list[str | None] = []
        self.attached: list[object] = []
        self.detached: list[object] = []

    def factory(self, path):
        self.built.append(path)
        audio = _FakeAudio()
        audio.src = path
        return audio

    def player(self):
        initial = self.factory(None)
        return AudioPlayer(initial, lambda fn, *a: None, factory=self.factory,
                           attach=self.attached.append, detach=self.detached.append)

    def test_binding_builds_a_new_service_with_the_source_already_set(self) -> None:
        player = self.player()
        original = player.audio
        self.assertTrue(player.bind(str(self.first)))
        self.assertIsNot(player.audio, original, "the service must be replaced, not mutated")
        self.assertEqual(player.audio.src, str(self.first.resolve()))
        self.assertEqual(self.built[-1], str(self.first.resolve()))

    def test_the_previous_service_is_detached_and_the_new_one_attached(self) -> None:
        player = self.player()
        original = player.audio
        player.bind(str(self.first))
        self.assertEqual(self.detached, [original])
        self.assertEqual(self.attached, [player.audio])

    def test_changing_recording_swaps_the_service_again(self) -> None:
        player = self.player()
        player.bind(str(self.first))
        first_service = player.audio
        player.bind(str(self.second))
        self.assertIsNot(player.audio, first_service)
        self.assertEqual(player.audio.src, str(self.second.resolve()))
        self.assertIn(first_service, self.detached)
        self.assertEqual(len(self.attached), 2)

    def test_every_service_the_player_owns_reports_back_to_it(self) -> None:
        player = self.player()
        player.bind(str(self.first))
        audio = player.audio
        # Bound methods are rebuilt on each attribute access, so compare by equality.
        self.assertEqual(audio.on_loaded, player.handle_loaded)
        self.assertEqual(audio.on_duration_change, player.handle_duration)
        self.assertEqual(audio.on_position_change, player.handle_position)
        self.assertEqual(audio.on_state_change, player.handle_state)

    def test_a_failed_bind_leaves_the_current_service_alone(self) -> None:
        player = self.player()
        player.bind(str(self.first))
        current = player.audio
        self.assertFalse(player.bind(str(self.tmp / "missing.m4a")))
        self.assertIs(player.audio, current)
        self.assertEqual(len(self.attached), 1)

    def test_unbinding_detaches_the_service(self) -> None:
        player = self.player()
        player.bind(str(self.first))
        bound = player.audio
        player.unbind()
        self.assertIn(bound, self.detached)
        self.assertFalse(player.ready)

    def recording_player(self):
        calls: list[tuple[str, tuple]] = []
        initial = self.factory(None)
        player = AudioPlayer(initial, lambda fn, *a: calls.append((fn.__name__, a)),
                             factory=self.factory, attach=self.attached.append,
                             detach=self.detached.append)
        return player, calls

    def test_a_request_made_before_the_source_opens_is_queued_not_sent(self) -> None:
        """Sending play() before the backend opened the source blocks 10s and then raises."""
        player, calls = self.recording_player()
        player.bind(str(self.first))
        self.assertFalse(player.loaded)
        self.assertEqual(player.seek(1543.219), 1543219, "the caller still gets the position")
        self.assertEqual(calls, [], "nothing may reach a backend that has no source yet")

    def test_the_queued_request_is_replayed_once_the_source_is_open(self) -> None:
        player, calls = self.recording_player()
        player.bind(str(self.first))
        player.seek(1543.219)
        player.handle_loaded(None)
        self.assertEqual(calls, [("play", (1543219,))], "seek arithmetic is unchanged")
        self.assertTrue(player.playing)

    def test_duration_also_unblocks_the_transport(self) -> None:
        class _Event:
            duration = 10_000
        player, calls = self.recording_player()
        player.bind(str(self.first))
        player.seek(42.5)
        player.handle_duration(_Event())
        self.assertEqual(calls, [("play", (42500,))])

    def test_after_loading_seeks_go_straight_through(self) -> None:
        player, calls = self.recording_player()
        player.bind(str(self.first))
        player.handle_loaded(None)
        self.assertEqual(player.seek(1543.219), 1543219)
        self.assertEqual(calls[0], ("play", (1543219,)))
        player.seek(42.5)
        self.assertIn(("seek", (42500,)), calls)

    def test_pressing_play_while_loading_starts_when_ready(self) -> None:
        player, calls = self.recording_player()
        player.bind(str(self.first))
        player.toggle()
        self.assertTrue(player.playing, "the button reflects the intent immediately")
        self.assertEqual(calls, [])
        player.handle_loaded(None)
        self.assertEqual(calls, [("play", (0,))])


class AudioReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="reference_")
        self.tmp = Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)
        self.recording = self.tmp / "WP1.m4a"
        self.recording.write_bytes(b"0" * 4096)
        self.info = AudioInfo(str(self.recording), "WP1.m4a", 4096, 7837.5, "aac", 48000, 2, 148000)
        self.segments = [TranscriptSegment(0, 0.0, "0", "Speaker 1", 0, 5, 12.5, 18.0, "Text", None, False,
                                           [Word(12.5, 13.0, "Text", .9)], .9)]

    def payload(self, include_path: bool = True) -> dict:
        return project_payload(self.info, [], self.segments, {"Speaker 1": "Moderator"},
                               "2026-07-19T12:00:00+03:00", {}, include_path, 2, "gladia", "gladia-v2")

    def write(self, payload: dict, name: str = "project.transcript.json") -> Path:
        path = self.tmp / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_saving_records_the_audio_reference_but_not_the_audio(self) -> None:
        payload = self.payload()
        self.assertEqual(payload["audio_path"], str(self.recording))
        self.assertEqual(payload["audio_filename"], "WP1.m4a")
        self.assertEqual(payload["audio_bytes"], 4096)
        raw = json.dumps(payload)
        self.assertLess(len(raw), 100_000, "the recording itself must never be embedded")

    def test_loading_a_project_with_a_valid_path_binds_the_audio_silently(self) -> None:
        controller = AppController()
        controller.load_project(str(self.write(self.payload())))
        self.assertFalse(controller.state.audio_missing)
        self.assertEqual(controller.state.audio_path, str(self.recording.resolve()))
        self.assertEqual(controller.state.audio_filename, "WP1.m4a")
        self.assertEqual(len(controller.state.transcript_segments), 1)

    def test_a_project_with_no_audio_path_still_loads_and_asks_to_reconnect(self) -> None:
        """The existing paid-run project: transcript intact, playback needs one manual step."""
        payload = self.payload()
        for key in ("audio_path", "source_path"):
            payload[key] = "" if key == "audio_path" else None
        payload["audio_metadata"]["path"] = ""
        controller = AppController()
        controller.load_project(str(self.write(payload, "no_audio.transcript.json")))
        # Everything except playback is present.
        self.assertEqual(len(controller.state.transcript_segments), 1)
        self.assertEqual(controller.state.speaker_mapping["Speaker 1"], "Moderator")
        self.assertEqual(controller.state.transcription_provider, "gladia")
        # And the banner condition is set.
        self.assertTrue(controller.state.audio_missing)
        self.assertFalse(controller.state.audio_banner_dismissed)
        self.assertEqual(controller.state.audio_filename, "WP1.m4a")
        self.assertEqual(controller.state.audio_bytes, 4096)

    def test_an_older_project_rebinds_from_source_path_when_audio_path_is_absent(self) -> None:
        payload = self.payload()
        del payload["audio_path"]          # written before this step existed
        controller = AppController()
        controller.load_project(str(self.write(payload, "older.transcript.json")))
        self.assertFalse(controller.state.audio_missing)
        self.assertEqual(controller.state.audio_path, str(self.recording.resolve()))

    def test_a_moved_recording_is_reported_missing(self) -> None:
        payload = self.payload()
        payload["audio_path"] = str(self.tmp / "moved" / "WP1.m4a")
        payload["source_path"] = None
        payload["audio_metadata"]["path"] = ""
        controller = AppController()
        controller.load_project(str(self.write(payload, "moved.transcript.json")))
        self.assertTrue(controller.state.audio_missing)
        self.assertEqual(len(controller.state.transcript_segments), 1, "the transcript still loads")

    def test_relocating_is_accepted_on_a_matching_name_or_size(self) -> None:
        controller = AppController()
        controller.state.audio_filename = "WP1.m4a"
        controller.state.audio_bytes = 4096
        renamed = self.tmp / "interview_copy.m4a"
        renamed.write_bytes(b"0" * 4096)             # different name, same size
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        moved = elsewhere / "WP1.m4a"
        moved.write_bytes(b"0" * 999)                # same name, different size
        mismatch = self.tmp / "other.m4a"
        mismatch.write_bytes(b"0" * 77)              # neither

        self.assertTrue(controller.audio_matches(str(self.recording)))
        self.assertTrue(controller.audio_matches(str(renamed)))
        self.assertTrue(controller.audio_matches(str(moved)))
        self.assertFalse(controller.audio_matches(str(mismatch)))
        self.assertFalse(controller.audio_matches(str(self.tmp / "absent.m4a")))

    def test_binding_after_relocation_clears_the_missing_flag(self) -> None:
        controller = AppController()
        controller.state.audio_missing = True
        self.assertTrue(controller.bind_audio(str(self.recording)))
        self.assertFalse(controller.state.audio_missing)
        self.assertEqual(controller.state.audio_path, str(self.recording.resolve()))

    def test_opening_a_project_never_rewrites_the_file(self) -> None:
        path = self.write(self.payload())
        before = path.read_bytes()
        stamp = path.stat().st_mtime
        AppController().load_project(str(path))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mtime, stamp)

    def test_the_export_still_honours_the_source_path_privacy_setting(self) -> None:
        without = self.payload(include_path=False)
        self.assertEqual(without["audio_path"], "")
        # Name and size are not sensitive and are what make a moved file re-identifiable.
        self.assertEqual(without["audio_filename"], "WP1.m4a")
        self.assertEqual(without["audio_bytes"], 4096)


if __name__ == "__main__": unittest.main()
