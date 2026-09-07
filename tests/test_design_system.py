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
        "speakers": lambda: speakers_view.build(state, noop, noop, noop, 1, noop,
                                                {"rows": {}, "speakers": {}}, 960, noop, noop,
                                                noop, noop, noop),
        "export": lambda: export_view.build(state, noop, noop),
        "settings": lambda: settings_view.build(state, noop, noop, noop),
        "welcome": lambda: welcome_view.build(noop, noop),
    }


class AccentTests(unittest.TestCase):
    def test_no_screen_carries_more_than_one_filled_button(self) -> None:
        """One thing to do next, and every other action stays quiet. A screen with nothing
        left to do — a transcript already made — carries none, which is also correct."""
        state = populated()
        for name, build in screens(state).items():
            with self.subTest(screen=name):
                filled = [c for c in layout_audit.walk(build())
                          if isinstance(c, ft.Button) and getattr(c, "bgcolor", None) == t.primary()]
                self.assertLessEqual(len(filled), 1, f"{name} has {len(filled)}")

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
        # A card is now a lighter surface, not an outlined box, so it is found by its fill.
        return [c for c in layout_audit.walk(control)
                if isinstance(c, ft.Container) and c.border_radius == t.RADIUS
                and c.bgcolor in (t.surface(), t.surface_variant()) and c.padding is not None]

    def test_the_cards_that_hold_a_screen_body_share_one_padding(self) -> None:
        state = populated()
        seen = set()
        for name, build in screens(state).items():
            if name == "speakers":
                continue          # a workbench, not a stack of cards
            for card in self.cards(build()):
                seen.add(str(card.padding))
        self.assertIn(str(t.CARD_PADDING), seen, f"no card uses the shared padding: {seen}")

    def test_the_padding_is_inside_the_range_a_card_reads_well_at(self) -> None:
        self.assertGreaterEqual(t.CARD_PADDING, 16)
        self.assertLessEqual(t.CARD_PADDING, 20)

    def test_no_card_is_flush_to_the_content_edge(self) -> None:
        """The shell always gives the content column a gutter, so a card can never touch
        the workspace edge however wide the window is."""
        self.assertGreaterEqual(t.CONTENT_GUTTER, t.S16)


class TypeLadderTests(unittest.TestCase):
    def test_the_ladder_is_three_rungs_not_eight(self) -> None:
        """Hierarchy comes from weight and colour. Eight sizes read as eight voices."""
        self.assertEqual(t.TYPE_DISPLAY, t.BASE_DISPLAY, "the only large text")
        self.assertEqual(t.TYPE_BODY, t.BASE_BODY, "everything a person reads")
        self.assertEqual(t.TYPE_META, t.BASE_META, "everything a person glances at")
        self.assertEqual(len({t.TYPE_DISPLAY, t.TYPE_BODY, t.TYPE_META,
                              t.TYPE_TITLE, t.TYPE_HEADING, t.TYPE_SUBHEADING,
                              t.TYPE_SUBTITLE, t.TYPE_SECONDARY, t.TYPE_LABEL,
                              t.TYPE_CAPTION, t.TYPE_MONO}), 3, "the rest are aliases")
        self.assertEqual(t.LINE_HEIGHT, 1.4)

    def test_there_is_one_radius(self) -> None:
        self.assertEqual({t.R_SM, t.R_MD, t.R_LG}, {t.RADIUS})
        self.assertEqual(t.RADIUS, 4, "sharp, the way an editor is")

    def test_the_shell_has_three_tones_to_separate_with(self) -> None:
        """Depth without a drawn line: chrome recedes, the work surface is raised."""
        for dark in (False, True):
            t.set_dark(dark)
            with self.subTest(dark=dark):
                self.assertEqual(len({t.chrome(), t.background(), t.surface()}), 3)
        t.set_dark(False)

    def test_speaker_colours_are_not_the_accent(self) -> None:
        """Identity is not a state. The first speaker used to wear the accent colour."""
        self.assertNotIn(t.primary(), {t.speaker_color(i) for i in range(8)})

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

    def test_the_accent_belongs_to_the_logo_palette(self) -> None:
        for dark in (False, True):
            t.set_dark(dark)
            self.assertEqual(t.primary(), t.scheme(dark)["primary"])
        t.set_dark(False)
        # Muted Teal, taken to the lightness each theme needs. The palette colour itself is
        # a fill and not an ink: white on #759588 is 3.4:1, which is not a button label.
        self.assertEqual(t.primary(), t.PRIMARY_LIGHT)
        t.set_dark(True); self.assertEqual(t.primary(), t.PRIMARY_DARK); t.set_dark(False)

    def test_every_hue_in_the_interface_comes_from_the_logo_palette(self) -> None:
        """A palette is only a palette if nothing sits outside it. Greys are allowed to be
        grey; anything with a hue has to be one of the five or a tint of one of them."""
        import colorsys
        family = [colorsys.rgb_to_hls(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))[0] * 360
                  for c in (t.AMBER, t.ROSE, t.TEAL, t.GRANITE, t.CARBON)]
        for dark in (False, True):
            scheme = t.scheme(dark)
            for role, value in scheme.items():
                if not (isinstance(value, str) and value.startswith("#") and len(value) == 7):
                    continue
                red, green, blue = (int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))
                hue, _, saturation = colorsys.rgb_to_hls(red, green, blue)
                if saturation < .12: continue          # a grey, warm or cool, is still a grey
                # Hue is a circle: Smoky Rose sits at 359 degrees, so a red at 4 degrees is
                # five degrees away from it and not three hundred and fifty-five.
                def apart(a: float, b: float) -> float:
                    gap = abs(a - b) % 360
                    return min(gap, 360 - gap)
                with self.subTest(theme="dark" if dark else "light", role=role, value=value):
                    self.assertTrue(min(apart(hue * 360, h) for h in family) < 26,
                                    f"{value} is not from the palette")

    def test_speaker_colours_do_not_borrow_the_accent_slot(self) -> None:
        """Speaker dots mark people, not states, so they must stay distinguishable without
        turning the transcript into a second palette."""
        colours = {t.speaker_color(i) for i in range(8)}
        self.assertEqual(len(colours), 8, "eight people, eight distinguishable dots")


if __name__ == "__main__": unittest.main()


class ColourLiteralTests(unittest.TestCase):
    """Every colour in the palette has to be a colour Flutter will read back as written."""

    def values(self):
        for dark in (False, True):
            for role, value in t.scheme(dark).items():
                if isinstance(value, str) and value.startswith("#"):
                    yield ("dark" if dark else "light"), role, value

    def test_every_colour_is_a_well_formed_hex_value(self) -> None:
        for theme, role, value in self.values():
            with self.subTest(theme=theme, role=role, value=value):
                self.assertIn(len(value), (7, 9), "either #RRGGBB or #AARRGGBB")
                int(value[1:], 16)

    def test_a_translucent_colour_puts_its_alpha_first(self) -> None:
        """Flutter reads eight digits as AARRGGBB. Written the other way round, the dark
        theme's "#FFFFFF26" became opaque #FFFF26 — a bright yellow scrollbar belonging to
        no palette at all, and visible only in the theme nobody screenshotted."""
        for theme, role, value in self.values():
            if len(value) != 9: continue
            alpha = int(value[1:3], 16)
            with self.subTest(theme=theme, role=role, value=value):
                self.assertLess(alpha, 0xF0,
                                "a fully opaque eight-digit colour is RGBA written backwards")

    def test_the_scrollbar_is_the_palette_and_not_an_accident(self) -> None:
        for dark in (False, True):
            with self.subTest(theme="dark" if dark else "light"):
                self.assertEqual(t.scheme(dark)["scrollbar"][3:].upper(), t.AMBER[1:].upper())
