"""The application wordmark: the one place the waveform mark is shown at full weight.

Everywhere else the mark is either absent or deliberately secondary, so the sidebar
identity stays distinct instead of competing with functional icons.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s

# The square crop of the master, served from the assets directory, so the sidebar, the
# window icon and the taskbar all show one artwork instead of three approximations of it.
# The master itself is a wide render; `tools_make_icon.py` derives this and every other size
# from it, which is why nothing here ever points at icon.png directly.
MARK_ASSET = "icon_mark.png"


def mark(size: int = 0) -> ft.Control:
    """The application logo at the requested size, on a ground of its own.

    The artwork carries its own ground, so the tile only rounds and clips it. An earlier
    logo was ink on nothing and needed a light tile put behind it or it vanished into the
    dark sidebar; this one arrives as a picture and fills the frame.

    `error_content` keeps the sidebar intact if the asset cannot be resolved: a small tile
    in the accent stands in rather than leaving a hole where the identity should be.
    """
    side = size or t.MARK_SIZE
    fallback = ft.Container(width=side, height=side, bgcolor=t.primary())
    # The mark fills its tile edge to edge. The artwork carries its own dark ground now, so
    # a light tile behind it would only put a pale ring around a picture that already ends
    # where it means to — the corners are rounded and clipped instead.
    art = ft.Image(src=MARK_ASSET, width=side, height=side, fit=ft.BoxFit.COVER,
                   error_content=fallback)
    return ft.Container(art, width=side, height=side, bgcolor=t.surface_variant(),
                        border_radius=max(t.RADIUS, round(side * .22)),
                        border=ft.Border.all(t.HAIRLINE, t.mark_edge()),
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        alignment=ft.Alignment.CENTER)


def wordmark(minimised: bool = False, on_home: Callable[[], None] | None = None) -> ft.Control:
    """The identity block, and the way back to Home.

    The sidebar hairline and the top bar hairline become one line across the application
    instead of two that nearly agree. The name is set a size up and a weight heavier than
    the navigation under it, so the identity reads first and the destinations read as a
    list. The name is allowed a second line rather than an ellipsis, which is what lets the
    mark be the size of an app icon without the risk of "Transcription La…".

    The rail's minimise control deliberately lives in the footer, not here: a button in this
    row would take ~40px away from the name and cut it off.
    """
    row: list[ft.Control] = [mark()]
    if not minimised:
        # Two words, with the space the name is meant to have. The window title and the
        # taskbar keep the one-word form; this is the piece a person reads.
        row.append(ft.Text(s.BRAND_WORDMARK, size=t.TYPE_HEADING, weight=ft.FontWeight.W_700,
            color=t.on_surface(), max_lines=2, expand=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            style=ft.TextStyle(letter_spacing=-.1, height=1.05)))
    content = ft.Row(row, spacing=t.WORDMARK_GAP, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER if minimised else ft.MainAxisAlignment.START)
    # Four pixels either side when minimised, not eight: the rail is 56 and the mark is 44,
    # so eight would have pushed the logo wider than the rail that holds it.
    side = t.S4 if minimised else t.WORDMARK_LEFT
    # Mark and name share one baseline (the row centres them), with the sidebar's own top
    # padding above rather than a band borrowed from the title bar.
    return ft.Container(content, padding=ft.Padding(side, t.WORDMARK_TOP, side, t.S16),
        alignment=ft.Alignment.CENTER_LEFT, ink=on_home is not None,
        ink_color=t.primary_soft(),
        tooltip=s.NAV_HOME_TOOLTIP if on_home else None,
        on_click=(lambda e: on_home()) if on_home else None)


def hero() -> ft.Control:
    """Home's identity block: the same mark, at the size the screen can afford."""
    return ft.Row([mark(t.MARK_HERO),
        ft.Column([ft.Text(s.APP_NAME, size=t.TYPE_DISPLAY, weight=ft.FontWeight.W_700,
                color=t.on_surface(), style=ft.TextStyle(letter_spacing=-.3)),
            ft.Text(s.APP_TAGLINE, size=t.TYPE_BODY, color=t.on_surface_variant())],
            spacing=2, tight=True, expand=True)],
        spacing=t.S16, vertical_alignment=ft.CrossAxisAlignment.CENTER)
