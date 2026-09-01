"""The review screen as a workbench rather than a document page.

Three things are being held to account here. The screen must not carry chrome that says
nothing — a heading block repeating the sidebar, a banner about something unchangeable, a
strip that can only ever report "all clear". It must use the desk it is given instead of
sitting inside a reading column meant for prose. And the two highlights it draws must mean
two different things, because before this they did not.
"""
from __future__ import annotations

import unittest

import flet as ft
import design_tokens as t
import layout_audit
import strings as s
from app_state import AppState
from components.app_shell import measure
from components.speaker_panel import speaker_panel
from components.transcript_list import checked_border, paint_turn, row_state, transcript_item
from models import TranscriptSegment, Word
from providers import ProviderCapabilities
from views import speakers_view

noop = lambda *a, **k: None


def turn(index: int, start: float, confidence: float = .93) -> TranscriptSegment:
    return TranscriptSegment(0, 0.0, f"raw{index % 3}", f"SPEAKER_{index % 3}", start, start + 6,
                             start, start + 6, "A turn of ordinary length.", None, False,
                             [Word(start, start + 1, "A", confidence)], confidence)


def populated(confidence: float = .93) -> AppState:
    state = AppState()
    state.transcript_segments = [turn(i, i * 8, confidence) for i in range(9)]
    state.speaker_mapping = {"SPEAKER_0": "Moderator", "SPEAKER_1": "Ana", "SPEAKER_2": "Radu"}
    state.run_capabilities = ProviderCapabilities(supports_diarization=True, global_speakers=True,
                                                  supports_confidence=True,
                                                  supports_word_timestamps=True)
    return state


def review(state: AppState, width: float = 960.0) -> ft.Control:
    return speakers_view.build(state, noop, noop, noop, 1, 0, noop,
                               {"rows": {}, "speakers": {}}, width, noop, noop, noop, noop)


def texts(control) -> list[str]:
    return [c.value for c in layout_audit.walk(control) if isinstance(c, ft.Text) and c.value]


class ChromeTests(unittest.TestCase):
    def column(self, state: AppState) -> list[ft.Control]:
        """The vertical stack between the workbench bar and the bottom of the transcript."""
        return review(state).controls[1].controls[-1].content.controls

    def test_a_clean_transcript_shows_one_bar_and_then_the_text(self) -> None:
        screen = review(populated())
        self.assertEqual(len(screen.controls), 2, "a bar, then the panes")
        self.assertEqual(screen.controls[0].height, t.WORKBENCH_BAR_HEIGHT)
        self.assertEqual(len(self.column(populated())), 1,
                         "the listing, and nothing standing between it and the bar")

    def test_the_bar_spans_the_whole_width_not_one_pane(self) -> None:
        """Inside a pane the bar was squeezed by the pane, and Continue to export — the one
        filled action on the screen — was the first thing cut off."""
        screen = review(populated())
        bar, panes = screen.controls
        self.assertIsInstance(panes, ft.Row)
        self.assertNotIn(bar, list(layout_audit.walk(panes)))
        self.assertIsNone(bar.width, "it takes the content width it is given")

    def test_the_screen_no_longer_repeats_what_the_sidebar_says(self) -> None:
        shown = texts(review(populated()))
        self.assertNotIn(s.SPEAKERS_SUBTITLE, shown, "the subtitle taught a first-run lesson")
        self.assertFalse([line for line in shown if line.startswith("STEP ")],
                         "the step is already marked in the navigation rail")

    def test_the_bar_carries_the_size_of_the_thing_being_edited(self) -> None:
        state = populated()
        self.assertIn(s.WORKBENCH_META.format(turns=9, speakers=3, duration="00:01:10"),
                      texts(review(state)))

    def test_the_diarization_notice_moved_beside_the_speakers(self) -> None:
        state = populated()
        self.assertIn(s.DIARIZATION_GLOBAL,
                      texts(speakers_view.identities_pane(state, noop, {}, noop, noop)),
                      "it describes the identity list, so it belongs on the identity list")
        self.assertNotIn(s.DIARIZATION_GLOBAL, texts(review(state)),
                         "and no longer sits between the researcher and the interview")

    def test_an_all_clear_row_is_not_drawn_at_all(self) -> None:
        self.assertIsNone(speakers_view._uncertain_strip(populated(), noop))

    def test_the_uncertain_row_appears_when_there_is_something_to_check(self) -> None:
        stack = self.column(populated(confidence=.2))
        self.assertEqual(len(stack), 2, "the uncertain row, then the listing")
        self.assertIn(s.LOW_CONFIDENCE_COUNT.format(count=9), texts(stack[0]))

    def test_one_filled_button_survives_the_simplification(self) -> None:
        filled = [c for c in layout_audit.walk(review(populated()))
                  if isinstance(c, ft.Button) and getattr(c, "bgcolor", None) == t.primary()]
        self.assertEqual(len(filled), 1)


class WorkbenchWidthTests(unittest.TestCase):
    """A document is capped at a readable column. A workbench takes the desk."""

    def test_document_screens_are_unchanged(self) -> None:
        for page_width in (760, 900, 1140, 1400, 1920):
            with self.subTest(width=page_width):
                document = measure(page_width, False)
                self.assertLessEqual(document.content, t.MAX_CONTENT)
                self.assertEqual(document.gutter, t.CONTENT_GUTTER)
                self.assertFalse(document.wide)

    def test_the_workbench_uses_the_whole_workspace(self) -> None:
        for page_width in (1400, 1600, 1920, 2560):
            with self.subTest(width=page_width):
                bench = measure(page_width, True, wide=True)
                self.assertEqual(bench.content, bench.body - 2 * t.WORKBENCH_GUTTER)
                self.assertTrue(bench.wide)

    def test_the_workbench_gains_room_on_a_wide_display(self) -> None:
        document, bench = measure(1920, True), measure(1920, True, wide=True)
        self.assertGreater(bench.content, document.content + 300,
                           "a 960px column on a 1920px display wastes a third of the desk")

    def test_it_still_fits_on_the_narrowest_window(self) -> None:
        for page_width in (760, 900, 1024):
            with self.subTest(width=page_width):
                bench = measure(page_width, True, wide=True)
                self.assertTrue(bench.fits)
                self.assertGreater(bench.content, 0)
                self.assertLessEqual(bench.content, bench.workspace)

    def test_nothing_on_the_screen_outgrows_its_column(self) -> None:
        state = populated()
        for page_width in (760, 900, 1140, 1400, 1920):
            with self.subTest(width=page_width):
                bench = measure(page_width, True, wide=True)
                _, widest = layout_audit.widest(review(state, bench.content))
                self.assertLessEqual(widest, bench.content)

    def test_the_spoken_text_keeps_its_own_measure_however_wide_the_desk(self) -> None:
        state = populated()
        widths = []
        for page_width in (1400, 1920, 2560, 3840):
            bench = measure(page_width, True, wide=True)
            line = speakers_view.reading_measure(bench.content)
            widths.append(line)
            self.assertLessEqual(line, t.TRANSCRIPT_MEASURE, f"at {page_width}")
            drawn = [c.width for c in layout_audit.walk(review(state, bench.content))
                     if isinstance(c, ft.Container) and c.width == line]
            self.assertTrue(drawn, f"the measure is actually applied at {page_width}")
        self.assertEqual(widths[-1], float(t.TRANSCRIPT_MEASURE),
                         "past a point the desk grows and the line length stops")
        self.assertEqual(sorted(widths), widths, "and never shrinks on the way there")


class TwoHighlightsTests(unittest.TestCase):
    """The turn being edited and the turn being heard must not look the same."""

    def row(self, selected: bool) -> tuple[ft.Control, dict]:
        refs: dict = {}
        item = transcript_item(0, turn(0, 0.0), {}, t.speaker_color(0), selected, 400,
                               noop, refs)
        return item, refs[0]

    def test_three_states_use_three_channels_and_never_collide(self) -> None:
        """Heard, open and reviewed can all be true of one row. The edge belongs to
        reviewed; playback and selection share the fill, playback winning."""
        chosen, parts = self.row(True)
        self.assertEqual(chosen.bgcolor, t.surface_variant(), "open in the inspector")
        self.assertEqual(chosen.border.left.color, ft.Colors.TRANSPARENT, "not reviewed yet")
        paint_turn(parts, parts["segment"], None, True)
        self.assertEqual(chosen.bgcolor, t.primary_soft(), "being heard wins the fill")
        row_state(parts, checked=True)
        self.assertEqual(chosen.border.left.color, t.primary(), "reviewed owns the edge")
        self.assertEqual(chosen.bgcolor, t.primary_soft(), "and does not touch the fill")
        row_state(parts, playing=False)
        self.assertEqual(chosen.bgcolor, t.surface_variant(), "back to merely open")

    def test_an_unreviewed_row_still_reserves_the_edge(self) -> None:
        plain, _ = self.row(False)
        self.assertEqual(plain.border.left.width, t.CHECK_RULE)
        self.assertEqual(plain.border.left.color, ft.Colors.TRANSPARENT,
                         "reserved, not drawn, so checking cannot nudge the text sideways")
        self.assertIsNone(plain.bgcolor, "an ordinary row shows nothing at all")
        self.assertEqual(checked_border(True).left.color, t.primary())

    def test_the_speaker_dot_keeps_its_colour_whatever_is_selected(self) -> None:
        _, parts = self.row(False)
        self.assertEqual(parts["marker"].bgcolor, t.speaker_color(0))
        self.assertEqual(parts["color"], t.speaker_color(0))

    def test_a_row_answers_the_pointer(self) -> None:
        plain, _ = self.row(False)
        self.assertTrue(plain.ink, "hover and ripple feedback on every turn")
        self.assertEqual(plain.ink_color, t.primary_soft())


class IdentityRowTests(unittest.TestCase):
    def panel(self) -> ft.Control:
        return speaker_panel({"SPEAKER_00": (34, 724.0), "SPEAKER_01": (12, 180.0)},
                             {"SPEAKER_00": "Moderator"}, {"SPEAKER_00": 0, "SPEAKER_01": 1},
                             noop, True, {}, noop, noop)

    def test_a_row_is_two_lines_not_three(self) -> None:
        for row in self.panel().controls:
            self.assertEqual(len(row.content.controls), 2)

    def test_the_label_and_the_counts_share_one_line(self) -> None:
        self.assertIn(s.IDENTITY_META.format(speaker="SPEAKER_00", count=34, duration="00:12:04"),
                      texts(self.panel()))

    def test_the_dot_the_name_and_both_actions_share_the_other(self) -> None:
        first = self.panel().controls[0].content.controls[0]
        self.assertEqual(len([c for c in first.controls if isinstance(c, ft.TextField)]), 1)
        self.assertEqual(len([c for c in first.controls if isinstance(c, ft.IconButton)]), 1)
        self.assertEqual(len([c for c in first.controls if isinstance(c, ft.PopupMenuButton)]), 1)


if __name__ == "__main__": unittest.main()


class PaneOrderTests(unittest.TestCase):
    """The open turn on the left where reading starts, the speaker list on the right."""

    def test_the_speaker_list_sits_left_of_the_transcript(self) -> None:
        state = populated()
        marker = ft.Container(ft.Text("SPEAKER LIST"))
        screen = speakers_view.build(state, noop, noop, noop, 1, 0, noop,
                                     {"rows": {}, "speakers": {}}, 960.0, identities=marker)
        panes = screen.controls[1].controls
        self.assertEqual(len(panes), 2)
        self.assertIn("SPEAKER LIST", texts(panes[0]), "the list is the first pane")
        self.assertNotIn("SPEAKER LIST", texts(panes[1]), "the transcript follows it")

    def test_the_list_column_declares_a_width_rather_than_a_share(self) -> None:
        """As a share it collapsed to about ninety pixels of name field on a normal window."""
        screen = speakers_view.build(populated(), noop, noop, noop, 1, 0, noop,
                                     {"rows": {}, "speakers": {}}, 960.0,
                                     identities=ft.Container())
        column = screen.controls[1].controls[0]
        self.assertEqual(column.width, t.IDENTITY_PANE_WIDTH)
        self.assertIn(column.expand, (None, False),
                      "a container given both width and expand ignores the width")

    def test_the_transcript_has_the_workspace_to_itself_when_the_list_is_away(self) -> None:
        screen = speakers_view.build(populated(), noop, noop, noop, None, 0, noop,
                                     {"rows": {}, "speakers": {}}, 960.0)
        self.assertEqual(len(screen.controls[1].controls), 1)

    def test_the_two_columns_always_fit_side_by_side(self) -> None:
        for content in (600, 660, 792, 1312, 1952):
            with self.subTest(content=content):
                if not speakers_view.identity_column_fits(content):
                    continue
                room = content - t.IDENTITY_PANE_WIDTH - t.S16
                self.assertGreaterEqual(room, t.TRANSCRIPT_MIN_COLUMN)
                self.assertLessEqual(speakers_view.reading_measure(content, t.IDENTITY_PANE_WIDTH),
                                     room, "the reading measure can never exceed its column")

    def test_below_the_fitting_width_the_list_does_not_take_a_column(self) -> None:
        self.assertFalse(speakers_view.identity_column_fits(492))
        self.assertTrue(speakers_view.identity_column_fits(660))

    def test_the_bar_can_hide_and_bring_back_the_speaker_list(self) -> None:
        seen: list[bool] = []
        bar = speakers_view._workbench_bar(populated(), 3, noop, noop,
                                           lambda: seen.append(True), False)
        toggles = [c for c in layout_audit.walk(bar) if isinstance(c, ft.IconButton)]
        self.assertEqual(len(toggles), 1)
        self.assertEqual(toggles[0].tooltip, s.COLLAPSE_IDENTITIES)
        toggles[0].on_click(None)
        self.assertEqual(seen, [True])
        hidden = speakers_view._workbench_bar(populated(), 3, noop, noop, noop, True)
        self.assertEqual([c for c in layout_audit.walk(hidden)
                          if isinstance(c, ft.IconButton)][0].tooltip, s.EXPAND_IDENTITIES)


class DensityTests(unittest.TestCase):
    def test_a_turn_fits_the_row_extent_it_is_scrolled_by(self) -> None:
        """The sticky speaker header reads the scroll position as row index times extent, so
        a row that is taller than the extent silently mislabels who is speaking.

        A row is: padding, a meta line, 2px, one line of speech, padding — then the gap.
        """
        meta = t.TYPE_CAPTION * 1.35
        speech = t.TYPE_BODY * t.LINE_HEIGHT
        content = t.TURN_PADDING * 2 + meta + 2 + speech
        self.assertLessEqual(content + t.TURN_GAP, t.TRANSCRIPT_ROW_HEIGHT,
                             "a turn plus its gap must fit the extent")

    def test_the_list_got_roughly_twice_as_dense(self) -> None:
        """Four turns on screen meant paging every few seconds on a two-hour interview."""
        before = 116
        self.assertGreaterEqual(before / t.TRANSCRIPT_ROW_HEIGHT, 1.7)
        self.assertEqual(t.TURN_GAP, 10, "the brief asked for ~10px between turns")
        self.assertEqual(t.LINE_HEIGHT, 1.4)

    def test_the_timestamp_gutter_still_holds_a_timestamp(self) -> None:
        self.assertGreaterEqual(t.TIMESTAMP_GUTTER, 8 * t.TYPE_MONO * .6,
                                "hh:mm:ss at the mono size, with air after it")


class NoOverlapTests(unittest.TestCase):
    """Nothing is cut off, and nothing sits on top of anything else.

    Both panes want space at the same widths, and both can float. These are the checks that
    the screen resolves that once, up front, instead of drawing two surfaces over each other.
    """

    WIDTHS = (760, 800, 900, 1000, 1024, 1140, 1200, 1268, 1280, 1400, 1600, 1920, 2560)

    def placements(self, hidden: bool = False, find: bool = False):
        for page in self.WIDTHS:
            layout = measure(page, True, False, False, wide=True)
            yield page, layout, speakers_view.pane_placement(layout.content,
                                                             layout.docked_inspector,
                                                             hidden, find)

    def test_at_most_one_thing_ever_floats(self) -> None:
        for hidden in (False, True):
            for find in (False, True):
                for page, _, placement in self.placements(hidden, find):
                    with self.subTest(width=page, hidden=hidden, find=find):
                        self.assertLessEqual(len(placement.floating), 1, placement)

    def test_a_floating_pane_steps_aside_for_the_transient_tool(self) -> None:
        """Find and replace floats top-right; so would a floating pane. One of them goes."""
        for page, _, placement in self.placements(find=True):
            with self.subTest(width=page):
                self.assertEqual(placement.floating, (), "the tool has the air to itself")

    def test_the_columns_always_fit_the_content_they_are_given(self) -> None:
        for page, layout, placement in self.placements():
            with self.subTest(width=page):
                used = t.IDENTITY_PANE_WIDTH + t.S16 if placement.identities == "column" else 0
                self.assertLessEqual(used, layout.content, "the list column cannot overhang")
                line = speakers_view.reading_measure(layout.content, used and t.IDENTITY_PANE_WIDTH)
                self.assertLessEqual(line, layout.content - used,
                                     "the reading measure cannot exceed its own column")

    def test_the_panes_never_both_claim_the_workspace(self) -> None:
        for page, layout, placement in self.placements():
            with self.subTest(width=page):
                if placement.detail == "pane":
                    self.assertEqual(layout.inspector, t.INSPECTOR_WIDTH)
                    self.assertLessEqual(layout.total, layout.page_width + .5)
                else:
                    self.assertEqual(layout.inspector, 0.0,
                                     "a floating turn must not also reserve a column")

    def test_an_ordinary_window_gets_all_three_columns_and_no_overlay(self) -> None:
        layout = measure(1268, True, False, False, wide=True)
        placement = speakers_view.pane_placement(layout.content, layout.docked_inspector)
        self.assertEqual((placement.identities, placement.detail), ("column", "pane"))
        self.assertEqual(placement.floating, ())

    def test_hiding_the_list_never_leaves_it_floating(self) -> None:
        for page, _, placement in self.placements(hidden=True):
            with self.subTest(width=page):
                self.assertEqual(placement.identities, "hidden")

    def test_the_name_field_has_room_to_read_a_name_in(self) -> None:
        """The reason the list stopped being a proportional share in the first place."""
        furniture = 9 + 3 * t.S8 + 2 * t.ICON_BUTTON
        field = t.IDENTITY_PANE_WIDTH - t.S16 - furniture
        self.assertGreaterEqual(field, 140, f"only {field}px of name field")
