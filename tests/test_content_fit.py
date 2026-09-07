"""Every declared width inside a screen must fit the content column, and the inspector
sheet must be an opaque, fixed-width panel.

Flutter measures intrinsic width on its side, which this process cannot see. What is checked
here is every width the application declares — if one of those exceeds its parent column, the
overflow is ours, and it is provable without a screen.
"""
from __future__ import annotations

import unittest

import design_tokens as t
import flet as ft
import layout_audit
from app_state import AppState
from components.app_shell import app_shell, measure
from models import AudioInfo, TranscriptSegment, Word
from views import export_view, recording_view, settings_view, speakers_view, transcription_view, welcome_view

noop = lambda *a, **k: None
validator = lambda *a, **k: None


def populated() -> AppState:
    state = AppState()
    state.selected_file_metadata = AudioInfo(r"C:\research\WP1.m4a", "WP1.m4a", 130_000_000, 7837.5,
                                             "aac", 48000, 2, 148000)
    state.selected_file_path = state.selected_file_metadata.path
    state.transcript_segments = [
        TranscriptSegment(0, 0.0, str(i % 3), f"Speaker {i % 3 + 1}", i * 18, i * 18 + 14, i * 18, i * 18 + 14,
                          "A turn of reasonable length that has to wrap inside its column.",
                          None, False, [Word(i * 18, i * 18 + 1, "A", .95)], .93)
        for i in range(6)]
    state.speaker_mapping = {"Speaker 1": "Moderator", "Speaker 2": "Speaker 2", "Speaker 3": "Speaker 3"}
    state.activity_log = ["File analysed.", "Uploading the recording to Gladia: 64%."]
    return state


def screens(state: AppState, content: float | None = None) -> dict[str, object]:
    return {
        "recording": lambda: recording_view.build(state, noop, noop, noop, noop, validator, content),
        "transcription": lambda: transcription_view.build(state, noop, noop, "01:12"),
        "speakers": lambda: speakers_view.build(state, noop, noop, noop, 1, noop,
                                                {"rows": {}, "speakers": {}}, content),
        "export": lambda: export_view.build(state, noop, noop),
        "settings": lambda: settings_view.build(state, noop, noop, noop),
    }


class ContentFitTests(unittest.TestCase):
    def test_no_declared_child_exceeds_the_content_column(self) -> None:
        state = populated()
        # Every real window this app can be given, including the narrowest allowed.
        for page_width in (760, 900, 1024, 1140, 1280, 1600, 1920):
            layout = measure(page_width, False)
            for name, build in screens(state, layout.content).items():
                with self.subTest(width=page_width, screen=name):
                    control = build()
                    child, widest = layout_audit.widest(control)
                    self.assertLessEqual(widest, layout.content,
                                         f"{name} at {page_width}px: {child} declares {widest}px "
                                         f"inside a {layout.content:.0f}px column")

    def test_the_empty_recording_screen_also_fits(self) -> None:
        state = AppState()
        for page_width in (760, 900, 1280, 1920):
            layout = measure(page_width, False)
            control = recording_view.build(state, noop, noop, noop, noop, validator, layout.content)
            _, widest = layout_audit.widest(control)
            self.assertLessEqual(widest, layout.content)

    def test_the_first_screen_fits_without_scrolling(self) -> None:
        """It was a 480px drop card, a paragraph and two more cards stacked under it."""
        state = AppState()
        for page_width in (760, 900, 1280, 1920):
            with self.subTest(width=page_width):
                layout = measure(page_width, False)
                screen = recording_view.build(state, noop, noop, noop, noop, validator,
                                              layout.content, noop, noop)
                self.assertLessEqual(len(screen.controls), 4, "four blocks at most")
                _, widest = layout_audit.widest(screen)
                self.assertLessEqual(widest, layout.content)
    def test_the_welcome_screen_declares_no_fixed_width(self) -> None:
        _, widest = layout_audit.widest(welcome_view.build(noop, noop))
        self.assertLessEqual(widest, measure(760, False).content)

    def test_the_transcription_screen_reports_its_numbers(self) -> None:
        state = populated()
        layout = measure(1280, False)
        control = transcription_view.build(state, noop, noop, "01:12")
        line = layout_audit.report("transcription", layout.content, control)
        self.assertIn("fits", line)
        self.assertNotIn("OVERFLOW", line)


class ApiKeyFieldTests(unittest.TestCase):
    """The API key input lives in Settings now, with the provider it belongs to.

    It used to be on the Transcription step while the provider that decides which key is
    needed was chosen in Settings — two screens for one decision.
    """

    def key_fields(self, control) -> list:
        return layout_audit.find(control, lambda item: isinstance(item, ft.TextField)
                                 and getattr(item, "password", False))

    def settings_for(self, provider: str, key: str = "") -> object:
        state = populated()
        state.settings.provider = provider
        if key:
            state.set_active_api_key(key)
        return settings_view.build(state, noop, noop, noop, noop)

    def test_the_key_field_is_present_for_every_provider(self) -> None:
        for provider in ("gladia", "soniox", "deepgram", "openai", "compatible"):
            with self.subTest(provider=provider):
                fields = self.key_fields(self.settings_for(provider))
                self.assertEqual(len(fields), 1, "exactly one API key field must be rendered")
                self.assertTrue(fields[0].can_reveal_password)
                # The label sits above the box now, not floating in a notch cut out of its
                # border, so it is a Text beside the field rather than a property of it.
                screen = self.settings_for(provider)
                names = [c.value for c in layout_audit.walk(screen)
                         if isinstance(c, ft.Text) and c.value and "API key" in c.value]
                self.assertEqual(len(names), 1, "and it names the provider it is for")

    def test_the_key_field_shows_the_provider_key_already_in_memory(self) -> None:
        self.assertEqual(self.key_fields(self.settings_for("gladia", "gl-in-memory"))[0].value,
                         "gl-in-memory")
        # Switching provider shows that provider's own field, not the previous key.
        self.assertEqual(self.key_fields(self.settings_for("deepgram"))[0].value, "")

    def test_the_transcription_step_no_longer_asks_for_it(self) -> None:
        state = populated()
        state.transcript_segments = []
        self.assertEqual(self.key_fields(transcription_view.build(state, noop, noop, "00:00")),
                         [], "one place to enter a key, not two")

    def test_no_wrapped_row_holds_an_expanding_child(self) -> None:
        """A Wrap cannot lay out a flexible child; the child renders with no width at all."""
        state = populated()
        for name, build in screens(state, measure(1280, False).content).items():
            with self.subTest(screen=name):
                offenders = layout_audit.wrapped_rows_with_expanding_children(build())
                self.assertEqual(offenders, [], f"{name}: {offenders}")
        self.assertEqual(layout_audit.wrapped_rows_with_expanding_children(welcome_view.build(noop, noop)), [])


class TypingFocusTests(unittest.TestCase):
    """Space is a space while typing, and a transport shortcut everywhere else."""

    def editable_fields(self, control) -> list:
        return layout_audit.find(control, lambda item: isinstance(item, ft.TextField))

    def test_every_editable_field_on_the_review_screen_reports_focus(self) -> None:
        state = populated()
        seen: list[bool] = []
        refs: dict = {"rows": {}, "speakers": {}}
        screen = speakers_view.build(state, noop, noop, noop, 1, noop, refs, 960,
                                     identities=speakers_view.identities_pane(state, noop, refs,
                                                                              seen.append, noop))
        fields = self.editable_fields(screen)
        self.assertTrue(fields, "the speaker rename fields must exist")
        for field in fields:
            with self.subTest(label=field.label or "rename"):
                self.assertIsNotNone(field.on_focus, "focus must be reported or Space stops audio")
                self.assertIsNotNone(field.on_blur, "blur must be reported or Space stays dead")

    def test_the_correction_box_reports_focus_too(self) -> None:
        state = populated()
        seen: list[bool] = []
        panel = speakers_view.inspector(state, 1, noop, noop, noop, {}, None, noop, seen.append)
        fields = self.editable_fields(panel)
        self.assertEqual(len(fields), 1)
        fields[0].on_focus(None)
        fields[0].on_blur(None)
        self.assertEqual(seen, [True, False], "focus then blur must be reported in order")

    def test_a_screen_built_without_a_tracker_still_works(self) -> None:
        state = populated()
        panel = speakers_view.inspector(state, 1, noop, noop, noop, {})
        self.assertIsNone(self.editable_fields(panel)[0].on_focus)


class InspectorSheetTests(unittest.TestCase):
    def sheet(self, page_width: int) -> tuple[object, object]:
        state = populated()
        layout = measure(page_width, True, inspector_open=True)
        refs: dict = {"rows": {}, "speakers": {}}
        body = speakers_view.build(state, noop, noop, noop, 1, noop, refs)
        inspector = ft.Container(speakers_view.inspector(state, 1, noop, noop, noop, refs, noop), expand=True)
        app_shell(ft.Container(), ft.Container(), body, inspector, layout, refs, False)
        return refs["inspector_sheet"], layout

    def test_the_open_sheet_is_opaque_and_the_width_it_declares(self) -> None:
        for page_width in (900, 1024, 1139):   # below the docking breakpoint
            with self.subTest(width=page_width):
                sheet, layout = self.sheet(page_width)
                self.assertTrue(layout.sheet_open)
                self.assertEqual(sheet.width, t.INSPECTOR_WIDTH)  # the pane, card inside it
                # A transparent panel would let the transcript show through the text.
                self.assertEqual(sheet.content.bgcolor, t.surface(), "the card inside is opaque")
                self.assertNotEqual(sheet.bgcolor, ft.Colors.TRANSPARENT)
                self.assertEqual(sheet.content.bgcolor, t.surface(), "the card inside is opaque")
                # No border: the pane is a raised card on the recessed shell, and tone is
                # what separates them now. Twenty hairlines became four.
                self.assertIsNone(sheet.border)
                self.assertEqual(sheet.content.border_radius, t.RADIUS)

    def test_the_body_shrinks_by_exactly_the_sheet_width(self) -> None:
        layout = measure(1024, True, inspector_open=True)
        self.assertEqual(layout.body, layout.workspace - t.INSPECTOR_WIDTH)
        self.assertEqual(layout.content, min(t.MAX_CONTENT, layout.body - 2 * t.CONTENT_GUTTER))
        # Nothing is painted under the sheet: body plus sheet is the whole workspace.
        self.assertEqual(layout.body + t.INSPECTOR_WIDTH, layout.workspace)

    def test_the_docked_inspector_is_also_opaque_and_fixed(self) -> None:
        sheet, layout = self.sheet(1600)
        self.assertTrue(layout.docked_inspector)
        self.assertFalse(layout.sheet_open)
        self.assertEqual(sheet.content.bgcolor, t.surface(), "the card inside is opaque")

    def test_a_closed_inspector_leaves_the_body_whole(self) -> None:
        layout = measure(1024, True, inspector_open=False)
        self.assertFalse(layout.sheet_open)
        self.assertEqual(layout.body, layout.workspace)

    def test_panes_still_sum_within_the_page_with_a_sheet_open(self) -> None:
        for page_width in (760, 900, 1024, 1139, 1140, 1280, 1600):
            for minimised in (False, True):
                layout = measure(page_width, True, True, minimised)
                self.assertTrue(layout.fits, layout.describe())
                self.assertLessEqual(layout.body + (t.INSPECTOR_WIDTH if layout.sheet_open else 0),
                                     layout.workspace + .5)


class MinimisedRailTests(unittest.TestCase):
    def test_minimising_the_rail_gives_the_workspace_its_width_back(self) -> None:
        wide = measure(1280, False, False, False)
        narrow = measure(1280, False, False, True)
        self.assertEqual(wide.nav, t.NAV_WIDTH)
        self.assertEqual(narrow.nav, t.NAV_MINIMISED)
        self.assertEqual(narrow.workspace - wide.workspace, t.NAV_WIDTH - t.NAV_MINIMISED)
        self.assertTrue(narrow.fits)


if __name__ == "__main__": unittest.main()
