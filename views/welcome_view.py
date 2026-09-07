"""The first screen, and Home.

They are the same content shown twice. On the very first run it fills the window with no
application chrome around it, because there is nothing yet to navigate. Afterwards the
wordmark in the sidebar brings it back as Home, inside the shell, with the reference
material a person actually returns for: the four steps, the shortcuts, what the marking
colours do, what each export contains, and what leaves the computer.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.brand import hero
from components.buttons import primary_button, secondary_button
from theme import card, page_title, panel_title

FACTS = ((ft.Icons.LOCK_OUTLINE, s.WELCOME_FACT_LOCAL),
         (ft.Icons.CLOUD_UPLOAD_OUTLINED, s.WELCOME_FACT_UPLOAD),
         (ft.Icons.KEY_OUTLINED, s.WELCOME_FACT_KEY))


def _paragraph(text: str) -> ft.Control:
    return ft.Text(text, size=t.TYPE_SECONDARY, color=t.on_surface_variant())


def _group(title: str, *body: ft.Control) -> ft.Control:
    """A heading and its content, on the one surface the screen already is."""
    return ft.Column([panel_title(title), *body], spacing=t.S8, tight=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


def _numbered(items: tuple[tuple[str, str], ...]) -> ft.Control:
    """The steps, numbered, each saying what it is for rather than only what it is called."""
    rows: list[ft.Control] = []
    for number, (title, body) in enumerate(items, 1):
        rows.append(ft.Row([
            ft.Container(ft.Text(str(number), size=t.TYPE_LABEL, weight=ft.FontWeight.W_700,
                    color=t.primary()), width=22, height=22, border_radius=t.R_SM,
                bgcolor=t.primary_soft(), alignment=ft.Alignment.CENTER),
            ft.Column([ft.Text(title, size=t.TYPE_SECONDARY, weight=ft.FontWeight.W_600,
                    color=t.on_surface()), _paragraph(body)],
                spacing=1, tight=True, expand=True)],
            spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.START))
    return ft.Column(rows, spacing=t.S12)


def _definitions(items: tuple[tuple[str, str], ...]) -> ft.Control:
    """Name on the left, what it holds on the right — a table without the ruling."""
    return ft.Column([ft.Row([
            ft.Text(name, size=t.TYPE_LABEL, weight=ft.FontWeight.W_600, color=t.on_surface(),
                    width=150),
            ft.Text(body, size=t.TYPE_LABEL, color=t.on_surface_variant(), expand=True)],
            spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.START)
        for name, body in items], spacing=t.S8)


def _lines(items: tuple[str, ...]) -> ft.Control:
    return ft.Column([ft.Text(line, size=t.TYPE_LABEL, color=t.on_surface_variant())
                      for line in items], spacing=t.S4)


def _privacy() -> ft.Control:
    return ft.Column([ft.Row([ft.Icon(icon, size=16, color=t.primary()),
            ft.Text(text, size=t.TYPE_LABEL, color=t.on_surface_variant(), expand=True)],
            spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.START)
        for icon, text in FACTS], spacing=t.S8)


def reference() -> list[ft.Control]:
    """Everything a person comes back to Home to look up.

    Kept in one function because the first run and Home must not drift apart: a shortcut
    added to one and forgotten in the other is worse than no list at all.
    """
    return [
        _group(s.HOME_WHAT_HEADING, _paragraph(s.HOME_WHAT_BODY)),
        _group(s.HOME_STEPS_HEADING, _numbered(s.HOME_STEPS)),
        _group(s.HOME_MARKING_HEADING, _paragraph(s.HOME_MARKING)),
        _group(s.HOME_REVIEW_HEADING, _paragraph(s.HOME_REVIEW)),
        _group(s.HELP_SHORTCUTS_HEADING, _lines(s.shortcuts(t.SKIP_SECONDS))),
        _group(s.HOME_EXPORTS_HEADING, _definitions(s.HOME_EXPORTS)),
        _group(s.HOME_PROVIDERS_HEADING, _paragraph(s.HOME_PROVIDERS_BODY)),
        _group(s.HOME_LANGUAGE_HEADING, _paragraph(s.HOME_LANGUAGE_BODY)),
        _group(s.HOME_PRIVACY_HEADING, _privacy())]


def home(on_start: Callable[[], None], on_open: Callable[[], None]) -> ft.Control:
    """Home, inside the shell: the identity, the two ways in, and the reference below it."""
    actions = ft.Row([primary_button(s.WELCOME_START, lambda e: on_start(), ft.Icons.ARROW_FORWARD),
        secondary_button(s.HOME_OPEN, lambda e: on_open(), ft.Icons.FOLDER_OPEN)], spacing=t.S12)
    body = ft.Column([hero(), actions, ft.Divider(height=1, color=t.outline()), *reference()],
        spacing=t.S24, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    return ft.Column([page_title(s.HOME_TITLE, s.HOME_SUBTITLE),
        ft.Container(body, padding=t.CARD_PADDING, bgcolor=t.surface(), border_radius=t.RADIUS)],
        spacing=t.S16)


def build(on_start: Callable[[], None], on_help: Callable[[], None]) -> ft.Control:
    """The very first run: no sidebar to come from, so it fills the window itself.

    It stays short on purpose. Someone opening the application for the first time needs the
    three facts about their recording and a way in, not the whole reference — that is what
    Home is for, and the wordmark leads there from every screen afterwards.
    """
    body = ft.Column([
        hero(),
        ft.Container(height=t.S8),
        ft.Text(s.WELCOME_TITLE, size=t.TYPE_DISPLAY, weight=ft.FontWeight.W_600, color=t.on_surface()),
        ft.Text(s.WELCOME_BODY, size=t.TYPE_BODY, color=t.on_surface_variant()),
        ft.Container(height=t.S8),
        card(ft.Column([ft.Row([ft.Icon(icon, size=18, color=t.primary()),
            ft.Text(text, size=t.TYPE_SECONDARY, color=t.on_surface(), expand=True)],
            spacing=t.S12) for icon, text in FACTS], spacing=t.S16)),
        ft.Container(height=t.S8),
        ft.Row([primary_button(s.WELCOME_START, lambda e: on_start(), ft.Icons.ARROW_FORWARD),
            secondary_button(s.WELCOME_HOW, lambda e: on_help())], spacing=t.S12),
        ft.Text(s.OPEN_EXISTING_BODY, size=t.TYPE_LABEL, color=t.muted())],
        spacing=t.S12, horizontal_alignment=ft.CrossAxisAlignment.START)
    return ft.Container(ft.Row([ft.Container(expand=1), ft.Container(body, expand=6), ft.Container(expand=1)],
        alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=t.background(), padding=t.S32, alignment=ft.Alignment.CENTER, expand=True)
