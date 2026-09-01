"""The design system, checked rather than remembered.

A style guide that lives only in a document drifts the moment two people edit two screens.
These are the rules stated as assertions: one accent per screen, one card, one type ladder,
one hit area. Breaking any of them fails here rather than in a screenshot months later.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import flet as ft
import design_tokens as t
import layout_audit
from app_state import AppState
from models import AudioInfo, TranscriptSegment, Word
from views import (export_view, recording_view, settings_view, speakers_view,
                   transcription_view, welcome_view)

noop = lambda *a, **k: None
ROOT = Path(__file__).resolve().parent.parent


def populated() -> AppState:
    state = AppState()
    state.selected_file_metadata = AudioInfo(r"C:\research\WP1.m4a", "WP1.m4a", 13_000_000, 7837.5,
                                             "aac", 48000, 2, 148000)
    state.selected_file_path = state.selected_file_metadata.path
    state.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i % 3}", f"SPEAKER_{i % 3}", i * 18, i * 18 + 14,
                          i * 18, i * 18 + 14, "A turn of ordinary length.", None, False,
                          [Word(i * 18, i * 18 + 1, "A", .93)], .93) for i in range(6)]
    state.speaker_mapping = {"SPEAKER_0": "Moderator", "SPEAKER_1": "Ana", "SPEAKER_2": "Radu"}
    state.activity_log = ["File analysed."]
    return state


def screens(state: AppState) -> dict[str, object]:
    return {
        "recording": lambda: recording_view.build(state, noop, noop, noop, noop,
                                                  lambda *a: (None, None), 960),
        "transcription": lambda: transcription_view.build(state, noop, noop, "01:12"),
        "speakers": lambda: speakers_view.build(state, noop, noop, noop, 1, 0, noop,
                                                {"rows": {}, "speakers": {}}, 960, noop, noop,
                                                noop, noop, noop),
        "export": lambda: export_view.build(state, noop, noop),
        "settings": lambda: settings_view.build(state, noop, noop, noop),
        "welcome": lambda: welcome_view.build(noop, noop),
    }


class AccentTests(unittest.TestCase):
    def test_each_screen_carries_exactly_one_filled_button(self) -> None:
        state = populated()
        for name, build in screens(state).items():
            with self.subTest(screen=name):
                filled = [c for c in layout_audit.walk(build())
                          if isinstance(c, ft.Button) and getattr(c, "bgcolor", None) == t.primary()]
                self.assertEqual(len(filled), 1,
                                 "one thing to do next; every other action stays quiet")

    def test_the_inspector_holds_no_filled_button_of_its_own(self) -> None:
        panel = speakers_view.inspector(populated(), 1, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop)
        filled = [c for c in layout_audit.walk(panel)
                  if isinstance(c, ft.Button) and getattr(c, "bgcolor", None) == t.primary()]
        self.assertEqual(filled, [], "the screen accent belongs to Continue to export")


class HitAreaTests(unittest.TestCase):
    def test_every_icon_button_is_forty_pixels(self) -> None:
        state = populated()
        for name, build in screens(state).items():
            with self.subTest(screen=name):
                for control in layout_audit.walk(build()):
                    if isinstance(control, ft.IconButton):
                        self.assertEqual(control.width, t.ICON_BUTTON, control.tooltip)
                        self.assertEqual(control.height, t.ICON_BUTTON, control.tooltip)

    def test_every_icon_button_says_what_it_does(self) -> None:
        state = populated()
        for name, build in screens(state).items():
            with self.subTest(screen=name):
                for control in layout_audit.walk(build()):
                    if isinstance(control, ft.IconButton):
                        self.assertTrue(control.tooltip, "an icon with no tooltip is a guess")


class CardTests(unittest.TestCase):
    """One card: same radius, same hairline, same inner padding, never flush to an edge."""

    def cards(self, control) -> list[ft.Container]:
        return [c for c in layout_audit.walk(control)
                if isinstance(c, ft.Container) and c.border_radius == t.R_LG and c.border is not None]

    def test_every_card_shares_one_inner_padding(self) -> None:
        state = populated()
        seen = set()
        for name, build in screens(state).items():
            for card in self.cards(build()):
                seen.add(str(card.padding))
        self.assertEqual(seen, {str(t.CARD_PADDING)}, f"cards disagree on padding: {seen}")

    def test_the_padding_is_inside_the_range_a_card_reads_well_at(self) -> None:
        self.assertGreaterEqual(t.CARD_PADDING, 16)
        self.assertLessEqual(t.CARD_PADDING, 20)

    def test_no_card_is_flush_to_the_content_edge(self) -> None:
        """The shell always gives the content column a gutter, so a card can never touch
        the workspace edge however wide the window is."""
        self.assertGreaterEqual(t.CONTENT_GUTTER, t.S16)


class TypeLadderTests(unittest.TestCase):
    def test_the_ladder_is_the_one_the_design_calls_for(self) -> None:
        self.assertEqual(t.TYPE_DISPLAY, 26, "screen title")
        self.assertEqual(t.TYPE_HEADING, 15, "section title")
        self.assertEqual(t.TYPE_BODY, 15, "body")
        self.assertEqual(t.TYPE_MONO, 11, "timestamps")
        self.assertEqual(t.LINE_HEIGHT, 1.4)

    def test_no_title_dwarfs_the_screen(self) -> None:
        self.assertLessEqual(t.TYPE_DISPLAY / t.TYPE_BODY, 2.0,
                             "a heading more than twice the body size shouts")

    def test_each_rung_is_distinguishable_from_the_next(self) -> None:
        ladder = sorted({t.TYPE_CAPTION, t.TYPE_LABEL, t.TYPE_SECONDARY, t.TYPE_BODY,
                         t.TYPE_TITLE, t.TYPE_DISPLAY})
        for smaller, larger in zip(ladder, ladder[1:]):
            self.assertGreaterEqual(larger - smaller, 1,
                                    f"{smaller} and {larger} are the same size to the eye")

    def test_timestamps_stay_quiet(self) -> None:
        self.assertLess(t.TYPE_MONO, t.TYPE_BODY, "a timestamp never competes with speech")


class PaletteTests(unittest.TestCase):
    """Colour comes from the palette, never from a literal typed into a screen."""

    SOURCES = sorted((ROOT / "views").glob("*.py")) + sorted((ROOT / "components").glob("*.py"))

    def test_no_screen_or_component_writes_a_raw_colour(self) -> None:
        for path in self.SOURCES:
            with self.subTest(module=path.name):
                literals = re.findall(r'"#[0-9A-Fa-f]{3,8}"', path.read_text(encoding="utf-8"))
                self.assertEqual(literals, [], f"{path.name} defines its own colour")

    def test_the_accent_is_the_sage_sampled_from_the_logo(self) -> None:
        for dark in (False, True):
            t.set_dark(dark)
            self.assertEqual(t.primary(), t.scheme(dark)["primary"])
        t.set_dark(False)
        self.assertEqual(t.SEED, "#5F7A68", "the interface accent is the darkened brand sage")

    def test_speaker_colours_do_not_borrow_the_accent_slot(self) -> None:
        """Speaker dots mark people, not states, so they must stay distinguishable without
        turning the transcript into a second palette."""
        colours = {t.speaker_color(i) for i in range(8)}
        self.assertEqual(len(colours), 8, "eight people, eight distinguishable dots")


if __name__ == "__main__": unittest.main()
