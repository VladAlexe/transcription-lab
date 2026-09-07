"""The design system, and the four defects the screenshot showed.

Everything here is a rule the previous interface broke: eight meanings for one colour,
twenty hairlines where three tones would do, a transcript clipped to thirty characters, a
progress bar too small to see, and a counter that pointed at most of the interview.
"""
from __future__ import annotations

import unittest

import flet as ft
import design_tokens as t
import layout_audit
import playback_sync
import strings as s
from app_state import AppState
from components.app_shell import measure
from components.transcript_list import transcript_item
from models import TranscriptSegment, Word
from views import speakers_view

noop = lambda *a, **k: None


def turn(index: int = 0, text: str = "A turn of the length these interviews produce.",
         confidence: float = .9) -> TranscriptSegment:
    return TranscriptSegment(0, 0.0, f"raw{index}", f"SPEAKER_{index % 2}", index * 10,
                             index * 10 + 8, index * 10, index * 10 + 8, text, None, False,
                             [Word(index * 10, index * 10 + 1, "A", confidence)], confidence)


def state(count: int = 6) -> AppState:
    made = AppState()
    made.transcript_segments = [turn(i) for i in range(count)]
    return made


class ReadableTranscriptTests(unittest.TestCase):
    """The one thing the application exists for was the one thing you could not read."""

    def test_a_turn_shows_two_full_lines(self) -> None:
        row = transcript_item(0, turn(), {}, t.speaker_color(0), False, 640, noop, {})
        body = [c for c in layout_audit.walk(row)
                if isinstance(c, ft.Text) and c.max_lines == t.TURN_LINES]
        self.assertEqual(len(body), 1)
        self.assertEqual(t.TURN_LINES, 2)

    def test_the_text_spans_the_column_it_is_given(self) -> None:
        row = transcript_item(0, turn(), {}, t.speaker_color(0), False, 640, noop, {})
        reading = [c for c in layout_audit.walk(row)
                   if isinstance(c, ft.Container) and c.width == 640]
        self.assertEqual(len(reading), 1, "no timestamp gutter eating into it")

    def test_the_transcript_keeps_a_column_it_can_be_read_in(self) -> None:
        """It used to be the narrowest thing on screen, at about thirty characters a line.

        It is no longer required to be the widest: correcting a sentence is what this screen
        is for, so the editing pane may take more than the list of turns you are choosing
        between. What the transcript keeps is a floor — wider than the speaker list, wider
        than the rail, and never below the declared minimum.
        """
        for page in (1268, 1600, 2000):
            with self.subTest(width=page):
                layout = measure(page, True, False, True, wide=True)
                identities = (t.IDENTITY_PANE_WIDTH
                              if speakers_view.identity_column_fits(layout.content) else 0)
                transcript = layout.content - (identities + t.S12 if identities else 0)
                self.assertGreater(transcript, identities, "wider than the speaker list")
                self.assertGreater(transcript, layout.nav, "wider than the rail")
                self.assertGreaterEqual(transcript, t.TRANSCRIPT_MIN_COLUMN)

    def test_the_editing_pane_is_the_widest_declared_pane(self) -> None:
        """Reading a turn is choosing one; correcting it is the work. The pane the work
        happens in is the one that gets the room."""
        self.assertGreater(t.INSPECTOR_WIDTH, t.IDENTITY_PANE_WIDTH)
        self.assertGreater(t.INSPECTOR_WIDTH, t.NAV_WIDTH)

    def test_the_rail_stopped_being_a_column(self) -> None:
        """Four destinations did not need two hundred and twenty pixels of chrome."""
        self.assertLessEqual(t.NAV_MINIMISED, 80)
        self.assertLess(measure(1268, True, False, True).nav, t.NAV_WIDTH)


class OneSystemTests(unittest.TestCase):
    def test_one_radius(self) -> None:
        self.assertEqual({t.R_SM, t.R_MD, t.R_LG}, {t.RADIUS})

    def test_the_whole_interface_resizes_from_one_number(self) -> None:
        """A transcript is nothing but text, so text size is a real preference."""
        try:
            for scale in (0.9, 1.15, 1.3):
                t.set_type_scale(scale)
                with self.subTest(scale=scale):
                    self.assertAlmostEqual(t.TYPE_BODY, round(t.BASE_BODY * scale, 1))
                    self.assertAlmostEqual(t.TYPE_META, t.TYPE_LABEL)
            t.set_type_scale(3.0)
            self.assertAlmostEqual(t.TYPE_BODY, round(t.BASE_BODY * 1.4, 1),
                                   msg="clamped at the top of the range")
        finally:
            t.set_type_scale(1.0)

    def test_three_type_sizes(self) -> None:
        sizes = {t.TYPE_DISPLAY, t.TYPE_BODY, t.TYPE_META, t.TYPE_TITLE, t.TYPE_HEADING,
                 t.TYPE_SUBHEADING, t.TYPE_SUBTITLE, t.TYPE_SECONDARY, t.TYPE_LABEL,
                 t.TYPE_CAPTION, t.TYPE_MONO}
        self.assertEqual(len(sizes), 3, f"eight rungs read as eight voices: {sorted(sizes)}")

    def test_three_tones_in_both_themes(self) -> None:
        for dark in (False, True):
            t.set_dark(dark)
            with self.subTest(dark=dark):
                self.assertEqual(len({t.chrome(), t.background(), t.surface()}), 3)
        t.set_dark(False)

    def test_the_shell_separates_by_tone_and_one_hairline_seam(self) -> None:
        """Chrome tone carries the separation and a single hairline sharpens it.

        This used to insist on tone alone. An editor rules the edges of its panels, and
        without them the sidebar and the transport bar melted into the work beside them —
        so the rule now is a seam of exactly one pixel in the outline colour, never heavier
        and never a second colour of its own.
        """
        from audio_player import AudioPlayer
        from components.audio_transport import audio_transport
        from components.navigation_rail import navigation_rail
        rail = navigation_rail(state(), noop, noop, noop, noop, True, noop)
        player = audio_transport(AudioPlayer(None, lambda fn, *a: fn(*a)), {}, noop, noop)
        for name, control in (("rail", rail), ("player", player)):
            with self.subTest(part=name):
                self.assertEqual(control.bgcolor, t.chrome())
                sides = [control.border.top, control.border.right,
                         control.border.bottom, control.border.left]
                drawn = [side for side in sides if side.width]
                self.assertEqual(len(drawn), 1, "one seam, not a frame")
                self.assertEqual(drawn[0].width, t.HAIRLINE)
                self.assertEqual(drawn[0].color, t.outline())

    def test_the_accent_no_longer_means_identity(self) -> None:
        """It meant eight things at once, so it drew attention to none of them."""
        self.assertNotIn(t.primary(), {t.speaker_color(i) for i in range(8)})


class DefectTests(unittest.TestCase):
    def test_the_speaker_select_shows_the_speaker(self) -> None:
        """It showed its own floating label where the name should have been."""
        panel = speakers_view.inspector(state(), 0, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop)
        select = layout_audit.find(panel, lambda c: isinstance(c, ft.Dropdown))[0]
        self.assertIsNone(select.label, "the label was what was being displayed")
        self.assertEqual(select.value, "SPEAKER_0")
        self.assertIn("SPEAKER_0", [option.key for option in select.options])

    def test_progress_is_a_ring_you_can_see(self) -> None:
        from components.review_strip import review_strip
        from review_progress import Progress
        strip = review_strip(Progress(41, 312), False, noop, noop, "00:12:16", {})
        rings = layout_audit.find(strip, lambda c: isinstance(c, ft.ProgressRing))
        self.assertEqual(len(rings), 1)
        self.assertGreaterEqual(rings[0].width, 20, "a 4px bar at 13% was invisible")

    def test_the_project_name_can_use_the_width_of_the_bar(self) -> None:
        from components.top_bar import top_bar
        from models import AudioInfo
        made = state()
        name = "Marius Culoaru interviu.m4a"
        made.selected_file_metadata = AudioInfo(name, name, 1, 1, "aac", 16000, 1, 1)
        bar = top_bar(made, noop, noop, noop, {}, noop, noop, noop, False, noop)
        shown = [c for c in layout_audit.walk(bar)
                 if isinstance(c, ft.Text) and c.value == name]
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0].tooltip, name, "readable in full even when clipped")

    def test_saving_is_not_offered_twice(self) -> None:
        from components.navigation_rail import navigation_rail
        rail = navigation_rail(state(), noop, noop, noop, noop, False, noop)
        saves = [c for c in layout_audit.find(rail, lambda c: isinstance(c, ft.IconButton))
                 if c.tooltip == s.SAVE_PROJECT]
        self.assertEqual(saves, [], "it is a labelled button in the top bar")


if __name__ == "__main__": unittest.main()


class SpeedTests(unittest.TestCase):
    """Changing speed used to tear the service down and reload the recording."""

    class _Fake:
        src = "r.m4a"
        playback_rate = 1.0
        def __init__(self): self.updates = 0; self.calls = []
        def update(self): self.updates += 1
        def play(self, position=0): self.calls.append("play")
        def resume(self): self.calls.append("resume")
        def pause(self): self.calls.append("pause")
        def seek(self, position): self.calls.append("seek")

    def player(self):
        from audio_player import AudioPlayer
        made = AudioPlayer(self._Fake(), lambda fn, *a: fn(*a))
        made.path = "r.m4a"; made.loaded = True; made._started = True
        made.duration_ms = 600_000; made.position_ms = 123_456; made.playing = True
        return made

    def test_the_rate_changes_on_the_live_service(self) -> None:
        made = self.player()
        made.set_speed(1.5)
        self.assertEqual(made.audio.playback_rate, 1.5)
        self.assertEqual(made.audio.updates, 1)

    def test_nothing_reloads_and_nothing_is_lost(self) -> None:
        """A 130 MB file was being reloaded to change a number, so playback stopped, the
        position was restored by guesswork and the audio stuttered back to life."""
        made = self.player()
        before = list(made.audio.calls)
        made.set_speed(0.5)
        self.assertEqual(made.audio.calls, before, "no play, no seek, no reload")
        self.assertEqual(made.position_ms, 123_456)
        self.assertTrue(made.playing)
        self.assertEqual(made.path, "r.m4a")

    def test_the_same_rate_twice_does_nothing(self) -> None:
        made = self.player()
        made.set_speed(1.0)
        self.assertEqual(made.audio.updates, 0)

    def test_a_rebuilt_service_is_born_at_the_chosen_rate(self) -> None:
        """Otherwise the rate silently resets whenever the source is rebound."""
        import ast, inspect, main
        source = inspect.getsource(main.DesktopApp.new_audio_service)
        call = next(n for n in ast.walk(ast.parse(source.strip()))
                    if isinstance(n, ast.Call) and "Audio" in ast.unparse(n.func))
        self.assertIn("playback_rate", {kw.arg for kw in call.keywords})


class HelpTextTests(unittest.TestCase):
    def test_it_explains_the_decisions_not_the_buttons(self) -> None:
        import strings as s
        steps = " ".join(s.HELP_STEPS).lower()
        for idea in ("never modified", "memory for this session", "only to that provider",
                     "confidence"):
            with self.subTest(idea=idea):
                self.assertIn(idea, steps)

    def test_reopening_says_what_comes_back(self) -> None:
        import strings as s
        steps = " ".join(s.HELP_OPEN_STEPS).lower()
        for idea in ("comments", "how far you had checked", "resume", "no api credit"):
            with self.subTest(idea=idea):
                self.assertIn(idea, steps)


class PanelWidthTests(unittest.TestCase):
    """The editing box has to fill the panel it sits in."""

    def panel(self):
        made = state(3)
        return speakers_view.inspector(made, 0, noop, noop, noop, {}, None, noop, noop,
                                       noop, noop, noop)

    def test_the_panel_stretches_its_children(self) -> None:
        """A Column left at its default gives every child its intrinsic width, so the box
        sat at whatever a TextField asks for however wide the panel grew. Widening the
        panel could never have fixed it."""
        self.assertEqual(self.panel().horizontal_alignment, ft.CrossAxisAlignment.STRETCH)

    def test_nothing_in_the_panel_pins_its_own_width(self) -> None:
        for control in layout_audit.walk(self.panel()):
            if isinstance(control, (ft.TextField, ft.Dropdown)):
                with self.subTest(control=type(control).__name__):
                    self.assertIsNone(control.width, "it must take the column's width")

    def test_the_box_is_nearly_as_wide_as_the_panel(self) -> None:
        usable = t.INSPECTOR_WIDTH - 2 * t.INSPECTOR_PADDING
        self.assertGreater(usable / t.INSPECTOR_WIDTH, .9, "padding, not a second margin")
        self.assertGreaterEqual(usable, 380)


class EditorChromeTests(unittest.TestCase):
    def test_the_scrollbar_is_a_hairline_with_no_track(self) -> None:
        from theme import application_theme
        for dark in (False, True):
            with self.subTest(dark=dark):
                bar = application_theme(dark).scrollbar_theme
                self.assertLessEqual(bar.thickness, 8)
                self.assertEqual(bar.track_color, ft.Colors.TRANSPARENT)
                self.assertFalse(bar.track_visibility)

    def test_the_scrollbar_follows_the_theme_being_built(self) -> None:
        """Not the theme that happens to be active — a function reading global state
        instead of its own argument gave both themes the same thumb."""
        from theme import application_theme
        light = application_theme(False).scrollbar_theme.thumb_color
        dark = application_theme(True).scrollbar_theme.thumb_color
        self.assertNotEqual(light, dark)

    def test_the_chrome_is_an_editors_height(self) -> None:
        self.assertLessEqual(t.TOP_BAR_HEIGHT, 48)
        self.assertLessEqual(t.PLAYER_BAR_HEIGHT, 44)
        self.assertLessEqual(t.NAV_MINIMISED, 56)
        self.assertLessEqual(t.RADIUS, 4)

    def test_the_current_destination_is_marked_on_the_edge(self) -> None:
        """An activity bar marks the current place with a bar, not a filled pill."""
        from components.navigation_rail import navigation_rail
        rail = navigation_rail(state(3), noop, noop, noop, noop, True, noop)
        marked = [c for c in layout_audit.walk(rail)
                  if isinstance(c, ft.Container) and c.border is not None
                  and getattr(c.border, "left", None) is not None
                  and c.border.left.color == t.primary()]
        self.assertTrue(marked, "the selected destination carries the edge")


class NestedStretchTests(unittest.TestCase):
    """The editing box has to fill the panel, through every column between them."""

    def panel(self, words: bool = False):
        made = state(3)
        return speakers_view.inspector(made, 0, noop, noop, noop, {}, None, noop, noop,
                                       noop, noop, noop, words_mode=words, on_words_mode=noop)

    def test_every_column_in_the_panel_stretches(self) -> None:
        """Fixing only the outer one left the box at its intrinsic width: a Column's
        alignment does not reach through a Column nested inside it."""
        for control in layout_audit.walk(self.panel()):
            if isinstance(control, ft.Column):
                with self.subTest(children=[type(x).__name__ for x in (control.controls or [])][:4]):
                    self.assertEqual(control.horizontal_alignment,
                                     ft.CrossAxisAlignment.STRETCH)

    def test_the_mode_tabs_keep_their_own_width_inside_the_strip(self) -> None:
        """The strip spans the panel, the way an editor's tab bar does. The tabs inside it
        must not: two options stretched to half a panel each is a segmented control, not a
        pair of tabs, and it was the previous look."""
        from views.speakers_view import mode_switch
        strip = mode_switch(False, noop)
        tabs = [c for c in (strip.content.controls or []) if getattr(c, "padding", None)]
        self.assertEqual(len(tabs), 2)
        for tab in tabs:
            self.assertIsNone(tab.width)
            self.assertFalse(tab.expand)


class EditorLookTests(unittest.TestCase):
    def test_panel_headers_are_small_upper_case_and_letter_spaced(self) -> None:
        """A 19px bold heading on a 420px panel is a poster, not a section header."""
        from theme import panel_title
        header = panel_title("Selected turn")
        label = [c for c in layout_audit.walk(header) if isinstance(c, ft.Text)][0]
        self.assertEqual(label.value, "SELECTED TURN")
        self.assertEqual(label.size, t.TYPE_META)
        self.assertGreater(label.style.letter_spacing, 0)

    def test_no_field_anywhere_uses_a_floating_label(self) -> None:
        """The notch cut into a border is the most Material thing an interface can do."""
        from app_state import AppState
        from views import settings_view
        screens = [settings_view.build(AppState(), noop, noop, noop, noop), self.panel_control()]
        for screen in screens:
            for control in layout_audit.walk(screen):
                if isinstance(control, (ft.TextField, ft.Dropdown)):
                    with self.subTest(control=type(control).__name__):
                        self.assertIsNone(getattr(control, "label", None))

    def panel_control(self):
        made = state(3)
        return speakers_view.inspector(made, 0, noop, noop, noop, {}, None, noop, noop,
                                       noop, noop, noop)

    def test_the_correction_box_is_the_tallest_thing_in_the_panel(self) -> None:
        boxes = layout_audit.find(self.panel_control(), lambda c: isinstance(c, ft.TextField))
        self.assertEqual(len(boxes), 1)
        self.assertGreaterEqual(boxes[0].min_lines, 8, "the panel is for editing in")
