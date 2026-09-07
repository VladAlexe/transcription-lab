"""How far through the review you are, small enough to live in the toolbar.

It used to be a full-width row with a four-pixel track. At thirteen per cent that is a
twenty-four-pixel smudge of muted sage: rendered, and invisible. A number you can read and
a ring you can see at a glance say the same thing in a tenth of the space, which is why
this now fits on the one toolbar line instead of owning a band of its own.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import icon_button
from review_progress import Progress

RING = 26
STROKE = 3


def label_for(progress: Progress) -> str:
    if not progress.total or not progress.checked:
        return s.PROGRESS_NONE
    if progress.complete:
        return s.PROGRESS_COMPLETE.format(total=progress.total)
    return s.PROGRESS_LABEL.format(checked=progress.checked, total=progress.total,
                                   percent=progress.percent)


def review_strip(progress: Progress, only_unchecked: bool,
                 on_filter: Callable[[], None] | None = None,
                 on_resume: Callable[[], None] | None = None,
                 resume_stamp: str = "", refs: dict | None = None) -> ft.Control:
    # A ring reads at a glance at 26px; a 4px bar does not read at any width.
    ring = ft.ProgressRing(value=progress.fraction, width=RING, height=RING,
                           stroke_width=STROKE, color=t.primary(), bgcolor=t.outline())
    count = ft.Text(label_for(progress), size=t.TYPE_META, color=t.on_surface_variant(),
                    no_wrap=True)
    if refs is not None:
        refs["progress_track"] = ring
        refs["progress_label"] = count

    row: list[ft.Control] = [ring, count]
    if on_filter is not None:
        row.append(icon_button(ft.Icons.FILTER_ALT if only_unchecked else ft.Icons.FILTER_ALT_OFF,
                               s.ONLY_UNCHECKED_TOOLTIP, lambda e: on_filter(), size=17,
                               color=t.primary() if only_unchecked else t.muted()))
    if on_resume is not None:
        resume = icon_button(ft.Icons.HISTORY, s.RESUME_TOOLTIP.format(stamp=resume_stamp or "—"),
                             lambda e: on_resume(), size=17)
        row.append(resume)
    return ft.Container(ft.Row(row, spacing=t.S8,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.Padding(t.S12, t.S4, t.S12, t.S4),
                        bgcolor=t.surface_variant(), border_radius=t.R_PILL)
