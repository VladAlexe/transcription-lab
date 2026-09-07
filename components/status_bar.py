"""The band along the bottom of the window: what is loaded, and where it is going.

Everything here is already true somewhere else on screen — the provider is in Settings, the
count is above the transcript, the saved state is in the title bar. The point of the band is
that it is true in ALL of those places at once, in a fixed spot, so none of them has to be
gone looking for. It answers nothing and does nothing; it is the one strip that is never a
control, which is what makes it readable at a glance.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from providers import provider_info

STEP_NAMES = (s.NAV_RECORDING, s.NAV_TRANSCRIPTION, s.NAV_SPEAKERS, s.NAV_EXPORT)


def _item(text: str, colour: str | None = None, icon: ft.IconData | None = None,
          mono: bool = False, tooltip: str = "",
          on_click: Callable[[], None] | None = None) -> ft.Control:
    """One reading in the band, with the same hit area whether or not it does anything."""
    row: list[ft.Control] = []
    if icon is not None: row.append(ft.Icon(icon, size=13, color=colour or t.on_surface_variant()))
    row.append(ft.Text(text, size=t.TYPE_CAPTION, color=colour or t.on_surface_variant(),
                       font_family=t.MONO if mono else None, no_wrap=True))
    return ft.Container(ft.Row(row, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.S8, 0, t.S8, 0), height=t.STATUS_BAR_HEIGHT,
        alignment=ft.Alignment.CENTER, tooltip=tooltip or None,
        ink=on_click is not None, ink_color=t.primary_soft(),
        on_click=(lambda e: on_click()) if on_click else None)


def status_bar(state: AppState, screen: str, checked: int = 0,
               on_settings: Callable[[], None] | None = None,
               on_home: Callable[[], None] | None = None) -> ft.Control:
    """The band, assembled left to right in the order a question tends to be asked."""
    provider = provider_info(state.settings.provider)
    turns = len(state.transcript_segments)

    # The left end names where you are, the way an editor marks its context. Amber Earth
    # rather than the accent: it is the one warm mark in the chrome, it echoes the logo, and
    # it is the only place in the band that is meant to be found without being looked for.
    label = {"home": s.HOME_TITLE, "settings": s.SETTINGS_TITLE}.get(
        screen, STEP_NAMES[min(state.current_workflow_step, len(STEP_NAMES) - 1)])
    here = ft.Container(ft.Row([ft.Icon(ft.Icons.HOME_OUTLINED, size=13, color=t.on_accent_warm()),
            ft.Text(label, size=t.TYPE_CAPTION, color=t.on_accent_warm(), no_wrap=True,
                    weight=ft.FontWeight.W_600)],
            spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.S12, 0, t.S12, 0), height=t.STATUS_BAR_HEIGHT,
        bgcolor=t.accent_warm(), alignment=ft.Alignment.CENTER,
        ink=on_home is not None, ink_color=t.primary_soft(),
        tooltip=s.NAV_HOME_TOOLTIP if on_home else None,
        on_click=(lambda e: on_home()) if on_home else None)

    left: list[ft.Control] = [here]
    if state.selected_file_metadata:
        left.append(_item(state.selected_file_metadata.filename, icon=ft.Icons.AUDIO_FILE_OUTLINED,
                          tooltip=state.selected_file_metadata.path))
    if turns:
        left.append(_item(s.STATUS_TURNS.format(done=checked, total=turns), mono=True,
                          icon=ft.Icons.CHECKLIST, tooltip=s.STATUS_TURNS_TOOLTIP))

    right: list[ft.Control] = [
        _item(provider.label.split(" · ")[0], icon=ft.Icons.CLOUD_OUTLINED,
              tooltip=provider.transfer_note, on_click=on_settings),
        _item(s.language_name(state.settings.language), icon=ft.Icons.TRANSLATE,
              tooltip=s.STATUS_LANGUAGE_TOOLTIP, on_click=on_settings),
        _item(s.API_CONFIGURED if state.active_api_key else s.API_MISSING,
              colour=None if state.active_api_key else t.warning(),
              icon=ft.Icons.KEY_OUTLINED, on_click=on_settings,
              tooltip=s.API_CONFIGURED_TOOLTIP if state.active_api_key else s.API_MISSING_TOOLTIP),
        _item(s.UNSAVED if state.dirty else s.SAVED,
              colour=t.warning() if state.dirty else t.success(),
              icon=ft.Icons.CIRCLE if state.dirty else ft.Icons.CHECK)]

    return ft.Container(ft.Row([*left, ft.Container(expand=True), *right], spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.STATUS_BAR_HEIGHT, bgcolor=t.chrome(),
        border=ft.Border(top=ft.BorderSide(t.HAIRLINE, t.outline())))
