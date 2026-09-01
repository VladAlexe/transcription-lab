"""The transport: a slim footer pinned under the workspace, never a card in the flow."""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import icon_button
from audio_player import AudioPlayer, format_position

SPEEDS = (0.75, 1.0, 1.25, 1.5)


def audio_transport(player: AudioPlayer, refs: dict | None = None,
                    on_speed: Callable[[float], None] | None = None) -> ft.Control:
    """One 56px row: play/pause, elapsed, thin scrubber, total, speed."""
    ready = player.ready
    total = max(player.duration_ms, 0)
    position = min(max(player.position_ms, 0), total or player.position_ms)

    button = icon_button(ft.Icons.PAUSE if player.playing else ft.Icons.PLAY_ARROW,
                         s.PLAYER_PAUSE if player.playing else s.PLAYER_PLAY,
                         lambda e: player.toggle(), size=20,
                         color=t.primary() if ready else t.muted(), disabled=not ready)

    scrubber = ft.Slider(min=0, max=float(total or 1), value=float(position),
                         disabled=not ready or not total, expand=True,
                         active_color=t.primary(), inactive_color=t.outline(),
                         on_change_end=lambda e: None if (refs or {}).get("scrubber_programmatic")
                         else player.scrub(int(float(e.control.value))))
    elapsed = ft.Text(format_position(position), size=t.TYPE_CAPTION, color=t.on_surface_variant(),
                      font_family="Consolas", no_wrap=True)
    duration = ft.Text(format_position(total) if total else "--:--", size=t.TYPE_CAPTION,
                       color=t.muted(), font_family="Consolas", no_wrap=True)
    speed = ft.Dropdown(value=str(getattr(player, "speed", 1.0)), width=88, dense=True,
                        disabled=not ready or on_speed is None,
                        border_color=t.outline(), text_size=t.TYPE_CAPTION,
                        options=[ft.DropdownOption(key=str(rate), text=f"{rate:g}×") for rate in SPEEDS],
                        on_select=lambda e: on_speed(float(e.control.value)) if on_speed else None)
    if refs is not None:
        refs["player_button"] = button
        refs["player_scrubber"] = scrubber
        refs["player_elapsed"] = elapsed
        refs["player_duration"] = duration

    return ft.Container(
        ft.Row([button, elapsed, scrubber, duration, speed],
               spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.PLAYER_BAR_HEIGHT, padding=ft.Padding(t.S16, 0, t.S16, 0),
        bgcolor=t.surface(), border=ft.Border(top=ft.BorderSide(1, t.outline())))


def audio_missing_banner(on_locate: Callable[[], None], on_dismiss: Callable[[], None]) -> ft.Control:
    """Shown when a project loads without a reachable recording. Everything else still works."""
    from components.buttons import secondary_button, tertiary_button
    return ft.Container(
        ft.Row([ft.Icon(ft.Icons.MUSIC_OFF_OUTLINED, size=18, color=t.warning()),
                ft.Column([ft.Text(s.AUDIO_MISSING_TITLE, size=t.TYPE_LABEL, color=t.warning(),
                                   weight=ft.FontWeight.W_600),
                           ft.Text(s.AUDIO_MISSING_BODY, size=t.TYPE_CAPTION, color=t.on_surface_variant())],
                          spacing=2, tight=True, expand=True),
                secondary_button(s.AUDIO_LOCATE, lambda e: on_locate(), ft.Icons.FOLDER_OPEN),
                tertiary_button(s.AUDIO_DISMISS, lambda e: on_dismiss())],
               spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.S16, t.S12, t.S16, t.S12), bgcolor=t.surface_variant(),
        border=ft.Border.all(1, t.outline()), border_radius=t.R_SM)
