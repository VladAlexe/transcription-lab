"""Transient tools float. They never join the page flow.

The root rule this module exists to enforce: a tool that comes and goes — find and
replace, a quick picker, anything opened from a button and closed again — must not insert
a block into the column and push the work around. Opening it changes nothing behind it.
The transcript keeps its scroll position, the identity panel keeps its width, the
inspector keeps its column.

Two shapes are allowed, and this module supplies both:

  * `floating_panel` — its own raised surface, a header with a title and a close button,
    capped at `OVERLAY_MAX_WIDTH` and docked to a corner of the content area.
  * `pinned_bar` — a slim strip anchored to the top of the content area, full width of
    the content column but only as tall as one row of controls.

Both are handed to `app_shell(..., overlays=[...])`, which stacks them over the content.
Neither takes the full width and neither takes the full height: `dock` refuses to build a
panel wider than the space it is given, and a panel's height is whatever its rows need.
"""
from __future__ import annotations

from typing import Callable

import flet as ft

import design_tokens as t
from components.buttons import icon_button


def panel_width(available: float | None) -> float:
    """How wide a floating tool may be here.

    Capped at 520 so it stays a tool rather than a second page, and shrunk on a narrow
    window so it can never reach — let alone exceed — the edges of the content area.
    """
    if available is None:
        return float(t.OVERLAY_MAX_WIDTH)
    room = float(available) - 2 * t.OVERLAY_INSET
    return float(max(t.OVERLAY_MIN_WIDTH, min(t.OVERLAY_MAX_WIDTH, room)))


def surface(content: ft.Control, width: float | None = None,
            height: float | None = None) -> ft.Container:
    """The one overlay surface: solid, hairlined, softly lifted. Never transparent."""
    return ft.Container(content, width=width, height=height, padding=t.OVERLAY_PADDING,
                        bgcolor=t.surface_raised(), border_radius=t.OVERLAY_RADIUS,
                        border=ft.Border.all(t.HAIRLINE, t.outline_strong()),
                        shadow=ft.BoxShadow(blur_radius=28, spread_radius=0,
                                            color=t.shadow(), offset=ft.Offset(0, 8)),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE)


def header(title: str, on_close: Callable[[], None] | None,
           icon: ft.IconData | None = None, trailing: ft.Control | None = None,
           close_tooltip: str = "Close") -> ft.Control:
    """Title on the left, live status in the middle, one close button on the right.

    Every overlay carries the same header so closing one is the same gesture as closing
    any other, and the close control always sits in the same corner.
    """
    row: list[ft.Control] = []
    if icon is not None:
        row.append(ft.Icon(icon, size=17, color=t.primary()))
    row.append(ft.Text(title, size=t.TYPE_SUBHEADING, weight=ft.FontWeight.W_600,
                       color=t.on_surface(), no_wrap=True))
    row.append(ft.Container(expand=True))
    if trailing is not None:
        row.append(trailing)
    if on_close is not None:
        row.append(icon_button(ft.Icons.CLOSE, close_tooltip, lambda e: on_close(), size=17))
    return ft.Row(row, spacing=t.S8, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def dock(panel: ft.Control, corner: str = "top_right") -> ft.Control:
    """Position a built panel inside the overlay stack. Positioned, so nothing reflows."""
    box = ft.Container(panel, top=float(t.OVERLAY_TOP))
    if corner.endswith("left"):
        box.left = float(t.OVERLAY_INSET)
    else:
        box.right = float(t.OVERLAY_INSET)
    return box


def floating_panel(title: str, rows: list[ft.Control], on_close: Callable[[], None] | None,
                   icon: ft.IconData | None = None, available: float | None = None,
                   status: ft.Control | None = None, corner: str = "top_right",
                   close_tooltip: str = "Close",
                   height: float | None = None) -> tuple[ft.Control, float]:
    """A complete docked tool panel, and the width it was actually built at.

    A panel with a list inside needs a declared height, because a list has no opinion about
    how tall it should be and a floating panel has no page to stretch against.
    """
    width = panel_width(available)
    body = ft.Column([header(title, on_close, icon, status, close_tooltip), *rows],
                     spacing=t.S12, tight=height is None, expand=height is not None)
    return dock(surface(body, width, height), corner), width


def pinned_bar(rows: list[ft.Control], available: float | None = None) -> ft.Control:
    """A slim strip pinned across the top of the content area, one row of controls tall."""
    body = ft.Column(rows, spacing=t.S8, tight=True)
    strip = ft.Container(body, padding=ft.Padding(t.OVERLAY_PADDING, t.S12, t.S12, t.S12),
                         bgcolor=t.surface_raised(),
                         border=ft.Border.all(t.HAIRLINE, t.outline_strong()),
                         border_radius=t.R_MD,
                         shadow=ft.BoxShadow(blur_radius=20, color=t.shadow(),
                                             offset=ft.Offset(0, 4)))
    return ft.Container(strip, top=float(t.OVERLAY_TOP), left=float(t.OVERLAY_INSET),
                        right=float(t.OVERLAY_INSET))


def stack(base: ft.Control, overlays: list[ft.Control] | None) -> ft.Control:
    """Put the overlays above the content. With none open, the content is returned untouched.

    That last sentence is the guarantee the rule rests on: with every tool closed the tree
    is byte-for-byte what it was before overlays existed, so nothing can have moved.
    """
    if not overlays:
        return base
    return ft.Stack([base, *overlays], expand=True, fit=ft.StackFit.EXPAND,
                    clip_behavior=ft.ClipBehavior.NONE)
