"""Tests for the optional transcription range: parsing, validation, extraction, provenance."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from audio_processing import range_command
from document_export import project_payload
from models import TranscriptSegment, Word
from time_range import TimeRange, TimeRangeError, describe, format_timecode, parse_timecode, resolve, shift_segments

DURATION = 7837.5  # a real two-hour group interview


class TimecodeTests(unittest.TestCase):
    def test_accepted_formats(self) -> None:
        self.assertEqual(parse_timecode("90"), 90.0)
        self.assertEqual(parse_timecode("12:30"), 750.0)
        self.assertEqual(parse_timecode("01:12:30"), 4350.0)
        self.assertEqual(parse_timecode(" 00:00:05 "), 5.0)

    def test_empty_means_not_set(self) -> None:
        self.assertIsNone(parse_timecode(""))
        self.assertIsNone(parse_timecode("   "))

    def test_rejected_formats(self) -> None:
        for text in ("abc", "1:2:3:4", "-5", "12:99", "1:75:00", "12,30"):
            with self.subTest(text=text):
                with self.assertRaises(TimeRangeError): parse_timecode(text)

    def test_formatting_round_trip(self) -> None:
        self.assertEqual(format_timecode(4350), "01:12:30")
        self.assertEqual(parse_timecode(format_timecode(4350)), 4350.0)


class RangeValidationTests(unittest.TestCase):
    def test_both_empty_means_the_whole_file(self) -> None:
        self.assertIsNone(resolve("", "", DURATION))

    def test_only_start_runs_to_the_end(self) -> None:
        selection = resolve("12:00", "", DURATION)
        self.assertEqual(selection.start, 720.0)
        self.assertEqual(selection.end, DURATION)

    def test_only_end_starts_at_zero(self) -> None:
        selection = resolve("", "35:00", DURATION)
        self.assertEqual(selection.start, 0.0)
        self.assertEqual(selection.end, 2100.0)

    def test_start_must_precede_end(self) -> None:
        with self.assertRaises(TimeRangeError) as caught: resolve("35:00", "12:00", DURATION)
        self.assertIn("before", str(caught.exception))

    def test_range_must_fall_inside_the_recording(self) -> None:
        with self.assertRaises(TimeRangeError) as caught: resolve("00:10", "99:99:99", DURATION)
        self.assertTrue(str(caught.exception))
        with self.assertRaises(TimeRangeError): resolve("10:00:00", "", DURATION)

    def test_degenerate_range_is_rejected(self) -> None:
        with self.assertRaises(TimeRangeError): resolve("12:00", "12:00", DURATION)
        with self.assertRaises(TimeRangeError): resolve("12:00", "12:00.5", DURATION)

    def test_full_span_collapses_back_to_the_whole_file(self) -> None:
        self.assertIsNone(resolve("00:00", format_timecode(DURATION), DURATION))

    def test_description_reports_both_cases(self) -> None:
        self.assertIn("full recording", describe(None, DURATION))
        text = describe(TimeRange(720.0, 2100.0), DURATION)
        self.assertIn("00:12:00", text)
        self.assertIn("00:35:00", text)


class ShiftTests(unittest.TestCase):
    def segment(self) -> TranscriptSegment:
        return TranscriptSegment(0, 0.0, "0", "Speaker 1", 5.0, 9.0, 5.0, 9.0, "Text", None, False,
                                 [Word(5.0, 6.0, "Text", 0.9)], 0.9)

    def test_absolute_times_are_reanchored_on_the_original_recording(self) -> None:
        item = self.segment()
        shift_segments([item], 720.0)
        self.assertEqual(item.absolute_start, 725.0)
        self.assertEqual(item.absolute_end, 729.0)
        self.assertEqual(item.chunk_start_offset, 720.0)
        self.assertEqual(item.words[0].start, 725.0)
        # Clip-relative positions stay untouched; only the recording timeline moves.
        self.assertEqual(item.local_start, 5.0)

    def test_zero_offset_changes_nothing(self) -> None:
        item = self.segment()
        shift_segments([item], 0.0)
        self.assertEqual(item.absolute_start, 5.0)
        self.assertEqual(item.words[0].start, 5.0)


class ExtractionCommandTests(unittest.TestCase):
    def test_stream_copy_command(self) -> None:
        command = range_command("ffmpeg.exe", Path("in.m4a"), Path("out.m4a"), 720.0, 2100.0, True)
        self.assertIn("-ss", command)
        self.assertEqual(command[command.index("-ss") + 1], "720.000")
        self.assertEqual(command[command.index("-t") + 1], "1380.000")
        self.assertEqual(command[command.index("-c:a") + 1], "copy")

    def test_reencode_command_matches_the_fragment_profile(self) -> None:
        command = range_command("ffmpeg.exe", Path("in.wav"), Path("out.m4a"), 0.0, 60.0, False, 64)
        self.assertEqual(command[command.index("-c:a") + 1], "aac")
        self.assertEqual(command[command.index("-b:a") + 1], "64k")
        self.assertEqual(command[command.index("-ar") + 1], "16000")


class RangeProvenanceTests(unittest.TestCase):
    def test_range_is_recorded_in_the_saved_project(self) -> None:
        payload = project_payload(None, [], [], {}, "date", {}, False, 2, "gladia", "gladia-v2", 720.0, 2100.0)
        self.assertEqual(payload["transcription_range_start"], 720.0)
        self.assertEqual(payload["transcription_range_end"], 2100.0)

    def test_whole_file_runs_record_no_range(self) -> None:
        payload = project_payload(None, [], [], {}, "date")
        self.assertIsNone(payload["transcription_range_start"])
        self.assertIsNone(payload["transcription_range_end"])

    def test_saved_range_survives_a_round_trip(self) -> None:
        from app_controller import AppController
        import tempfile
        payload = project_payload(None, [], [], {}, "date", {}, False, 2, "gladia", "gladia-v2", 720.0, 2100.0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ranged.transcript.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            controller = AppController()
            controller.load_project(str(path))
        self.assertEqual(controller.state.range_start, 720.0)
        self.assertEqual(controller.state.range_end, 2100.0)
        selection = controller.selected_range()
        self.assertEqual((selection.start, selection.end), (720.0, 2100.0))


if __name__ == "__main__": unittest.main()
