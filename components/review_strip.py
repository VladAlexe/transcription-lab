"""How far through the review you are, said once and quietly.

A slim track, a plain count, and the two controls that follow from them: hide what is
already done, and go back to where you stopped. It reads as status, not as an alert — the
screen's one sage accent still belongs to Continue to export, so the only sage here is the
few pixels of filled track.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import tertiary_button
from review_progress import Progress

TRACK_HEIGHT = 4
TRACK_MIN = 120


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
    track = ft.ProgressBar(value=progress.fraction, bar_height=TRACK_HEIGHT,
                           color=t.primary(), bgcolor=t.outline(),
                           border_radius=t.R_PILL, expand=True)
    count = ft.Text(label_for(progress), size=t.TYPE_LABEL, color=t.on_surface_variant(),
                    no_wrap=True)
    if refs is not None:
        refs["progress_track"] = track
        refs["progress_label"] = count

    filter_box = ft.Checkbox(s.ONLY_UNCHECKED, value=only_unchecked,
                             tooltip=s.ONLY_UNCHECKED_TOOLTIP,
                             active_color=t.primary(), check_color=t.on_primary(),
                             label_style=ft.TextStyle(size=t.TYPE_LABEL,
                                                      color=t.on_surface_variant()),
                             on_change=(lambda e: on_filter()) if on_filter else None,
                             disabled=on_filter is None)

    row: list[ft.Control] = [ft.Container(track, expand=True, padding=ft.Padding(0, 0, t.S8, 0)),
                             count, filter_box]
    if on_resume is not None:
        row.append(tertiary_button(s.RESUME, lambda e: on_resume(), ft.Icons.HISTORY))
        row[-1].tooltip = s.RESUME_TOOLTIP.format(stamp=resume_stamp or "—")
    return ft.Container(ft.Row(row, spacing=t.S12,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.Padding(0, t.S4, 0, t.S4))
