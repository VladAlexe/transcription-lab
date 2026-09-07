"""Marking a phrase inside a turn, rather than the whole turn.

Flet's text field cannot draw bold and highlight inside itself — an editable field is one
uniform style, and no framework option changes that. So the marking is shown the only
honest way: a read-only preview under the box, painted from the same run-splitting the Word
exporter uses. What is on screen is what the document will contain.
"""
from __future__ import annotations
from typing import Callable

import flet as ft

import annotations as an
import design_tokens as t
import strings as s
from components.buttons import icon_button
from theme import panel_title

SWATCH = 22
# Dimmed while nothing is selected, but still recognisably the three colours: at a third
# they read as mud, which looks like a fault rather than like "not yet".
DIM = 0.5


def label_for(labels: list[str] | None, slot: str) -> str:
    """The researcher's name for a colour, or a neutral one until they give it a name."""
    index = int(slot) - 1
    names = list(labels or [])
    if 0 <= index < len(names) and (names[index] or "").strip():
        return names[index].strip()
    return s.MARK_UNNAMED.format(number=slot)


def preview(text: str, marks: list[an.Annotation], labels: list[str] | None) -> ft.Control:
    """The turn as Word will render it: real bold, the real highlighter colours.

    Commented stretches are underlined rather than tinted, because a comment is not a
    colour and giving it one would collide with the code the highlights carry.
    """
    spans: list[ft.TextSpan] = []
    for piece in an.runs(text, marks):
        style = ft.TextStyle(size=t.TYPE_SECONDARY,
            color=an.ink(piece.slot) if piece.slot else t.on_surface(),
            bgcolor=an.colour(piece.slot) if piece.slot else None,
            weight=ft.FontWeight.W_700 if piece.bold else ft.FontWeight.W_400,
            decoration=ft.TextDecoration.UNDERLINE if piece.comments else None,
            decoration_color=t.primary(), decoration_style=ft.TextDecorationStyle.DOTTED)
        spans.append(ft.TextSpan(piece.text, style))
    return ft.Container(ft.Text(spans=spans, selectable=True, size=t.TYPE_SECONDARY,
            color=t.on_surface()),
        padding=t.S12, bgcolor=t.surface_variant(), border_radius=t.R_SM,
        border=ft.Border.all(t.HAIRLINE, t.outline()))


def comment_list(marks: list[an.Annotation],
                 on_remove: Callable[[an.Annotation], None] | None) -> list[ft.Control]:
    """Every comment on this turn, with the phrase it sits on.

    A comment anchored inside a paragraph is invisible until the document is opened in Word;
    listed here it can be read, and taken back, without leaving the panel.
    """
    rows: list[ft.Control] = []
    for mark in [m for m in marks if m.kind == an.COMMENT]:
        rows.append(ft.Row([
            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=13, color=t.primary()),
            ft.Column([
                ft.Text(f"“{mark.quote}”", size=t.TYPE_CAPTION, color=t.muted(),
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(mark.note, size=t.TYPE_LABEL, color=t.on_surface(), max_lines=3)],
                spacing=0, tight=True, expand=True),
            icon_button(ft.Icons.CLOSE, s.MARK_CLEAR,
                (lambda e, m=mark: on_remove(m)) if on_remove else None, size=13)],
            spacing=t.S8, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return rows


def marking_bar(field: ft.TextField, marks: list[an.Annotation], labels: list[str] | None,
                on_mark: Callable[[int, int, str, str], None],
                on_comment: Callable[[int, int], None],
                on_clear: Callable[[int, int], None],
                refs: dict | None = None) -> ft.Control:
    """Bold, three highlighters, a comment, and a way to undo them — for the live selection.

    The buttons are dead until something is selected and come alive when it is, so the bar
    answers "can I do this now?" without being read. Nothing here is a dialog or a mode: the
    text stays selected, the mark lands, the researcher carries on reading.
    """
    span = {"start": 0, "end": 0}
    # The same dict, not a copy: the keyboard shortcuts read the live selection from here,
    # so Ctrl+B marks what is selected in the box rather than what was selected at build.
    if refs is not None: refs["selection"] = span
    marked = sum(1 for m in marks if m.valid)
    # The hint gets a line of its own. Sharing the button row meant it was truncated to
    # "Select text above, then mar…" at every panel width, which is a hint that has to be
    # guessed at rather than read.
    hint = ft.Text(s.MARK_HINT, size=t.TYPE_CAPTION, color=t.muted(),
                   max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
    controls: list[ft.Control] = []

    def act(handler: Callable[..., None], *extra) -> Callable[[ft.Event], None]:
        def run(event: ft.Event) -> None:
            if span["end"] > span["start"]:
                handler(span["start"], span["end"], *extra)
        return run

    bold = icon_button(ft.Icons.FORMAT_BOLD, s.MARK_BOLD,
                       act(on_mark, an.BOLD, ""), size=16, disabled=True)
    controls.append(bold)
    swatches: list[ft.Control] = []
    for slot in an.SLOTS:
        # A swatch painted in the colour it applies. A named colour reads as a code; the
        # name comes from Settings and shows up here as the tooltip.
        swatch = ft.Container(width=SWATCH, height=SWATCH, bgcolor=an.colour(slot),
            border_radius=t.R_SM, border=ft.Border.all(t.HAIRLINE, t.outline()),
            tooltip=s.MARK_HIGHLIGHT.format(label=label_for(labels, slot)),
            on_click=act(on_mark, an.HIGHLIGHT, slot), ink=True, disabled=True,
            opacity=DIM, animate_opacity=120)
        swatches.append(swatch)
    controls.extend(swatches)
    comment = icon_button(ft.Icons.ADD_COMMENT_OUTLINED, s.MARK_COMMENT,
                          act(on_comment), size=16, disabled=True)
    # Clear is the one button that must not wait for a selection. Applying a mark rebuilds
    # this panel, which forgets the selection, so the moment a researcher wanted to undo it
    # the button was greyed out and pressing it did nothing at all. With nothing selected it
    # now clears the whole turn, which is what a button sitting beside "3 marked" promises.
    clear = icon_button(ft.Icons.FORMAT_CLEAR, s.MARK_CLEAR_ALL if marked else s.MARK_CLEAR,
                        lambda e: on_clear(span["start"], span["end"]), size=16,
                        disabled=not marked)
    controls.extend([comment, clear])

    def selected(event) -> None:
        selection = getattr(event, "selection", None)
        span["start"] = getattr(selection, "start", 0) or 0
        span["end"] = getattr(selection, "end", 0) or 0
        live = span["end"] > span["start"]
        quote = (getattr(event, "selected_text", "") or "").strip()
        hint.value = f"“{quote}”" if live and quote else s.MARK_HINT
        hint.color = t.on_surface_variant() if live else t.muted()
        for control in (bold, comment):
            control.disabled = not live
        clear.disabled = not (live or marked)
        clear.tooltip = s.MARK_CLEAR if live else s.MARK_CLEAR_ALL
        for swatch in swatches:
            swatch.disabled = not live
            swatch.opacity = 1.0 if live else DIM
        for control in (*controls, hint):
            try: control.update()
            except Exception: pass  # not yet on the page, on the first render
    field.on_selection_change = selected

    trailing = ft.Text(s.MARK_COUNT.format(count=marked), size=t.TYPE_CAPTION,
                       color=t.muted(), no_wrap=True) if marked else ft.Container()
    return ft.Column([
        ft.Row([*controls, ft.Container(expand=True), trailing],
               spacing=t.S4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        hint], spacing=t.S4, tight=True)
