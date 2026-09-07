"""Turn merging and shell geometry.

Both are pure arithmetic over data structures, so they are checked here rather than by eye.
"""
from __future__ import annotations

import unittest

import design_tokens as t
from components.app_shell import measure
from models import TranscriptSegment, Word
from providers.base import MAX_TURN_GAP, merge_turns
from providers.deepgram import parse_response as deepgram_parse
from providers.gladia import parse_result as gladia_parse
from providers.openai_compatible import parse_response as compatible_parse


def utterance(speaker: int, start: float, end: float, text: str, confidence: float = .9) -> dict:
    return {"speaker": speaker, "start": start, "end": end, "confidence": confidence, "text": text,
            "words": [{"word": word, "start": start, "end": end, "confidence": confidence}
                      for word in text.split()]}


def gladia(*utterances: dict) -> dict:
    return {"status": "done", "result": {"transcription": {"utterances": list(utterances)}}}


class TurnMergeTests(unittest.TestCase):
    def test_consecutive_same_speaker_gladia_segments_collapse_into_one_turn(self) -> None:
        # The reported bug: one bubble per short phrase, a second apart.
        payload = gladia(utterance(0, 0.5, 1.1, "Bună"), utterance(0, 1.4, 2.0, "ziua"),
                         utterance(0, 2.3, 3.2, "tuturor."))
        segments = gladia_parse(payload)
        self.assertEqual(len(segments), 1)
        turn = segments[0]
        self.assertEqual(turn.original_text, "Bună ziua tuturor.")
        self.assertEqual(turn.speaker_id, "Speaker 1")
        # The merged turn must still describe the real span, or seek and export drift apart.
        self.assertEqual(turn.absolute_start, 0.5)
        self.assertEqual(turn.absolute_end, 3.2)
        self.assertEqual(turn.local_start, 0.5)
        self.assertEqual(turn.local_end, 3.2)
        self.assertEqual([word.text for word in turn.words], ["Bună", "ziua", "tuturor."])

    def test_a_speaker_change_always_starts_a_new_turn(self) -> None:
        payload = gladia(utterance(0, 0.0, 1.0, "Prima"), utterance(1, 1.1, 2.0, "A doua"),
                         utterance(0, 2.1, 3.0, "A treia"))
        segments = gladia_parse(payload)
        self.assertEqual([item.speaker_id for item in segments], ["Speaker 1", "Speaker 2", "Speaker 1"])

    def test_a_silence_longer_than_the_gap_starts_a_new_turn(self) -> None:
        payload = gladia(utterance(0, 0.0, 1.0, "Înainte"), utterance(0, 1.0 + MAX_TURN_GAP + .1, 4.0, "După"))
        segments = gladia_parse(payload)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].original_text, "Înainte")
        self.assertEqual(segments[1].absolute_start, 1.0 + MAX_TURN_GAP + .1)

    def test_a_gap_exactly_at_the_threshold_stays_in_the_same_turn(self) -> None:
        payload = gladia(utterance(0, 0.0, 1.0, "Prima"), utterance(0, 1.0 + MAX_TURN_GAP, 3.0, "parte"))
        self.assertEqual(len(gladia_parse(payload)), 1)

    def test_deepgram_utterances_merge_the_same_way(self) -> None:
        payload = {"results": {"utterances": [
            {"speaker": 0, "start": 0.0, "end": 0.6, "confidence": .9, "transcript": "Da", "words": []},
            {"speaker": 0, "start": 0.9, "end": 1.8, "confidence": .9, "transcript": "sigur.", "words": []},
            {"speaker": 1, "start": 2.0, "end": 3.0, "confidence": .8, "transcript": "Mulțumesc.", "words": []}]}}
        segments = deepgram_parse(payload)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].original_text, "Da sigur.")
        self.assertEqual(segments[0].absolute_end, 1.8)

    def test_confidence_is_weighted_by_duration(self) -> None:
        payload = gladia(utterance(0, 0.0, 3.0, "lung", 1.0), utterance(0, 3.2, 3.4, "scurt", 0.0))
        turn = gladia_parse(payload)[0]
        # 3.0s at 1.0 and 0.2s at 0.0 → far closer to 1.0 than a plain mean would give.
        self.assertAlmostEqual(turn.confidence or 0, 3.0 / 3.2, places=4)

    def test_a_single_segment_is_returned_untouched(self) -> None:
        only = TranscriptSegment(0, 0.0, "0", "Speaker 1", 1.0, 2.0, 1.0, 2.0, "Solo", None, False,
                                 [Word(1.0, 2.0, "Solo", .9)], .9)
        self.assertIs(merge_turns([only])[0], only)

    def test_empty_input_is_safe(self) -> None:
        self.assertEqual(merge_turns([]), [])

    def test_the_generic_endpoint_is_never_merged(self) -> None:
        """One default speaker plus zero timestamps would collapse into a single turn."""
        segments, timestamped = compatible_parse({"text": "First para.\n\nSecond para.\n\nThird para."})
        self.assertEqual(len(segments), 3)
        self.assertFalse(timestamped)
        segments, _ = compatible_parse({"segments": [{"start": 0.0, "end": 1.0, "text": "One"},
                                                     {"start": 1.1, "end": 2.0, "text": "Two"}]})
        self.assertEqual(len(segments), 2)


class ShellGeometryTests(unittest.TestCase):
    def test_panes_never_exceed_the_page_at_any_width(self) -> None:
        for width in (760, 800, 900, 1000, 1139, 1140, 1280, 1440, 1600, 1920, 2560, 3440):
            for wants in (False, True):
                with self.subTest(width=width, inspector=wants):
                    layout = measure(width, wants)
                    self.assertTrue(layout.fits, layout.describe())
                    self.assertLessEqual(layout.content, t.MAX_CONTENT)
                    self.assertLessEqual(layout.content, layout.workspace)

    def test_the_inspector_docks_only_at_or_above_the_breakpoint(self) -> None:
        self.assertEqual(t.INSPECTOR_BREAKPOINT,
                         t.NAV_WIDTH + t.WORKSPACE_MIN + t.INSPECTOR_WIDTH)
        self.assertFalse(measure(t.INSPECTOR_BREAKPOINT - 1, True).docked_inspector)
        self.assertTrue(measure(t.INSPECTOR_BREAKPOINT, True).docked_inspector)
        # Below the breakpoint the workspace keeps the full remainder; the inspector floats.
        self.assertEqual(measure(t.INSPECTOR_BREAKPOINT - 1, True).inspector, 0)
        self.assertEqual(measure(1139, True).workspace, 1139 - t.NAV_WIDTH)

    def test_the_workspace_never_drops_below_the_minimum_while_docked(self) -> None:
        for width in (1140, 1200, 1600, 2560):
            self.assertGreaterEqual(measure(width, True).workspace, t.WORKSPACE_MIN)

    def test_fixed_pane_widths(self) -> None:
        layout = measure(1600, True)
        self.assertEqual(layout.nav, 220)
        self.assertEqual(layout.inspector, t.INSPECTOR_WIDTH)
        self.assertEqual(layout.workspace, 1600 - 220 - t.INSPECTOR_WIDTH)

    def test_content_is_capped_and_gutters_are_symmetric(self) -> None:
        wide = measure(2560, False)
        self.assertEqual(wide.content, t.MAX_CONTENT)
        narrow = measure(900, False)
        self.assertEqual(narrow.content, 900 - t.NAV_WIDTH - 2 * t.CONTENT_GUTTER)


if __name__ == "__main__": unittest.main()
