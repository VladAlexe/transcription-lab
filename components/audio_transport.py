"""The transport: a slim footer pinned under the workspace, never a card in the flow."""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import icon_button
from audio_player import AudioPlayer, format_position

# The range a transcriptionist actually uses: half speed to pick a word out of a mumble,
# double to skim a passage that needs no checking.
SPEEDS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


def audio_transport(player: AudioPlayer, refs: dict | None = None,
                    on_speed: Callable[[float], None] | None = None,
                    on_skip: Callable[[float], None] | None = None,
                    on_follow: Callable[[], None] | None = None,
                    following: bool = False) -> ft.Control:
    """One 56px row: back, play/pause, forward, elapsed, thin scrubber, total, speed.

    The two skip buttons sit either side of play/pause, which is where a hand already
    expects them, and they are the same jump the left and right arrow keys make.
    """
    ready = player.ready
    total = max(player.duration_ms, 0)
    position = min(max(player.position_ms, 0), total or player.position_ms)

    button = icon_button(ft.Icons.PAUSE if player.playing else ft.Icons.PLAY_ARROW,
                         s.PLAYER_PAUSE if player.playing else s.PLAYER_PLAY,
                         lambda e: player.toggle(), size=20,
                         color=t.primary() if ready else t.muted(), disabled=not ready)

    def jump(delta: float, icon: ft.IconData, tooltip: str) -> ft.Control:
        return icon_button(icon, tooltip,
                           (lambda e: on_skip(delta)) if on_skip else None,
                           size=20, color=t.on_surface_variant(),
                           disabled=not ready or on_skip is None)

    back = jump(-float(t.SKIP_SECONDS), ft.Icons.REPLAY_5,
                s.PLAYER_BACK.format(seconds=t.SKIP_SECONDS))
    forward = jump(float(t.SKIP_SECONDS), ft.Icons.FORWARD_5,
                   s.PLAYER_FORWARD.format(seconds=t.SKIP_SECONDS))

    follow = icon_button(ft.Icons.MY_LOCATION if following else ft.Icons.LOCATION_SEARCHING,
                         s.FOLLOW_ON if following else s.FOLLOW_OFF,
                         (lambda e: on_follow()) if on_follow else None, size=18,
                         color=t.primary() if following else t.on_surface_variant(),
                         disabled=on_follow is None)

    scrubber = ft.Slider(min=0, max=float(total or 1), value=float(position),
                         disabled=not ready or not total, expand=True,
                         active_color=t.primary(), inactive_color=t.outline(),
                         on_change_end=lambda e: None if (refs or {}).get("scrubber_programmatic")
                         else player.scrub(int(float(e.control.value))))
    # A fixed-width face for both readings. In a proportional one the digits change width as
    # they change value, so the clock jitters sideways for the whole length of a two-hour
    # recording — and the scrubber between them moves with it.
    elapsed = ft.Text(format_position(position), size=t.TYPE_CAPTION, font_family=t.MONO,
                      color=t.on_surface_variant(), no_wrap=True)
    duration = ft.Text(format_position(total) if total else "--:--", size=t.TYPE_CAPTION,
                       font_family=t.MONO, color=t.muted(), no_wrap=True)
    speed = ft.Dropdown(value=str(getattr(player, "speed", 1.0)), width=88, dense=True,
                        disabled=not ready or on_speed is None,
                        border_color=t.outline(), text_size=t.TYPE_CAPTION,
                        options=[ft.DropdownOption(key=str(rate), text=f"{rate:g}×") for rate in SPEEDS],
                        on_select=lambda e: on_speed(float(e.control.value)) if on_speed else None)
    if refs is not None:
        refs["player_follow"] = follow
        refs["player_back"] = back
        refs["player_forward"] = forward
        refs["player_button"] = button
        refs["player_scrubber"] = scrubber
        refs["player_elapsed"] = elapsed
        refs["player_duration"] = duration

    return ft.Container(
        ft.Row([back, button, forward, elapsed, scrubber, duration, follow, speed],
               spacing=t.S8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.PLAYER_BAR_HEIGHT, padding=ft.Padding(t.S16, 0, t.S16, 0),
        bgcolor=t.chrome(),
        # A hairline where the transport meets the transcript, matching the seams the rail
        # and the title bar now carry. An editor rules its panel edges; tone alone left them
        # soft enough that the bar looked like part of the list it sits under.
        border=ft.Border(top=ft.BorderSide(t.HAIRLINE,t.outline())))


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
