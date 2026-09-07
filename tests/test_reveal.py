"""Both halves of the screen showing the same turn.

The panel on the right and the list in the middle have to agree about where you are. They
did not: a row's place in the list is its position in the *visible order*, and the code
subtracted the page offset from the *transcript index* instead. Those are the same number
only while nothing is filtered and everything fits one page, which is never true of a
two-hour interview.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import flet as ft
import layout_audit
import review_progress
import strings as s
from app_controller import AppController
from app_state import AppState
from models import TranscriptSegment
from views import speakers_view

noop = lambda *a, **k: None
PAGE = speakers_view.PAGE_SIZE


def state(count: int = 200, checked_every: int = 3) -> AppState:
    made = AppState()
    made.transcript_segments = [
        TranscriptSegment(0, 0.0, f"raw{i % 2}", f"SPEAKER_{i % 2}", i * 10, i * 10 + 8,
                          i * 10, i * 10 + 8, f"Turn {i}.") for i in range(count)]
    for i, segment in enumerate(made.transcript_segments):
        segment.checked = bool(checked_every) and i % checked_every == 0
    return made


class RevealTests(unittest.TestCase):
    def app(self, only_unchecked: bool = False, offset: int = 0, count: int = 200):
        import main
        controller = AppController(state(count))
        controller.state.show_only_unchecked = only_unchecked
        order = review_progress.visible_order(controller.state.transcript_segments, only_unchecked)
        scrolled: list[int] = []
        rendered: list[bool] = []
        app = SimpleNamespace(controller=controller, transcript_offset=offset,
                              refs={"visible_order": order, "listing": object()},
                              render=lambda: rendered.append(True))
        app.current_order = lambda: main.DesktopApp.current_order(app)
        app.scroll_to_row = lambda position: scrolled.append(position)
        app.reveal_turn = lambda index, allow=True: main.DesktopApp.reveal_turn(app, index, allow)
        app.scrolled, app.rendered, app.order = scrolled, rendered, order
        return app

    def test_a_turn_on_the_first_page_is_scrolled_to(self) -> None:
        app = self.app()
        self.assertTrue(app.reveal_turn(30))
        self.assertEqual(app.scrolled, [30])
        self.assertEqual(app.rendered, [], "no rebuild for the page already shown")

    def test_a_turn_far_down_the_list_needs_no_rebuild_at_all(self) -> None:
        """There are no pages any more. Resume to turn 150 is one scroll, not a page flip
        followed by a scroll — which is what used to leave the list on turns 0 to 79."""
        app = self.app()
        self.assertTrue(app.reveal_turn(150))
        self.assertEqual(app.scrolled, [150])
        self.assertEqual(app.rendered, [], "the list already holds every visible turn")

    def test_the_row_position_is_not_the_transcript_index(self) -> None:
        """With a filter on, turn 100 is the sixty-sixth row. The old maths aimed at row
        100, past the end of the page, so it gave up and did nothing at all."""
        app = self.app(only_unchecked=True)
        position = app.order.index(100)
        self.assertNotEqual(position, 100, "the fixture has to actually filter something")
        self.assertTrue(app.reveal_turn(100))
        self.assertEqual(app.transcript_offset, position // PAGE * PAGE)
        self.assertEqual(app.scrolled, [position - app.transcript_offset])

    def test_a_turn_the_filter_hides_is_reported_rather_than_guessed_at(self) -> None:
        app = self.app(only_unchecked=True)
        self.assertNotIn(0, app.order, "turn 0 is checked, so the filter hides it")
        self.assertFalse(app.reveal_turn(0))
        self.assertEqual(app.scrolled, [])
        self.assertEqual(app.rendered, [])

    def test_revealing_never_rebuilds_the_screen(self) -> None:
        """Playback ticks call this constantly; a rebuild there would be unusable."""
        app = self.app()
        for index in (5, 150, 199):
            self.assertTrue(app.reveal_turn(index))
        self.assertEqual(app.rendered, [])

    def test_nothing_to_reveal_is_not_an_error(self) -> None:
        app = self.app()
        self.assertFalse(app.reveal_turn(None))
        self.assertFalse(app.reveal_turn(9999))


class ResumeTests(unittest.TestCase):
    """Resume promises to take you there, so it clears a filter that would hide it."""

    def app(self, stored: int, only_unchecked: bool):
        import main
        controller = AppController(state())
        controller.state.show_only_unchecked = only_unchecked
        controller.state.last_reviewed_index = stored
        order = review_progress.visible_order(controller.state.transcript_segments, only_unchecked)
        told: list[str] = []
        app = SimpleNamespace(controller=controller, transcript_offset=0, selected_segment=None,
                              refs={"visible_order": order, "listing": object()},
                              render=noop, page=None)
        app.current_order = lambda: main.DesktopApp.current_order(app)
        app.scroll_to_row = noop
        app.reveal_turn = lambda index, allow=True: main.DesktopApp.reveal_turn(app, index, allow)
        app.resume_target = lambda: main.DesktopApp.resume_target(app)
        app.select_segment = lambda index: setattr(app, "selected_segment", index)
        app.told = told
        return app

    def resume(self, app) -> None:
        import main
        original = main.notification
        main.notification = lambda page, message: app.told.append(message)
        try:
            main.DesktopApp.resume_review(app)
        finally:
            main.notification = original

    def test_it_opens_the_turn_you_stopped_on(self) -> None:
        app = self.app(stored=150, only_unchecked=False)
        self.resume(app)
        self.assertEqual(app.selected_segment, 150)

    def test_a_filter_hiding_the_destination_is_cleared(self) -> None:
        """Where you stopped is very often a turn you had just checked."""
        app = self.app(stored=150, only_unchecked=True)
        self.assertNotIn(150, app.current_order(), "150 is checked, so the filter hides it")
        self.resume(app)
        self.assertFalse(app.controller.state.show_only_unchecked)
        self.assertEqual(app.selected_segment, 150)
        self.assertEqual(app.told, [s.FILTER_CLEARED], "and it says why the view changed")

    def test_a_visible_destination_leaves_the_filter_alone(self) -> None:
        app = self.app(stored=151, only_unchecked=True)
        self.assertIn(151, app.current_order())
        self.resume(app)
        self.assertTrue(app.controller.state.show_only_unchecked)
        self.assertEqual(app.told, [])


class LocateButtonTests(unittest.TestCase):
    def buttons(self, panel) -> list[ft.IconButton]:
        return [c for c in layout_audit.find(panel, lambda c: isinstance(c, ft.IconButton))
                if c.tooltip == s.INSPECTOR_LOCATE]

    def test_the_panel_offers_a_way_back_to_the_list(self) -> None:
        panel = speakers_view.inspector(state(10), 3, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop, on_locate=noop)
        self.assertEqual(len(self.buttons(panel)), 1)

    def test_pressing_it_asks_for_the_turn_to_be_shown(self) -> None:
        asked: list[bool] = []
        panel = speakers_view.inspector(state(10), 3, noop, noop, noop, {}, None, noop, noop,
                                        noop, noop, noop, on_locate=lambda: asked.append(True))
        self.buttons(panel)[0].on_click(None)
        self.assertEqual(asked, [True])

    def test_it_is_absent_when_there_is_nothing_to_locate_with(self) -> None:
        panel = speakers_view.inspector(state(10), 3, noop, noop, noop, {})
        self.assertEqual(self.buttons(panel), [])


if __name__ == "__main__": unittest.main()
