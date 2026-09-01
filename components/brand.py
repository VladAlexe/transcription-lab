"""The application wordmark: the one place the waveform mark is shown at full weight.

Everywhere else the mark is either absent or deliberately secondary, so the sidebar
identity stays distinct instead of competing with functional icons.
"""
from __future__ import annotations
import flet as ft
import design_tokens as t
import strings as s

MARK_SIZE = 26
HERO_SIZE = 48
# The logo itself, served from the assets directory, so the sidebar, the window icon and the
# taskbar all show one artwork instead of three approximations of it.
MARK_ASSET = "icon.png"


def mark(size: int = MARK_SIZE) -> ft.Control:
    """The application logo at the requested size.

    `error_content` keeps the sidebar intact if the asset cannot be resolved: a small sage
    tile stands in rather than leaving a hole where the identity should be.
    """
    fallback = ft.Container(width=size, height=size, bgcolor=t.primary(),
                            border_radius=size * .3)
    return ft.Image(src=MARK_ASSET, width=size, height=size, fit=ft.BoxFit.CONTAIN,
                    error_content=fallback)


def wordmark(minimised:bool=False)->ft.Control:
    """The identity block, sitting in a band the exact height of the title bar beside it.

    That is the whole idea: the sidebar hairline and the top bar hairline become one line
    across the application instead of two that nearly agree. The name is set a size up and
    a weight heavier than the navigation under it, so the identity reads first and the
    destinations read as a list — with the mark small enough that the name never truncates.

    The rail's minimise control deliberately lives in the footer, not here: a button in this
    row would take ~40px away from the name and cut it off.
    """
    row:list[ft.Control]=[mark()]
    if not minimised:
        # Two words, with the space the name is meant to have. The window title and the
        # taskbar keep the one-word form; this is the piece a person reads.
        row.append(ft.Text(s.BRAND_WORDMARK,size=t.TYPE_HEADING,weight=ft.FontWeight.W_700,
            color=t.on_surface(),max_lines=1,no_wrap=True,expand=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            style=ft.TextStyle(letter_spacing=-.1,height=1.0)))
    content=ft.Row(row,spacing=t.WORDMARK_GAP,vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER if minimised else ft.MainAxisAlignment.START)
    side=t.S8 if minimised else t.WORDMARK_LEFT
    # Mark and name share one baseline (the row centres them), with the sidebar's own top
    # padding above rather than a band borrowed from the title bar.
    return ft.Container(content,padding=ft.Padding(side,t.WORDMARK_TOP,side,t.S16),
        alignment=ft.Alignment.CENTER_LEFT,
        border=ft.Border(bottom=ft.BorderSide(t.HAIRLINE,t.outline())))


def hero()->ft.Control:
    """The welcome screen's identity block: the same mark, one size up, with the tagline."""
    return ft.Row([mark(HERO_SIZE),
        ft.Column([ft.Text(s.APP_NAME,size=t.TYPE_TITLE,weight=ft.FontWeight.W_600,color=t.on_surface()),
            ft.Text(s.APP_TAGLINE,size=t.TYPE_SECONDARY,color=t.on_surface_variant())],
            spacing=2,tight=True)],spacing=t.S16,vertical_alignment=ft.CrossAxisAlignment.CENTER)
