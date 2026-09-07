"""Where things sit, and why. One assertion per decision about the layout of the review
screen, so a later tidy-up cannot quietly undo a choice that was made for a reason."""
from __future__ import annotations
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flet as ft
import design_tokens as t
import layout_audit
import strings as s
from app_state import AppState
from components.app_shell import measure
from components.top_bar import save_status, top_bar
from models import AudioInfo, TranscriptSegment, Word
from views import speakers_view

noop = lambda *a, **k: None


def populated() -> AppState:
    state = AppState()
    state.selected_file_metadata = AudioInfo(r"C:\r\WP1.m4a", "WP1.m4a", 13_000_000, 7837.5,
                                             "aac", 48000, 2, 148000)
    state.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i % 3}", f"SPEAKER_{i % 3}", i * 18, i * 18 + 14,
                          i * 18, i * 18 + 14, "A turn of ordinary length.", None, False,
                          [Word(i * 18, i * 18 + 1, "A", .93)], .93) for i in range(6)]
    state.speaker_mapping = {"SPEAKER_0": "Moderator", "SPEAKER_1": "Ana", "SPEAKER_2": "Radu"}
    return state


def texts(control) -> list[str]:
    return [v for v in (getattr(c, "value", None) for c in layout_audit.walk(control))
            if isinstance(v, str)]


class PaneWidthTests(unittest.TestCase):
    def test_the_editor_takes_the_room_and_the_speaker_list_gives_it_up(self) -> None:
        """Reading a turn is choosing one; correcting it is the work."""
        self.assertGreaterEqual(t.INSPECTOR_WIDTH, 480)
        self.assertLessEqual(t.IDENTITY_PANE_WIDTH, 240)

    def test_all_three_panes_fit_an_ordinary_window(self) -> None:
        for page in (1268, 1366, 1440, 1600, 1920):
            for minimised in (True, False):
                with self.subTest(width=page, rail="mini" if minimised else "full"):
                    layout = measure(page, True, False, minimised, wide=True)
                    self.assertTrue(layout.fits, layout.describe())
                    self.assertGreater(layout.content, 0)

    def test_the_editor_docks_rather_than_floats_at_the_declared_breakpoint(self) -> None:
        layout = measure(t.INSPECTOR_BREAKPOINT, True, False, False, wide=True)
        self.assertTrue(layout.docked_inspector)

    def test_a_turn_preview_still_carries_enough_words_to_recognise_it(self) -> None:
        """The transcript row is a preview you choose from, not the surface you read on —
        that is the editing pane now. It gives width up deliberately, but a row has to hold
        enough of a sentence to be told apart from the one above it."""
        for page in (1268, 1366, 1440, 1600, 1920):
            with self.subTest(width=page):
                layout = measure(page, True, False, True, wide=True)
                # Measured with the list where it actually goes: on a narrow window it steps
                # out to a floating panel, and the transcript gets its width back.
                beside = (t.IDENTITY_PANE_WIDTH
                          if speakers_view.identity_column_fits(layout.content) else 0)
                measure_px = speakers_view.reading_measure(layout.content, beside)
                self.assertGreaterEqual(measure_px / (t.TYPE_BODY * .5) * t.TURN_LINES, 72)


class InspectorOrderTests(unittest.TestCase):
    """The panel reads top to bottom in the order the work happens."""

    def panel(self, **kwargs):
        return speakers_view.inspector(populated(), 1, noop, noop, noop, {}, None, noop, noop,
                                       noop, noop, **kwargs)

    def index_of(self, panel, predicate) -> int:
        for position, control in enumerate(panel.controls):
            if predicate(control): return position
        return -1

    def test_the_text_comes_before_the_button_that_saves_it(self) -> None:
        panel = self.panel()
        editor = self.index_of(panel, lambda c: isinstance(c, ft.Column)
                               and any(isinstance(x, ft.TextField) for x in (c.controls or [])))
        saving = self.index_of(panel, lambda c: isinstance(c, ft.Row)
                               and any(getattr(x, "content", None) == s.SAVE_CORRECTION
                                       for x in (c.controls or [])))
        self.assertGreater(editor, 0)
        self.assertEqual(saving, editor + 1)

    def test_reassigning_the_speaker_comes_after_saving_not_before(self) -> None:
        """It is an occasional correction; it used to sit between the text and the save."""
        panel = self.panel(on_toggle_note=noop)
        saving = self.index_of(panel, lambda c: isinstance(c, ft.Row)
                               and any(getattr(x, "content", None) == s.SAVE_CORRECTION
                                       for x in (c.controls or [])))
        select = self.index_of(panel, lambda c: isinstance(c, ft.Row)
                               and any(isinstance(x, ft.Dropdown) for x in (c.controls or [])))
        self.assertGreater(select, saving)

    def test_the_raw_diarization_label_is_not_repeated_on_a_global_transcript(self) -> None:
        """The name says it, and the Speakers pane lists the raw label under every name."""
        facts = [line for line in texts(self.panel()) if line.startswith("Turn 2 of")]
        self.assertEqual(len(facts), 1)
        self.assertNotIn("SPEAKER_1", facts[0])

    def test_it_is_shown_where_labels_are_per_fragment_and_matching_them_is_the_work(self) -> None:
        from providers import ProviderCapabilities
        state = populated()
        state.run_capabilities = ProviderCapabilities(supports_diarization=True,
                                                      global_speakers=False)
        panel = speakers_view.inspector(state, 1, noop, noop, noop, {}, None, noop, noop, noop, noop)
        facts = [line for line in texts(panel) if line.startswith("Turn 2 of")]
        self.assertIn("SPEAKER_1", facts[0])

    def test_the_pane_has_one_name_whether_or_not_a_turn_is_open(self) -> None:
        empty = speakers_view.inspector(populated(), None, noop, noop, noop, {})
        # A panel title is set upper case by the type system, so compare on the words.
        self.assertIn(s.INSPECTOR_TITLE.upper(), [line.upper() for line in texts(empty)])
        self.assertIn(s.INSPECTOR_TITLE.upper(), [line.upper() for line in texts(self.panel())])

    def test_the_select_says_what_it_selects(self) -> None:
        self.assertIn(s.REASSIGN_LABEL, texts(self.panel()))


class SaveStatusTests(unittest.TestCase):
    """The line beside the Save button answers the question that belongs there: where."""

    def test_it_names_the_file_the_work_belongs_to(self) -> None:
        self.assertIn("WP1.transcript.json", save_status(False, "WP1.transcript.json"))
        self.assertIn("WP1.transcript.json", save_status(True, "WP1.transcript.json"))

    def test_unsaved_work_is_still_unmistakable(self) -> None:
        self.assertNotEqual(save_status(True, "WP1.transcript.json"),
                            save_status(False, "WP1.transcript.json"))

    def test_a_project_with_no_file_yet_says_so(self) -> None:
        self.assertEqual(save_status(True, ""), s.SAVE_STATUS_NEW)

    def test_the_key_badge_no_longer_repeats_the_status_band(self) -> None:
        """It said the same sentence twice on every screen; the band leads to Settings."""
        state = populated(); state.current_workflow_step = 0
        bar = top_bar(state, noop, noop, noop, {})
        self.assertNotIn(s.API_MISSING, texts(bar))


class ShellBandTests(unittest.TestCase):
    """Every band that describes the window spans the window."""

    def shell(self, docked: bool = True):
        from components.app_shell import app_shell
        layout = measure(1600 if docked else 900, True, False, True, wide=True)
        top = ft.Container(ft.Text("top"), height=t.TOP_BAR_HEIGHT)
        footer = ft.Container(ft.Text("player"), height=t.PLAYER_BAR_HEIGHT)
        status = ft.Container(ft.Text("status"), height=t.STATUS_BAR_HEIGHT)
        panel = ft.Text("selected turn")
        return app_shell(ft.Text("rail"), top, ft.Text("work"), panel, layout, {}, False,
                         footer, None, status), top, footer, status, layout

    def test_the_title_bar_is_not_inside_the_workspace_column(self) -> None:
        """It used to be, which put the window's own close button five hundred pixels in
        from the right edge whenever the editing pane was docked."""
        shell, top, _, _, _ = self.shell()
        self.assertIn(top, shell.content.controls)

    def test_the_bands_run_above_and_below_the_row_of_panes(self) -> None:
        shell, top, footer, status, _ = self.shell()
        rows = shell.content.controls
        frame = [c for c in rows if isinstance(c, ft.Row)]
        self.assertEqual(len(frame), 1)
        self.assertEqual(rows.index(top), 0)
        self.assertLess(rows.index(frame[0]), rows.index(footer))
        self.assertEqual(rows[-1], status)

    def test_all_three_panes_start_at_the_same_height(self) -> None:
        """One Row, so the editing pane cannot begin lower than the two beside it."""
        _, _, _, _, layout = self.shell()
        shell, *_ = self.shell()
        panes = [c for c in shell.content.controls if isinstance(c, ft.Row)][0].controls
        self.assertEqual(len(panes), 3)
        # Rail, then the editing pane, then the transcript: the work comes first and the
        # list you pick from sits beside it.
        self.assertEqual([c.width for c in panes],
                         [layout.nav, layout.inspector, layout.workspace])

    def test_the_title_bar_leaves_the_sidebar_strip_alone(self) -> None:
        """The filename lines up with the work it describes, not over the wordmark."""
        state = populated()
        bar = top_bar(state, noop, noop, noop, {}, lead_offset=t.NAV_WIDTH)
        indented = [c for c in layout_audit.walk(bar)
                    if isinstance(c, ft.Container) and c.padding is not None
                    and getattr(c.padding, "left", 0) >= t.NAV_WIDTH]
        self.assertTrue(indented)


class TurnDensityTests(unittest.TestCase):
    def test_a_row_still_fits_inside_the_uniform_height(self) -> None:
        """The list is virtualised on a fixed row height; a row taller than it clips."""
        meta, speech = 15, t.TYPE_BODY * t.LINE_HEIGHT * t.TURN_LINES
        content = t.TURN_PADDING * 2 + meta + t.S4 + speech
        self.assertLessEqual(content + t.TURN_GAP, t.TRANSCRIPT_ROW_HEIGHT)

    def test_the_gap_between_turns_is_air_and_not_a_margin(self) -> None:
        self.assertLessEqual(t.TURN_GAP, 2)

    def test_more_turns_reach_the_screen_than_before(self) -> None:
        self.assertGreaterEqual(600 // t.TRANSCRIPT_ROW_HEIGHT, 7)


class PaneOrderTests(unittest.TestCase):
    """Rail, editing pane, transcript, speaker list — left to right."""

    def shell(self):
        from components.app_shell import app_shell
        layout = measure(1600, True, False, True, wide=True)
        return app_shell(ft.Text("rail"), ft.Container(height=t.TOP_BAR_HEIGHT),
                         ft.Text("work"), ft.Text("selected turn"), layout, {}), layout

    def test_the_editing_pane_comes_before_the_transcript(self) -> None:
        shell, layout = self.shell()
        panes = [c for c in shell.content.controls if isinstance(c, ft.Row)][0].controls
        self.assertEqual([c.width for c in panes],
                         [layout.nav, layout.inspector, layout.workspace])

    def test_its_gutter_faces_the_transcript(self) -> None:
        """Docked on the left, the breathing space belongs on its right-hand edge."""
        shell, _ = self.shell()
        pane = [c for c in shell.content.controls if isinstance(c, ft.Row)][0].controls[1]
        self.assertEqual(pane.padding.right, 0)
        self.assertGreater(pane.padding.left, 0)

    def test_it_can_still_be_asked_for_on_the_other_side(self) -> None:
        from components.app_shell import app_shell
        layout = measure(1600, True, False, True, wide=True)
        shell = app_shell(ft.Text("rail"), ft.Container(height=t.TOP_BAR_HEIGHT),
                          ft.Text("work"), ft.Text("turn"), layout, {}, inspector_left=False)
        panes = [c for c in shell.content.controls if isinstance(c, ft.Row)][0].controls
        self.assertEqual([c.width for c in panes],
                         [layout.nav, layout.workspace, layout.inspector])


class ToolbarFitTests(unittest.TestCase):
    """A Row cannot shrink an intrinsic child: a toolbar with more in it than fits does not
    compress, it clips — and what it clips is the last thing in the row, which is the button
    that leaves the screen."""

    def bar(self, width: float):
        from views.speakers_view import _workbench_bar
        from components.review_strip import review_strip
        from review_progress import Progress
        state = populated()
        strip = review_strip(Progress(42, 312), False, noop, noop)
        return _workbench_bar(state, 2, noop, noop, noop, False, strip, width)

    def labels(self, control) -> list[str]:
        return [c for c in (getattr(x, "content", None) for x in layout_audit.walk(control))
                if isinstance(c, str)]

    def test_the_way_out_of_the_screen_is_never_the_thing_that_is_dropped(self) -> None:
        for width in (380, 439, 564, 736, 960):
            with self.subTest(width=width):
                found = layout_audit.find(self.bar(width),
                                          lambda c: getattr(c, "tooltip", "") == s.CONTINUE_TO_EXPORT
                                          or getattr(c, "content", None) == s.CONTINUE_TO_EXPORT)
                self.assertTrue(found, "no way to reach export at all")

    def test_the_screen_name_goes_before_the_button_loses_its_words(self) -> None:
        """The sidebar and the status band both name the screen; nothing else says export."""
        from views import speakers_view
        narrow = self.bar(564)
        self.assertNotIn(s.SPEAKERS_TITLE, texts(narrow))
        self.assertIn(s.CONTINUE_TO_EXPORT, self.labels(narrow))

    def test_a_wide_toolbar_carries_the_title_and_the_counts(self) -> None:
        wide = texts(self.bar(960))
        self.assertIn(s.SPEAKERS_TITLE, wide)

    def test_everything_declared_fits_the_width_it_is_offered(self) -> None:
        from views import speakers_view as v
        for width in (439, 564, 736, 960):
            with self.subTest(width=width):
                cost = v.BAR_PROGRESS + v.BAR_ICONS
                if width >= cost + v.BAR_EXPORT_LABELLED: cost += v.BAR_EXPORT_LABELLED
                else: cost += t.ICON_BUTTON + t.S8
                if width >= cost + v.BAR_TITLE: cost += v.BAR_TITLE
                self.assertLessEqual(cost, width)
