"""The root rule: a transient tool floats, and nothing behind it moves.

Every check here is about geometry, not about what the tools do. Find and replace, the
reassign select and the merge menu each get one question asked of them: does opening you
change the page? The answer has to be no, and it has to stay no.
"""
from __future__ import annotations

import unittest

import flet as ft
import design_tokens as t
import layout_audit
import strings as s
from app_state import AppState
from components import overlay
from components.app_shell import app_shell, measure
from components.find_replace_bar import find_replace_bar
from components.speaker_panel import speaker_panel
from models import TranscriptSegment, Word
from views import speakers_view

noop = lambda *a, **k: None


def turn(index: int, start: float) -> TranscriptSegment:
    # (chunk, offset, original_speaker, speaker_id, ...) — the fourth field is the one the
    # panel, the transcript and the exports all key on.
    return TranscriptSegment(0, 0.0, f"raw_{index % 3}", f"SPEAKER_{index % 3}", start, start + 6,
                             start, start + 6, "A turn of ordinary length, long enough to wrap.",
                             None, False, [Word(start, start + 1, "A", .93)], .93)


def populated() -> AppState:
    state = AppState()
    state.transcript_segments = [turn(i, i * 8) for i in range(9)]
    state.speaker_mapping = {"SPEAKER_0": "Moderator", "SPEAKER_1": "Ana", "SPEAKER_2": "Radu"}
    return state


def signature(control) -> list[tuple]:
    """Everything about the tree that decides where a pixel lands."""
    return [(type(item).__name__, getattr(item, "width", None), getattr(item, "height", None),
             getattr(item, "expand", None), getattr(item, "padding", None))
            for item in layout_audit.walk(control)]


def review(state: AppState, content: float, **kwargs) -> ft.Control:
    return speakers_view.build(state, noop, noop, noop, 1, 0, noop,
                               {"rows": {}, "speakers": {}}, content, noop, noop, noop, noop,
                               **kwargs)


def shell_with(state: AppState, page_width: int, overlays: list | None):
    layout = measure(page_width, True)
    refs: dict = {"rows": {}, "speakers": {}}
    body = review(state, layout.content)
    inspector = ft.Container(speakers_view.inspector(state, 1, noop, noop, noop, refs), expand=True)
    shell = app_shell(ft.Container(), ft.Container(), body, inspector, layout, refs, False,
                      None, overlays)
    return shell, refs, layout


def find_panel(state: AppState, available: float, refs: dict | None = None) -> ft.Control:
    return find_replace_bar("primaria", "Primăria", False, False, 4, 3, True,
                            noop, noop, noop, noop, refs if refs is not None else {}, noop,
                            available)


class RootRuleTests(unittest.TestCase):
    """A tool may float above the content. It may not join it."""

    def test_the_review_screen_is_identical_with_a_tool_open(self) -> None:
        state = populated()
        closed, closed_refs, layout = shell_with(state, 1400, None)
        panel = find_panel(state, layout.body)
        opened, opened_refs, _ = shell_with(state, 1400, [panel])
        self.assertEqual(signature(closed_refs["content_host"]),
                         signature(opened_refs["content_host"]),
                         "opening a tool must not change a single measurement of the content")

    def test_the_three_panes_keep_their_widths(self) -> None:
        state = populated()
        for page_width in (900, 1140, 1400, 1920):
            with self.subTest(width=page_width):
                closed, closed_refs, layout = shell_with(state, page_width, None)
                opened, opened_refs, _ = shell_with(state, page_width,
                                                    [find_panel(state, layout.body)])
                self.assertEqual(closed_refs["content_host"].width,
                                 opened_refs["content_host"].width)
                self.assertEqual(closed_refs["workspace_pane"].width,
                                 opened_refs["workspace_pane"].width)
                self.assertEqual(closed_refs.get("inspector_sheet") is None,
                                 opened_refs.get("inspector_sheet") is None)
                if closed_refs.get("inspector_sheet") is not None:
                    self.assertEqual(closed_refs["inspector_sheet"].width,
                                     opened_refs["inspector_sheet"].width,
                                     "the inspector must not shrink to make room for a tool")

    def test_the_inspector_sheet_is_never_covered_or_narrowed(self) -> None:
        """Below the docking breakpoint the inspector is a slide-over pane. A tool floats
        over the transcript, not over the pane the researcher is typing in."""
        state = populated()
        layout = measure(1024, True, inspector_open=True)
        refs: dict = {"rows": {}, "speakers": {}}
        inspector = ft.Container(speakers_view.inspector(state, 1, noop, noop, noop, refs),
                                 expand=True)
        app_shell(ft.Container(), ft.Container(), review(state, layout.content), inspector,
                  layout, refs, False, None, [find_panel(state, layout.body)])
        self.assertTrue(layout.sheet_open)
        self.assertEqual(refs["inspector_sheet"].width, t.INSPECTOR_WIDTH)
        stack = refs["overlay_stack"]
        self.assertNotIn(refs["inspector_sheet"], list(layout_audit.walk(stack)),
                         "the sheet sits beside the stack, never underneath it")

    def test_with_no_tool_open_there_is_no_stack_at_all(self) -> None:
        _, refs, _ = shell_with(populated(), 1400, None)
        self.assertNotIn("overlay_stack", refs,
                         "the closed state must be the tree that existed before overlays")

    def test_an_open_tool_is_stacked_over_the_content_not_inside_it(self) -> None:
        state = populated()
        layout = measure(1400, True)
        panel = find_panel(state, layout.body)
        _, refs, _ = shell_with(state, 1400, [panel])
        stack = refs["overlay_stack"]
        self.assertIsInstance(stack, ft.Stack)
        self.assertEqual(len(stack.controls), 2, "the content, and the tool above it")
        self.assertIs(stack.controls[1], panel, "the tool is the last child, so it paints on top")
        self.assertIn(refs["content_host"], list(layout_audit.walk(stack.controls[0])),
                      "the content is the base of the stack, unmodified")

    def test_a_floating_tool_is_positioned_in_a_corner(self) -> None:
        panel = find_panel(populated(), 960.0)
        self.assertEqual(panel.top, float(t.OVERLAY_TOP))
        self.assertEqual(panel.right, float(t.OVERLAY_INSET))
        self.assertIsNone(panel.left, "docked to one corner, not stretched across")

    def test_a_floating_tool_takes_neither_the_full_width_nor_the_full_height(self) -> None:
        for available in (476.0, 640.0, 960.0, 1360.0):
            with self.subTest(available=available):
                refs: dict = {}
                find_panel(populated(), available, refs)
                width = refs["find_panel_width"]
                self.assertLessEqual(width, t.OVERLAY_MAX_WIDTH, "capped at 520")
                self.assertLessEqual(width + 2 * t.OVERLAY_INSET, max(available, width + 48),
                                     "it must fit inside the content area with its insets")
        panel = find_panel(populated(), 960.0)
        surfaces = [c for c in layout_audit.walk(panel) if isinstance(c, ft.Container)]
        self.assertTrue(all(c.height is None for c in surfaces), "nothing claims a full height")
        self.assertTrue(all(c.expand in (None, False, True) for c in surfaces))

    def test_the_panel_is_a_solid_surface_with_a_close_control(self) -> None:
        refs: dict = {}
        panel = find_panel(populated(), 960.0, refs)
        card = panel.content
        self.assertIsNotNone(card.bgcolor, "never transparent over the transcript")
        self.assertIsNotNone(card.border)
        self.assertIsNotNone(card.shadow)
        closers = [c for c in layout_audit.walk(panel)
                   if isinstance(c, ft.IconButton) and c.tooltip == s.FIND_CLOSE]
        self.assertEqual(len(closers), 1, "exactly one way to close it")
        self.assertEqual(closers[0].width, t.ICON_BUTTON, "40px hit area")


class ReassignTests(unittest.TestCase):
    """Moving one turn to another speaker: a select in the inspector row, no panel."""

    def dropdowns(self, control) -> list[ft.Dropdown]:
        return layout_audit.find(control, lambda c: isinstance(c, ft.Dropdown))

    def test_the_inspector_offers_one_speaker_select(self) -> None:
        state = populated()
        panel = speakers_view.inspector(state, 1, noop, noop, noop, {}, None, noop, noop, noop, noop)
        found = self.dropdowns(panel)
        self.assertEqual(len(found), 1, "one select, not a panel of options")
        self.assertEqual(found[0].value, state.transcript_segments[1].speaker_id)
        self.assertEqual([option.key for option in found[0].options],
                         sorted({item.speaker_id for item in state.transcript_segments}))
        self.assertEqual([option.text for option in found[0].options],
                         ["Moderator", "Ana", "Radu"], "it shows the names, not the raw labels")
        self.assertIsNotNone(found[0].tooltip)

    def test_the_select_sits_in_the_same_row_as_the_other_turn_controls(self) -> None:
        panel = speakers_view.inspector(populated(), 1, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop)
        rows = layout_audit.find(panel, lambda c: isinstance(c, ft.Row)
                                 and any(isinstance(x, ft.Dropdown) for x in (c.controls or [])))
        self.assertEqual(len(rows), 1)
        beside = [c for c in rows[0].controls if isinstance(c, ft.IconButton)]
        self.assertEqual(len(beside), 3, "insert timestamp, revert and play share the row")
        self.assertEqual({c.tooltip for c in beside},
                         {s.INSERT_TIMESTAMP, s.REVERT_CORRECTION, s.PLAY_RANGE})
        for control in beside:
            self.assertEqual(control.width, t.ICON_BUTTON)

    def test_choosing_a_speaker_calls_back_with_the_turn_and_the_label(self) -> None:
        seen: list[tuple[int, str]] = []
        panel = speakers_view.inspector(populated(), 2, noop, noop, noop, {}, None, noop, noop,
                                        noop, lambda index, speaker: seen.append((index, speaker)))
        select = self.dropdowns(panel)[0]
        select.value = "SPEAKER_0"
        select.on_select(ft.Event(name="select", control=select, data=""))
        self.assertEqual(seen, [(2, "SPEAKER_0")])

    def test_the_select_is_dead_when_there_is_only_one_speaker(self) -> None:
        state = AppState()
        state.transcript_segments = [turn(0, 0.0)]
        panel = speakers_view.inspector(state, 0, noop, noop, noop, {}, None, noop, noop, noop, noop)
        self.assertTrue(self.dropdowns(panel)[0].disabled)

    def test_reassigning_moves_only_the_label(self) -> None:
        from app_controller import AppController
        controller = AppController()
        controller.state.transcript_segments = populated().transcript_segments
        item = controller.state.transcript_segments[1]
        before = (item.text, item.original_text, item.absolute_start, item.absolute_end,
                  [w.text for w in item.words], [w.start for w in item.words])
        self.assertTrue(controller.reassign_turn(1, "SPEAKER_0"))
        after = (item.text, item.original_text, item.absolute_start, item.absolute_end,
                 [w.text for w in item.words], [w.start for w in item.words])
        self.assertEqual(before, after, "wording and timings are untouched")
        self.assertEqual(item.speaker_id, "SPEAKER_0")
        self.assertTrue(controller.state.dirty)
        self.assertFalse(controller.reassign_turn(1, "SPEAKER_0"), "already there")
        self.assertFalse(controller.reassign_turn(99, "SPEAKER_0"), "out of range")


class MergeTests(unittest.TestCase):
    """Folding one label into another: a menu on the row, a confirm, and a panel that
    does not move while any of it happens."""

    def menus(self, control) -> list[ft.PopupMenuButton]:
        return layout_audit.find(control, lambda c: isinstance(c, ft.PopupMenuButton))

    def panel(self, on_merge=noop, speakers=("A", "B", "C")) -> ft.Control:
        stats = {name: (3, 30.0) for name in speakers}
        return speaker_panel(stats, {}, {name: i for i, name in enumerate(speakers)},
                             noop, True, {}, noop, on_merge)

    def test_every_row_carries_a_merge_menu(self) -> None:
        found = self.menus(self.panel())
        self.assertEqual(len(found), 3, "one per speaker")
        for menu in found:
            self.assertEqual(len(menu.items), 2, "every other speaker, and never itself")
            self.assertEqual(menu.tooltip, s.MERGE_INTO)
            self.assertEqual(menu.width, t.ICON_BUTTON)

    def test_the_menu_is_disabled_rather_than_missing_when_alone(self) -> None:
        found = self.menus(self.panel(speakers=("A",)))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].disabled)
        self.assertEqual(found[0].tooltip, s.MERGE_UNAVAILABLE)

    def test_choosing_a_target_reports_source_then_target(self) -> None:
        seen: list[tuple[str, str]] = []
        menu = self.menus(self.panel(lambda a, b: seen.append((a, b))))[0]
        menu.items[1].on_click(ft.Event(name="click", control=menu.items[1], data=""))
        self.assertEqual(seen, [("A", "C")])

    def test_the_panel_keeps_its_size_whether_merging_is_offered_or_not(self) -> None:
        state = populated()
        with_menu = speakers_view.identities_pane(state, noop, {}, noop, noop)
        without = speakers_view.identities_pane(state, noop, {}, noop, None)
        self.assertEqual(len(self.menus(with_menu)), 3)
        self.assertEqual(self.menus(without), [])
        self.assertEqual([type(c).__name__ for c in with_menu.controls],
                         [type(c).__name__ for c in without.controls],
                         "the same rows, in the same shape, menu or no menu")

    def test_the_identity_pane_is_the_fixed_pane_so_names_stay_readable(self) -> None:
        _, refs, _ = shell_with(populated(), 1400, None)
        self.assertEqual(refs["inspector_sheet"].width, t.INSPECTOR_WIDTH)

    def test_merging_moves_every_turn_and_retires_the_label(self) -> None:
        from app_controller import AppController
        controller = AppController()
        controller.state.transcript_segments = populated().transcript_segments
        controller.state.speaker_mapping = dict(populated().speaker_mapping)
        texts = [item.text for item in controller.state.transcript_segments]
        moved = controller.merge_speakers("SPEAKER_2", "SPEAKER_1")
        self.assertEqual(moved, 3)
        self.assertNotIn("SPEAKER_2", {item.speaker_id for item in controller.state.transcript_segments})
        self.assertNotIn("SPEAKER_2", controller.state.speaker_mapping)
        self.assertEqual([item.text for item in controller.state.transcript_segments], texts,
                         "merging is a relabel, never a rewrite")
        self.assertTrue(controller.state.dirty)

    def test_merging_into_itself_or_nothing_does_nothing(self) -> None:
        from app_controller import AppController
        controller = AppController()
        controller.state.transcript_segments = populated().transcript_segments
        self.assertEqual(controller.merge_speakers("SPEAKER_1", "SPEAKER_1"), 0)
        self.assertEqual(controller.merge_speakers("", "SPEAKER_1"), 0)
        self.assertFalse(controller.state.dirty)


if __name__ == "__main__": unittest.main()
