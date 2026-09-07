"""The keyboard, and the two transport buttons that do the same thing with a mouse.

Reviewing an interview is one hand on the keyboard and one on the audio. Everything here
is about that: can I go back ten seconds without losing my place, can I get from correcting
the wording to hearing a single word without hunting for a control, and does none of it
fire while I am in the middle of typing a sentence.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import flet as ft
import design_tokens as t
import layout_audit
import strings as s
from app_state import AppState
from audio_player import AudioPlayer
from components.audio_transport import audio_transport
from models import TranscriptSegment, Word
from views import speakers_view

noop = lambda *a, **k: None


class FakeAudio:
    """Just enough of the Audio service for the player to drive."""
    src = None
    def __init__(self): self.calls = []
    def play(self, position=0): self.calls.append(("play", position))
    def resume(self): self.calls.append(("resume", None))
    def pause(self): self.calls.append(("pause", None))
    def seek(self, position): self.calls.append(("seek", position))
    def update(self): ...


def player(position_ms: int = 60_000, duration_ms: int = 600_000,
           playing: bool = False) -> AudioPlayer:
    made = AudioPlayer(FakeAudio(), lambda fn, *a: fn(*a))
    made.path = "recording.m4a"
    made.loaded = True
    made._started = True
    made.duration_ms = duration_ms
    made.position_ms = position_ms
    made.playing = playing
    return made


class SkipTests(unittest.TestCase):
    def test_the_skip_goes_back(self) -> None:
        moved = player(position_ms=60_000)
        moved.skip(-t.SKIP_SECONDS)
        self.assertEqual(moved.position_ms, 60_000 - t.SKIP_SECONDS * 1000)

    def test_the_skip_goes_forward(self) -> None:
        moved = player(position_ms=60_000)
        moved.skip(t.SKIP_SECONDS)
        self.assertEqual(moved.position_ms, 60_000 + t.SKIP_SECONDS * 1000)

    def test_it_cannot_go_back_past_the_beginning(self) -> None:
        moved = player(position_ms=3_000)
        moved.skip(-10)
        self.assertEqual(moved.position_ms, 0)

    def test_it_cannot_run_off_the_end(self) -> None:
        moved = player(position_ms=599_000, duration_ms=600_000)
        moved.skip(10)
        self.assertLessEqual(moved.position_ms, 600_000)
        self.assertGreater(moved.position_ms, 0)

    def test_skipping_while_paused_leaves_it_paused(self) -> None:
        """Checking a word means jumping back without the audio starting up again."""
        paused = player(playing=False)
        paused.skip(-10)
        self.assertFalse(paused.playing)

    def test_skipping_while_playing_keeps_playing(self) -> None:
        running = player(playing=True)
        running.skip(-10)
        self.assertTrue(running.playing)

    def test_a_player_with_nothing_loaded_ignores_it(self) -> None:
        empty = AudioPlayer(None, lambda fn, *a: fn(*a))
        self.assertIsNone(empty.skip(-10))

    def test_the_jump_is_the_one_the_buttons_and_the_arrows_share(self) -> None:
        self.assertEqual(t.SKIP_SECONDS, 5, "short enough to re-hear a word, not a sentence")


class TransportTests(unittest.TestCase):
    def bar(self, on_skip=noop, ready: bool = True) -> ft.Control:
        made = player() if ready else AudioPlayer(None, lambda fn, *a: fn(*a))
        return audio_transport(made, {}, noop, on_skip)

    def buttons(self, bar) -> list[ft.IconButton]:
        return layout_audit.find(bar, lambda c: isinstance(c, ft.IconButton))

    def test_back_and_forward_sit_either_side_of_play(self) -> None:
        row = [c for c in self.buttons(self.bar())]
        self.assertGreaterEqual(len(row), 3)
        self.assertEqual(row[0].icon, ft.Icons.REPLAY_5)
        self.assertEqual(row[1].icon, ft.Icons.PLAY_ARROW)
        self.assertEqual(row[2].icon, ft.Icons.FORWARD_5)

    def test_they_say_how_far_they_jump(self) -> None:
        row = self.buttons(self.bar())
        self.assertEqual(row[0].tooltip, s.PLAYER_BACK.format(seconds=t.SKIP_SECONDS))
        self.assertEqual(row[2].tooltip, s.PLAYER_FORWARD.format(seconds=t.SKIP_SECONDS))

    def test_they_report_the_direction(self) -> None:
        seen: list[float] = []
        row = self.buttons(self.bar(seen.append))
        row[0].on_click(None)
        row[2].on_click(None)
        self.assertEqual(seen, [-float(t.SKIP_SECONDS), float(t.SKIP_SECONDS)])

    def test_they_are_dead_with_no_recording_loaded(self) -> None:
        for button in self.buttons(self.bar(ready=False))[:3]:
            self.assertTrue(button.disabled)

    def test_they_get_the_same_hit_area_as_every_other_icon(self) -> None:
        for button in self.buttons(self.bar()):
            self.assertEqual(button.width, t.ICON_BUTTON)


def turn(index: int, timed: bool = True) -> TranscriptSegment:
    words = [Word(index * 10 + i, index * 10 + i + 1, w, .9)
             for i, w in enumerate(("this", "is", "a", "turn"))] if timed else []
    return TranscriptSegment(0, 0.0, f"raw{index}", f"SPEAKER_{index % 2}", index * 10,
                             index * 10 + 8, index * 10, index * 10 + 8,
                             "this is a turn", None, False, words, .9)


def state(count: int = 4, timed: bool = True) -> AppState:
    made = AppState()
    made.transcript_segments = [turn(i, timed) for i in range(count)]
    return made


class ModeSwitchTests(unittest.TestCase):
    """Getting from correcting the wording to clicking a word was the hard part."""

    def panel(self, words_mode: bool = False, timed: bool = True, on_words_mode=noop):
        return speakers_view.inspector(state(timed=timed), 0, noop, noop, noop, {}, None, noop,
                                       noop, noop, noop, noop, words_mode=words_mode,
                                       on_words_mode=on_words_mode)

    def labels(self, panel) -> list[str]:
        return [c.value for c in layout_audit.walk(panel) if isinstance(c, ft.Text) and c.value]

    def test_both_modes_are_named_on_screen_not_hidden_behind_an_icon(self) -> None:
        shown = self.labels(self.panel())
        self.assertIn(s.MODE_EDIT, shown)
        self.assertIn(s.MODE_WORDS, shown)

    def test_the_switch_sits_directly_above_the_text_it_switches(self) -> None:
        panel = self.panel()
        slot = [c for c in layout_audit.walk(panel)
                if isinstance(c, ft.Column) and len(c.controls or []) == 2
                and any(isinstance(x, ft.TextField) for x in c.controls)]
        self.assertEqual(len(slot), 1, "the switch and the editor are one block")
        self.assertIn(s.MODE_EDIT, self.labels(slot[0].controls[0]))

    def test_choosing_the_other_mode_reports_it(self) -> None:
        seen: list[bool] = []
        panel = self.panel(on_words_mode=lambda: seen.append(True))
        switch = [c for c in layout_audit.walk(panel)
                  if isinstance(c, ft.Container) and c.on_click is not None
                  and s.MODE_WORDS in self.labels(c)]
        self.assertEqual(len(switch), 1)
        switch[0].on_click(None)
        self.assertEqual(seen, [True])

    def test_the_mode_you_are_in_is_not_a_button(self) -> None:
        """Clicking the option you are already on should do nothing at all."""
        for words_mode, active in ((False, s.MODE_EDIT), (True, s.MODE_WORDS)):
            with self.subTest(mode=active):
                panel = self.panel(words_mode=words_mode)
                # The open tab is the colour of the sheet below it, so tab and text read as
                # one surface — the editor look, in place of the earlier tinted pill.
                current = [c for c in layout_audit.walk(panel)
                           if isinstance(c, ft.Container) and active in self.labels(c)
                           and c.bgcolor == t.surface()]
                self.assertTrue(current)
                self.assertIsNone(current[0].on_click)

    def test_words_mode_swaps_the_editor_for_clickable_words(self) -> None:
        editing = self.panel(words_mode=False)
        listening = self.panel(words_mode=True)
        self.assertEqual(len(layout_audit.find(editing, lambda c: isinstance(c, ft.TextField))), 1)
        self.assertEqual(len(layout_audit.find(listening, lambda c: isinstance(c, ft.TextField))), 0)
        spans = [c for c in layout_audit.walk(listening) if isinstance(c, ft.Text) and c.spans]
        self.assertTrue(spans, "the words have to be there to click")
        self.assertTrue(all(span.on_click for span in spans[0].spans))

    def test_no_switch_when_the_provider_never_timed_the_words(self) -> None:
        shown = self.labels(self.panel(timed=False))
        self.assertNotIn(s.MODE_WORDS, shown, "offering a mode that cannot work is worse")

    def test_the_switch_is_gone_from_the_row_of_icon_buttons(self) -> None:
        """It used to be one small icon among four, which is what made it hard to find."""
        tooltips = {c.tooltip for c in layout_audit.find(
            self.panel(), lambda c: isinstance(c, ft.IconButton))}
        self.assertNotIn(s.SEEK_WORDS, tooltips)
        self.assertIn(s.INSERT_TIMESTAMP, tooltips)


class _Press:
    """Drives `_route_key` as an unbound method over a stand-in, so routing is testable without
    a window. A mixin rather than a base test class, so a second group of key tests does not
    silently re-run the first group's assertions as well."""

    def press(self, key: str, ctrl: bool = False, typing: bool = False,
              reviewing: bool = True, segments: int = 4, shift: bool = False) -> list[str]:
        """Drive `on_key` over a stand-in, so routing is testable without a window."""
        import main
        fired: list[str] = []
        record = lambda name: (lambda *a, **k: fired.append(name))
        app_state = state(segments)
        app_state.current_workflow_step = 2 if reviewing else 0
        stand_in = SimpleNamespace(
            LEFT_KEYS=main.DesktopApp.LEFT_KEYS, RIGHT_KEYS=main.DesktopApp.RIGHT_KEYS,
            UP_KEYS=main.DesktopApp.UP_KEYS, DOWN_KEYS=main.DesktopApp.DOWN_KEYS,
            ENTER_KEYS=main.DesktopApp.ENTER_KEYS, PLAY_KEYS=main.DesktopApp.PLAY_KEYS,
            PLAY_LETTERS=main.DesktopApp.PLAY_LETTERS,
            SLOT_KEYS=main.DesktopApp.SLOT_KEYS, CLEAR_KEYS=main.DesktopApp.CLEAR_KEYS,
            controller=SimpleNamespace(state=app_state), show_settings=False, show_home=False,
            find_open=True, typing=typing, selected_segment=1,
            commit_correction=record("commit_correction"),
            mark_from_keyboard=record("mark_from_keyboard"),
            comment_from_keyboard=record("comment_from_keyboard"),
            clear_from_keyboard=record("clear_from_keyboard"),
            locate_open_turn=record("locate_open_turn"), play_segment=record("play_segment"),
            toggle_unchecked_filter=record("toggle_unchecked_filter"),
            resume_review=record("resume_review"), resume_target=lambda: 0,
            close_find=record("close_find"), step_turn=record("step_turn"),
            mark_and_advance=record("mark_and_advance"), save_project=record("save_project"),
            open_project=record("open_project"), open_find=record("open_find"),
            insert_timestamp=record("insert_timestamp"),
            toggle_words_mode=record("toggle_words_mode"),
            skip_audio=record("skip_audio"),
            save_project_as=record("save_project_as"), toggle_note=record("toggle_note"),
            player=SimpleNamespace(toggle=record("toggle")))
        main.DesktopApp._route_key(stand_in, SimpleNamespace(key=key, ctrl=ctrl, shift=shift))
        return fired


class KeyRoutingTests(_Press, unittest.TestCase):
    """`on_key` is called with a real key name and has to route it, or deliberately not."""

    def test_the_plain_keys(self) -> None:
        self.assertEqual(self.press(" "), ["toggle"])
        self.assertEqual(self.press("Arrow Left"), ["skip_audio"])
        self.assertEqual(self.press("Arrow Right"), ["skip_audio"])
        self.assertEqual(self.press("Arrow Up"), ["step_turn"])
        self.assertEqual(self.press("Arrow Down"), ["step_turn"])
        self.assertEqual(self.press("Escape"), ["close_find"])

    def test_the_control_keys(self) -> None:
        for key, expected in (("f", "open_find"), ("t", "insert_timestamp"),
                              ("k", "toggle_words_mode"),
                              ("o", "open_project"),
                              ("Enter", "mark_and_advance"),
                              ("Arrow Left", "skip_audio"), ("Arrow Right", "skip_audio"),
                              ("Arrow Up", "step_turn"), ("Arrow Down", "step_turn")):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, ctrl=True), [expected])

    def test_the_audio_keys_all_work_with_the_caret_in_a_field(self) -> None:
        """Stopping and stepping the recording is exactly what is wanted mid-sentence.

        Space is not among them on purpose: Flet cannot consume a key, so the field would
        receive it too and a space would land in the sentence.
        """
        for key in ("w", "Arrow Left", "Arrow Right"):
            with self.subTest(key=key):
                self.assertNotEqual(self.press(key, ctrl=True, typing=True), [])

    def test_the_audio_keys_are_not_tied_to_one_screen(self) -> None:
        for key, expected in (("w", "toggle"), ("Arrow Left", "skip_audio"),
                              ("Arrow Right", "skip_audio")):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, ctrl=True, reviewing=False), [expected])

    def test_the_play_key_does_nothing_else_in_any_context(self) -> None:
        """One key, one effect. Whatever the screen, whatever has focus, whatever is open."""
        for context in ({}, {"typing": True}, {"reviewing": False}, {"segments": 0},
                        {"typing": True, "reviewing": False}):
            with self.subTest(**context):
                self.assertEqual(self.press("w", ctrl=True, **context), ["toggle"])
                self.assertEqual(self.press("F4", **context), ["toggle"])

    def test_the_play_key_is_a_letter_the_user_chose(self) -> None:
        """F4 was a reach and Ctrl+K was not what they wanted to press. It is Ctrl+W."""
        import main
        self.assertEqual(main.DesktopApp.PLAY_LETTERS, ("w",))
        self.assertEqual(self.press("W", ctrl=True), ["toggle"], "case makes no difference")

    def test_a_letter_cannot_be_mistaken_for_a_scroll(self) -> None:
        """This is the whole reason it is not Space: a focused list scrolls on Space."""
        import main
        self.assertNotIn(" ", main.DesktopApp.PLAY_LETTERS)
        self.assertNotIn("Space", main.DesktopApp.PLAY_KEYS)

    def test_the_play_key_is_answered_before_any_other_rule(self) -> None:
        """Read from the source: it must not sit behind a guard that could skip it."""
        import ast, inspect, main
        body = ast.parse(inspect.getsource(main.DesktopApp._route_key).strip()).body[0].body
        statements = [node for node in body if not isinstance(node, ast.Expr)]
        first = statements[0]
        while isinstance(first, ast.Assign):
            statements.pop(0); first = statements[0]
        self.assertIsInstance(first, ast.If)
        self.assertIn("PLAY_KEYS", ast.unparse(first.test),
                      "the play key has to be the first decision the handler makes")

    def test_pressing_play_never_moves_the_view(self) -> None:
        """The complaint was that it sometimes scrolled. Its branch calls one thing."""
        import ast, inspect, main
        source = inspect.getsource(main.DesktopApp._route_key).strip()
        branch = ast.parse(source).body[0].body
        play = next(node for node in branch
                    if isinstance(node, ast.If) and "PLAY_KEYS" in ast.unparse(node.test))
        # The body of the branch, not its condition: matching the key is not an effect.
        calls = {ast.unparse(node.func) for statement in play.body
                 for node in ast.walk(statement) if isinstance(node, ast.Call)}
        self.assertEqual(calls, {"self.player.toggle"},
                         f"play/pause must call nothing but the player, got {calls}")

    def test_save_writes_the_sentence_in_the_box_before_it_writes_the_file(self) -> None:
        """Ctrl+S used to save the project around an unsaved correction and then report
        "Saved" — the one thing a save key must never do."""
        self.assertEqual(self.press("s", ctrl=True), ["commit_correction", "save_project"])

    def test_shift_turns_save_into_save_as(self) -> None:
        self.assertEqual(self.press("s", ctrl=True, shift=True), ["save_project_as"])
        self.assertEqual(self.press("s", ctrl=True, shift=True, segments=0), [],
                         "nothing to save anywhere")

    def test_typing_swallows_the_plain_keys_and_nothing_else(self) -> None:
        """Space has to be a space, and the arrows have to move the caret."""
        for key in (" ", "Arrow Left", "Arrow Right", "Arrow Up", "Arrow Down"):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, typing=True), [])
        for key in ("Enter", "k", "t"):
            with self.subTest(key=key, ctrl=True):
                self.assertNotEqual(self.press(key, ctrl=True, typing=True), [],
                                    "Ctrl shortcuts are wanted most while typing")

    def test_nothing_review_related_fires_off_the_review_screen(self) -> None:
        for key, ctrl in ((" ", False), ("Arrow Left", False), ("Arrow Up", False),
                          ("k", True), ("Enter", True), ("Arrow Up", True)):
            with self.subTest(key=key, ctrl=ctrl):
                self.assertEqual(self.press(key, ctrl=ctrl, reviewing=False), [])

    def test_open_a_project_works_anywhere_saving_needs_something_to_save(self) -> None:
        self.assertEqual(self.press("o", ctrl=True, reviewing=False), ["open_project"])
        self.assertEqual(self.press("s", ctrl=True, segments=0), [], "nothing to save yet")
        self.assertEqual(self.press("s", ctrl=True, segments=3),
                         ["commit_correction", "save_project"])

    def test_the_arrow_spellings_other_builds_use_are_accepted(self) -> None:
        for key in ("Arrow Left", "ArrowLeft", "Left"):
            with self.subTest(key=key):
                self.assertEqual(self.press(key), ["skip_audio"])


class HelpTests(unittest.TestCase):
    def test_every_shortcut_the_app_answers_to_is_written_down(self) -> None:
        written = " ".join(s.shortcuts(t.SKIP_SECONDS))
        for shortcut in ("Space", "Left", "Right", "Ctrl+Enter", "Ctrl+W", "Ctrl+K", "Ctrl+T",
                         "Ctrl+U", "Ctrl+F", "Ctrl+S", "Ctrl+O", "Esc"):
            with self.subTest(shortcut=shortcut):
                self.assertIn(shortcut, written)

    def test_it_says_space_yields_to_typing(self) -> None:
        self.assertIn("text field", " ".join(s.shortcuts(t.SKIP_SECONDS)))

    def test_the_help_cannot_claim_a_jump_length_the_app_does_not_use(self) -> None:
        """It went on saying ten seconds after the jump became five."""
        written = " ".join(s.shortcuts(t.SKIP_SECONDS))
        self.assertIn(f"{t.SKIP_SECONDS} seconds back or forward", written)
        self.assertNotIn("{seconds}", written, "every placeholder is filled in")

    def test_the_help_names_the_play_key_the_player_button_names(self) -> None:
        self.assertIn("Ctrl+W", s.PLAYER_PLAY)
        self.assertIn("Ctrl+W", " ".join(s.shortcuts(t.SKIP_SECONDS)))


if __name__ == "__main__": unittest.main()


class MarkingKeyTests(_Press, unittest.TestCase):
    """Marking a phrase without leaving the keyboard. All under Ctrl, because the caret is
    inside the text at the moment the selection exists."""

    def test_the_three_highlighters_are_on_the_digit_row(self) -> None:
        for key in ("1", "2", "3"):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, ctrl=True), ["mark_from_keyboard"])

    def test_the_digit_spellings_other_builds_use_are_accepted(self) -> None:
        for key in ("2", "Digit 2", "Numpad 2"):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, ctrl=True), ["mark_from_keyboard"])

    def test_bold_comment_and_clear_have_keys_of_their_own(self) -> None:
        self.assertEqual(self.press("b", ctrl=True), ["mark_from_keyboard"])
        self.assertEqual(self.press("d", ctrl=True), ["comment_from_keyboard"])
        self.assertEqual(self.press("0", ctrl=True), ["clear_from_keyboard"])

    def test_they_work_with_the_caret_still_in_the_text(self) -> None:
        """Which is the only moment there is anything selected to mark."""
        for key in ("b", "1", "0", "d"):
            with self.subTest(key=key):
                self.assertTrue(self.press(key, ctrl=True, typing=True))

    def test_none_of_them_fire_away_from_the_review_screen(self) -> None:
        for key in ("b", "1", "0", "d", "j", "e", "r", "p"):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, ctrl=True, reviewing=False), [])

    def test_the_review_keys_reach_their_own_actions(self) -> None:
        for key, expected in (("j", "locate_open_turn"), ("p", "play_segment"),
                              ("e", "toggle_unchecked_filter"), ("r", "resume_review")):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, ctrl=True), [expected])

    def test_a_digit_on_its_own_is_still_a_digit_in_the_text(self) -> None:
        for key in ("1", "0"):
            with self.subTest(key=key):
                self.assertEqual(self.press(key, typing=True), [])


class KeyFailureTests(unittest.TestCase):
    """A shortcut that fails must say so, not take the window with it."""

    def app(self, boom):
        import main
        shown: list[str] = []
        page = SimpleNamespace(show_dialog=lambda control: shown.append(control))
        stand_in = SimpleNamespace(_route_key=boom, page=page)
        return main, stand_in, shown

    def test_a_failing_shortcut_is_caught_rather_than_raised(self) -> None:
        def boom(event): raise RuntimeError("no such row")
        main, stand_in, _ = self.app(boom)
        main.DesktopApp.on_key(stand_in, SimpleNamespace(key="u", ctrl=True))

    def test_the_failure_is_put_in_front_of_the_researcher(self) -> None:
        """A built application has no console; a message is the only place it can appear."""
        def boom(event): raise RuntimeError("no such row")
        main, stand_in, shown = self.app(boom)
        main.DesktopApp.on_key(stand_in, SimpleNamespace(key="u", ctrl=True))
        self.assertEqual(len(shown), 1)

    def test_a_key_that_works_is_not_wrapped_in_anything(self) -> None:
        seen: list[str] = []
        main, stand_in, shown = self.app(lambda event: seen.append(event.key))
        main.DesktopApp.on_key(stand_in, SimpleNamespace(key="u", ctrl=True))
        self.assertEqual(seen, ["u"])
        self.assertEqual(shown, [])
