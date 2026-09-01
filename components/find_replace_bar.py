"""Find and replace as a floating tool, not a block in the page.

It docks under the top bar in the right-hand corner of the content area and floats over the
transcript: opening it moves nothing. Live counting happens as the researcher types, before
anything is changed, so Replace all is never a leap of faith. The bar reports its own text
focus, because Space belongs to the search box while it is being typed in.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import primary_button, tertiary_button
from components import overlay


def match_summary(term: str, matches: int, turns: int) -> tuple[str, str]:
    """The live count and the colour it is shown in. One place, so the bar and the
    in-place update in `main` can never drift apart."""
    if not (term or "").strip():
        return s.FIND_COUNT_EMPTY, t.muted()
    if matches:
        return s.FIND_COUNT.format(count=matches, turns=turns), t.on_surface()
    return s.FIND_COUNT_NONE, t.muted()


def find_replace_bar(term: str, replacement: str, case_sensitive: bool, whole_word: bool,
                     matches: int, turns: int, can_undo: bool,
                     on_change: Callable[[str, str, bool, bool], None],
                     on_replace_all: Callable[[], None], on_undo: Callable[[], None],
                     on_close: Callable[[], None], refs: dict | None = None,
                     on_typing: Callable[[bool], None] | None = None,
                     available: float | None = None) -> ft.Control:
    def field(label: str, value: str, key: str, focus: bool = False) -> ft.TextField:
        control = ft.TextField(label=label, value=value, dense=True, height=t.FIELD_HEIGHT_DENSE,
                               expand=True, autofocus=focus,
                               border_radius=t.R_SM, border_color=t.outline(),
                               focused_border_color=t.primary(), color=t.on_surface(),
                               text_size=t.TYPE_SECONDARY,
                               label_style=ft.TextStyle(size=t.TYPE_LABEL, color=t.muted()),
                               content_padding=ft.Padding(t.S12, t.S8, t.S12, t.S8),
                               on_focus=(lambda e: on_typing(True)) if on_typing else None,
                               on_blur=(lambda e: on_typing(False)) if on_typing else None)
        if refs is not None:
            refs[key] = control
        return control

    # The cursor lands in Find, so Ctrl+F is followed straight by typing.
    find = field(s.FIND_LABEL, term, "find_term", focus=True)
    into = field(s.REPLACE_LABEL, replacement, "find_replacement")

    def toggle(label: str, value: bool) -> ft.Checkbox:
        return ft.Checkbox(label, value=value, active_color=t.primary(),
                           check_color=t.on_primary(),
                           label_style=ft.TextStyle(size=t.TYPE_LABEL, color=t.on_surface_variant()))

    case_box = toggle(s.FIND_CASE, case_sensitive)
    word_box = toggle(s.FIND_WHOLE_WORD, whole_word)

    def changed(event: ft.Event | None = None) -> None:
        on_change(find.value or "", into.value or "", bool(case_box.value), bool(word_box.value))

    # Every control that can change the outcome reports it. The replacement field used to be
    # left out, so Replace all ran with an empty replacement and silently deleted the term.
    find.on_change = changed
    into.on_change = changed
    case_box.on_change = changed
    word_box.on_change = changed

    summary, tone = match_summary(term, matches, turns)
    count = ft.Text(summary, size=t.TYPE_LABEL, color=tone, no_wrap=True)
    if refs is not None:
        refs["find_count"] = count

    # Replace all is the only weighted control here, and it is dead until there is
    # something to replace: the count and the button always tell the same story.
    actions: list[ft.Control] = [ft.Container(expand=True)]
    if can_undo:
        actions.append(tertiary_button(s.FIND_UNDO, lambda e: on_undo()))
    apply = primary_button(s.FIND_REPLACE_ALL, lambda e: on_replace_all(), disabled=not matches)
    # Registered so the live recount can wake it up. Typing a term used to update the count
    # and leave the button dead, because the panel is not rebuilt on every keystroke.
    if refs is not None:
        refs["find_apply"] = apply
    actions.append(apply)

    rows = [
        ft.Row([find, into], spacing=t.S12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([case_box, word_box, *actions], spacing=t.S8,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Text(s.FIND_HINT, size=t.TYPE_CAPTION, color=t.muted()),
    ]
    panel, width = overlay.floating_panel(s.FIND_REPLACE, rows, on_close,
                                          ft.Icons.FIND_REPLACE, available, count,
                                          close_tooltip=s.FIND_CLOSE)
    if refs is not None:
        refs["find_panel_width"] = width
    return panel
