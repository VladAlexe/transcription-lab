"""Pressing the buttons, not merely drawing them.

Every other test on these screens builds the controls and reads them. None of them ever
pressed Save — which is how the settings screen shipped with a Save button that raised
`AttributeError: 'Column' object has no attribute 'value'` on its first line, so nothing on
it could be saved at all: not the highlight names, not the reviewer, not the language.

The rule these tests hold is simple: a screen that offers to commit something has to be able
to commit it, and what it hands over has to be what the application accepts.
"""
from __future__ import annotations
import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flet as ft
import layout_audit
import strings as s
from app_state import AppState
from views import export_view, settings_view

noop = lambda *a, **k: None


def configured() -> AppState:
    state = AppState()
    state.settings.highlight_labels = ["Key quote", "Needs checking", "Follow up"]
    state.settings.reviewer = "Vlad Alexe"
    state.settings.language = "nl"
    state.settings.appearance = "dark"
    state.settings.type_scale = 1.15
    state.settings.auto_rewind_seconds = 2.5
    state.set_active_api_key("secret-key")
    return state


def button(screen: ft.Control, label: str):
    found = [c for c in layout_audit.walk(screen)
             if isinstance(c, (ft.Button, ft.OutlinedButton, ft.TextButton))
             and getattr(c, "content", None) == label]
    assert len(found) == 1, f"expected one {label!r} button, found {len(found)}"
    return found[0]


class SettingsSaveTests(unittest.TestCase):
    def save(self, state: AppState | None = None):
        """Build the screen, press Save, and return what it handed over."""
        sent: dict = {}
        keys: list[str] = []
        screen = settings_view.build(state or configured(),
                                     lambda *args: sent.update(args=args), noop, noop,
                                     lambda value: keys.append(value))
        button(screen, s.SETTINGS_SAVE).on_click(None)
        return sent.get("args"), keys

    def test_pressing_save_does_not_raise(self) -> None:
        """The crash itself: `apply` read `.value` off the label wrapper, not the input."""
        values, _ = self.save()
        self.assertIsNotNone(values, "Save handed over nothing")

    def test_the_highlight_names_reach_the_application(self) -> None:
        """What the researcher was doing when the screen fell over."""
        values, _ = self.save()
        self.assertIn(["Key quote", "Needs checking", "Follow up"], values)

    def test_the_reviewer_name_reaches_the_application(self) -> None:
        values, _ = self.save()
        self.assertIn("Vlad Alexe", values)

    def test_the_language_and_the_appearance_reach_the_application(self) -> None:
        values, _ = self.save()
        self.assertEqual(values[0], "dark")
        self.assertEqual(values[7], "nl")

    def test_the_numbers_arrive_as_numbers(self) -> None:
        values, _ = self.save()
        self.assertIsInstance(values[1], float)
        self.assertIsInstance(values[2], int)
        self.assertIsInstance(values[3], float)

    def test_the_api_key_is_handed_over_on_its_own(self) -> None:
        """It never travels with the rest, because the rest is written to preferences."""
        values, keys = self.save()
        self.assertEqual(keys, ["secret-key"])
        self.assertNotIn("secret-key", values)

    def test_a_screen_with_the_fragmenting_fields_shown_also_saves(self) -> None:
        """Those three inputs only exist on the OpenAI provider, so they are a second path
        through the same closure."""
        state = configured()
        state.settings.provider = "openai"
        values, _ = self.save(state)
        self.assertIsNotNone(values)

    def test_a_screen_with_the_endpoint_fields_shown_also_saves(self) -> None:
        state = configured()
        state.settings.provider = "compatible"
        state.compatible_base_url = "https://local.example/v1"
        state.compatible_model = "whisper-1"
        values, _ = self.save(state)
        self.assertIn("https://local.example/v1", values)
        self.assertIn("whisper-1", values)

    def test_what_the_screen_sends_is_what_the_application_accepts(self) -> None:
        """Binds the real handler's signature to the real call.

        This is the other half of the same failure: a screen can hand over the right number
        of values and still hand them over in the wrong order or of the wrong kind. Binding
        catches an argument added on one side and not the other.
        """
        import main
        values, _ = self.save()
        signature = inspect.signature(main.DesktopApp.apply_settings)
        signature.bind(object(), *values)


class SaveIsNotAWrapperTests(unittest.TestCase):
    """The generic form of the bug, so it cannot come back through another field.

    A layout wrapper has no `.value`. Any control the Save closure reads has to be an input,
    which is why `field` and `choice` return the control and the labelling happens where the
    row is built.
    """

    INPUTS = (ft.TextField, ft.Dropdown, ft.Switch, ft.Checkbox, ft.Slider, ft.RadioGroup)

    def test_every_control_the_screen_keeps_hold_of_is_an_input(self) -> None:
        source = inspect.getsource(settings_view.build)
        body = source.split("def apply(", 1)[1]
        read = {line.split(".value")[0].strip().split()[-1].lstrip("(")
                for line in body.splitlines() if ".value" in line}
        self.assertTrue(read, "the Save closure reads nothing at all")

    def test_the_helpers_return_a_control_and_not_a_column(self) -> None:
        """Read from the parse tree, not by slicing text: the helpers sit inside `build`,
        so a text search runs on past them into the rest of the screen."""
        import ast, textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(settings_view.build)))
        helpers = {node.name: node for node in ast.walk(tree)
                   if isinstance(node, ast.FunctionDef)}
        for helper, kind in (("field", "ft.TextField"), ("choice", "ft.Dropdown")):
            with self.subTest(helper=helper):
                returns = [ast.unparse(node.value) for node in ast.walk(helpers[helper])
                           if isinstance(node, ast.Return) and node.value is not None]
                self.assertEqual(len(returns), 1)
                # `syncing(...)` may wrap it — that hands back the same control — but a
                # label wrapper must never come out of here.
                self.assertIn(kind, returns[0])
                self.assertNotIn("labelled", returns[0])

    def test_the_label_wrapper_is_only_ever_used_inside_a_row(self) -> None:
        """`labelled` returns the Column that a ResponsiveRow lays out. Assigning it to a
        name and reading it later is exactly what broke."""
        source = inspect.getsource(settings_view.build)
        assignments = [line for line in source.splitlines()
                       if "= labelled(" in line and not line.strip().startswith("#")]
        self.assertEqual(assignments, [], f"a wrapper is being kept: {assignments}")


class ExportCommitTests(unittest.TestCase):
    """The other screen with a commit closure over its own inputs."""

    def test_changing_a_field_does_not_raise(self) -> None:
        sent: list = []
        state = configured()
        screen = export_view.build(state, noop, lambda *args: sent.append(args))
        fields = [c for c in layout_audit.walk(screen) if isinstance(c, ft.TextField)]
        self.assertTrue(fields)
        fields[0].on_change(None)
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(sent[0]), 7)

    def test_every_export_field_carries_its_own_handler(self) -> None:
        state = configured()
        screen = export_view.build(state, noop, noop)
        inputs = [c for c in layout_audit.walk(screen)
                  if isinstance(c, (ft.TextField, ft.Checkbox))]
        self.assertTrue(inputs)
        for control in inputs:
            with self.subTest(control=type(control).__name__):
                self.assertIsNotNone(control.on_change)


if __name__ == "__main__":
    unittest.main()
