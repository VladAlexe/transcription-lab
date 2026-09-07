"""Home, the wordmark that leads there, and the status band along the bottom."""
from __future__ import annotations
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components import brand
from components.status_bar import status_bar
from models import AudioInfo, TranscriptSegment
from views import recording_view, welcome_view


def walk(control, seen=None) -> list:
    seen = [] if seen is None else seen
    seen.append(control)
    for name in ("controls", "actions", "spans"):
        for child in getattr(control, name, None) or []: walk(child, seen)
    for name in ("content", "label", "title", "subtitle"):
        child = getattr(control, name, None)
        if hasattr(child, "controls") or hasattr(child, "value"): walk(child, seen)
    return seen


def texts(control) -> list[str]:
    return [v for v in (getattr(c, "value", None) for c in walk(control)) if isinstance(v, str)]


class MarkTests(unittest.TestCase):
    def test_the_mark_carries_its_own_ground_and_is_clipped_to_its_tile(self) -> None:
        """The logo used to be ink on nothing and needed a light tile put behind it. The
        new artwork brings its own backdrop, so it fills the tile instead and the tile only
        rounds and clips it."""
        art = brand.mark()
        self.assertEqual(art.content.fit, ft.BoxFit.COVER)
        self.assertIsNotNone(art.clip_behavior)
        self.assertTrue(art.border_radius)

    def test_the_mark_is_the_size_of_an_application_icon(self) -> None:
        self.assertGreaterEqual(brand.mark().width, 36)
        self.assertGreater(brand.mark(t.MARK_HERO).width, brand.mark().width)

    def test_the_artwork_fills_its_tile_exactly(self) -> None:
        self.assertEqual(brand.mark().content.width, brand.mark().width)

    def test_the_interface_uses_the_square_crop_and_never_the_wide_master(self) -> None:
        """The master is a 3:2 render with the mark in the middle of a field. Shown as an
        icon it would be mostly backdrop; every size ships from the square crop."""
        self.assertEqual(brand.MARK_ASSET, "icon_mark.png")
        self.assertTrue((Path(__file__).resolve().parents[1] / "assets" / "icon_mark.png").is_file())


class WordmarkTests(unittest.TestCase):
    def test_the_wordmark_leads_home_and_says_so(self) -> None:
        opened: list[bool] = []
        block = brand.wordmark(False, lambda: opened.append(True))
        self.assertIsNotNone(block.on_click)
        self.assertIn("Home", block.tooltip)
        block.on_click(None)
        self.assertEqual(opened, [True])

    def test_without_a_handler_it_is_not_pretending_to_be_a_button(self) -> None:
        block = brand.wordmark(False)
        self.assertIsNone(block.on_click)
        self.assertFalse(block.ink)

    def test_the_name_wraps_rather_than_truncating_beside_a_larger_mark(self) -> None:
        """A bigger mark takes width from the name; an ellipsis in the product's own name
        is worse than a second line."""
        name = [c for c in walk(brand.wordmark()) if getattr(c, "value", "") == s.BRAND_WORDMARK]
        self.assertEqual(name[0].max_lines, 2)

    def test_the_minimised_rail_shows_the_mark_alone(self) -> None:
        self.assertNotIn(s.BRAND_WORDMARK, texts(brand.wordmark(True)))


class HomeTests(unittest.TestCase):
    def screen(self):
        return welcome_view.home(lambda: None, lambda: None)

    def test_home_names_all_four_steps(self) -> None:
        shown = texts(self.screen())
        for title, _ in s.HOME_STEPS: self.assertIn(title, shown)

    def test_home_carries_the_shortcut_list(self) -> None:
        shown = texts(self.screen())
        for line in s.shortcuts(t.SKIP_SECONDS): self.assertIn(line, shown)

    def test_the_shortcut_list_cannot_drift_from_the_one_help_shows(self) -> None:
        """One source, so a shortcut added in one place is never missing from the other."""
        shown = texts(self.screen())
        self.assertEqual([line for line in s.shortcuts(t.SKIP_SECONDS) if line not in shown], [])

    def test_home_says_what_each_export_contains(self) -> None:
        shown = texts(self.screen())
        for name, body in s.HOME_EXPORTS:
            self.assertIn(name, shown); self.assertIn(body, shown)

    def test_home_explains_the_marking_colours(self) -> None:
        self.assertIn(s.HOME_MARKING, texts(self.screen()))

    def test_home_still_states_what_leaves_the_computer(self) -> None:
        shown = texts(self.screen())
        for _, fact in welcome_view.FACTS: self.assertIn(fact, shown)

    def test_home_offers_both_ways_in(self) -> None:
        started: list[str] = []
        screen = welcome_view.home(lambda: started.append("new"), lambda: started.append("open"))
        clickable = (ft.Button, ft.OutlinedButton, ft.TextButton, ft.FilledButton)
        for button in [c for c in walk(screen) if isinstance(c, clickable)]:
            if button.on_click: button.on_click(None)
        self.assertEqual(sorted(started), ["new", "open"])

    def test_the_first_run_screen_stays_short(self) -> None:
        """Someone opening this for the first time needs a way in, not the whole reference."""
        first = texts(welcome_view.build(lambda: None, lambda: None))
        self.assertNotIn(s.HOME_MARKING, first)
        self.assertIn(s.WELCOME_BODY, first)


class StatusBarTests(unittest.TestCase):
    """The band is the one strip that is never a control: it only reports."""

    def state(self, turns: int = 0, checked: int = 0) -> AppState:
        app = AppState()
        app.selected_file_metadata = AudioInfo(r"C:\R\iv.m4a", "iv.m4a", 100, 60.0, "aac", 48000, 2)
        app.transcript_segments = [
            TranscriptSegment(0, 0.0, "A", "A", 0.0, 1.0, 0.0, 1.0, "text", checked=i < checked)
            for i in range(turns)]
        return app

    def test_the_band_is_a_slim_strip_and_not_a_toolbar(self) -> None:
        self.assertLessEqual(status_bar(self.state(), "home").height, 26)

    def test_it_reports_how_much_of_the_transcript_is_checked(self) -> None:
        band = status_bar(self.state(turns=12, checked=5), "speakers", checked=5)
        self.assertIn("5/12", texts(band))

    def test_a_project_with_no_transcript_shows_no_counter(self) -> None:
        self.assertNotIn("0/0", texts(status_bar(self.state(), "recording")))

    def test_it_names_the_recording_the_provider_and_the_language(self) -> None:
        app = self.state(turns=2)
        app.settings.language = "ro"
        shown = texts(status_bar(app, "speakers"))
        self.assertIn("iv.m4a", shown)
        self.assertIn("Romanian", shown)
        self.assertIn("Gladia", shown)

    def test_detect_automatically_reads_as_words_not_as_the_code(self) -> None:
        app = self.state(); app.settings.language = "auto"
        self.assertIn("Detect automatically", texts(status_bar(app, "recording")))

    def test_unsaved_work_is_stated_in_the_band_as_well(self) -> None:
        app = self.state(turns=1); app.dirty = True
        self.assertIn(s.UNSAVED, texts(status_bar(app, "speakers")))

    def test_the_left_end_names_the_screen_you_are_on(self) -> None:
        for screen, expected in (("home", s.HOME_TITLE), ("settings", s.SETTINGS_TITLE)):
            self.assertIn(expected, texts(status_bar(self.state(), screen)))

    def test_the_left_end_leads_home(self) -> None:
        opened: list[bool] = []
        band = status_bar(self.state(), "speakers", on_home=lambda: opened.append(True))
        band.content.controls[0].on_click(None)
        self.assertEqual(opened, [True])


class RecordingWordingTests(unittest.TestCase):
    def test_audio_preparation_names_no_particular_service(self) -> None:
        """The provider is chosen later, and there are five of them; naming one here read as
        though the recording could only ever go to that one."""
        app = AppState()
        app.selected_file_metadata = AudioInfo(r"C:\R\iv.m4a", "iv.m4a", 100, 60.0, "aac", 48000, 2)
        nothing = lambda *a: None
        shown = " ".join(texts(recording_view.build(app, nothing, nothing, nothing, nothing,
                                                    nothing, 900, nothing, nothing)))
        for service in ("Gladia", "Deepgram", "Soniox", "OpenAI"):
            self.assertNotIn(service, shown.replace(s.QUALITY_TRANSFER, ""))
        self.assertIn("API provider", shown)


class RailFitTests(unittest.TestCase):
    def test_the_bigger_mark_still_leaves_the_name_a_readable_column(self) -> None:
        """The mark grew; the name must not be squeezed to nothing beside it."""
        for_name = t.NAV_WIDTH - 2 * t.WORDMARK_LEFT - t.MARK_SIZE - t.WORDMARK_GAP
        self.assertGreaterEqual(for_name, 120)

    def test_the_minimised_rail_can_still_hold_the_mark(self) -> None:
        self.assertLessEqual(t.MARK_SIZE + 2 * t.S4, t.NAV_MINIMISED)


class TutorialTests(unittest.TestCase):
    """The tutorial has to be about interviews, and to read like instructions."""

    def test_nothing_claims_the_application_is_only_for_group_interviews(self) -> None:
        copy = " ".join([s.WELCOME_TITLE, s.WELCOME_BODY, s.APP_TAGLINE, s.HOME_WHAT_BODY,
                         *(body for _, body in s.HOME_STEPS)]).lower()
        self.assertNotIn("group interview", copy)

    def test_it_says_a_single_interviewee_is_the_same_job(self) -> None:
        self.assertIn("one interviewee", s.HOME_WHAT_BODY.lower())

    def test_the_steps_name_the_screen_they_happen_on(self) -> None:
        steps = " ".join(s.HELP_STEPS)
        for screen in ("Settings", "Recording", "Transcription", "Review", "Export"):
            with self.subTest(screen=screen):
                self.assertIn(screen, steps)

    def test_the_steps_still_carry_the_promises_about_your_data(self) -> None:
        """Direct is not the same as silent: what happens to the file and the key stays."""
        steps = " ".join(s.HELP_STEPS).lower()
        for promise in ("never written to disk", "never modified", "only to that provider"):
            with self.subTest(promise=promise):
                self.assertIn(promise, steps)

    def test_dutch_is_offered_as_a_recording_language(self) -> None:
        self.assertIn(("nl", "Dutch"), s.LANGUAGES)
        self.assertEqual(s.language_name("nl"), "Dutch")

    def test_the_language_list_is_about_the_recording_not_the_interface(self) -> None:
        self.assertIn("interface is English", s.HOME_LANGUAGE_BODY)
