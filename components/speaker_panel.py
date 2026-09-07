"""The Identities panel: one row per detected voice.

A row is a name you can correct and, when diarization split one person across two labels, a
quiet menu that folds one into the other. The menu is a popup — it opens over the panel, so
the panel keeps its width and every other row stays exactly where it was.
"""
from __future__ import annotations
from types import SimpleNamespace
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.inputs import syncing
from components.buttons import icon_button
from document_export import format_timestamp


def _merge_menu(speaker:str,others:list[str],mapping:dict[str,str],
                on_merge:Callable[[str,str],None])->ft.Control:
    """"Merge into…" for this row. Disabled, not hidden, when there is nothing to merge into:
    a control that appears and disappears between rows makes the panel feel unstable."""
    items=[ft.PopupMenuItem(content=ft.Text(s.MERGE_MENU_ITEM.format(speaker=mapping.get(other,other)),
            size=t.TYPE_SECONDARY,color=t.on_surface()),
            on_click=lambda e,target=other:on_merge(speaker,target)) for other in others]
    return ft.PopupMenuButton(items=items,icon=ft.Icons.CALL_MERGE,
        tooltip=s.MERGE_INTO if others else s.MERGE_UNAVAILABLE,
        icon_color=t.on_surface_variant(),icon_size=18,
        disabled=not others,bgcolor=t.surface_raised(),
        width=t.ICON_BUTTON,height=t.ICON_BUTTON,padding=0,
        shape=ft.RoundedRectangleBorder(radius=t.R_MD),
        menu_padding=ft.Padding(0,t.S4,0,t.S4))


def speaker_panel(stats:dict[str,tuple[int,float]],mapping:dict[str,str],speaker_index:dict[str,int],
                  on_map:Callable[[str,str],None],enabled:bool=True,refs:dict|None=None,
                  on_typing:Callable[[bool],None]|None=None,
                  on_merge:Callable[[str,str],None]|None=None)->ft.Control:
    rows:list[ft.Control]=[]
    speakers=list(stats)
    for speaker,(count,duration) in stats.items():
        color=t.speaker_color(speaker_index.get(speaker,0))
        current=mapping.get(speaker,speaker)

        def commit(event,key=speaker)->None:
            """Apply the typed name. Enter, the tick, or simply clicking away."""
            value=(event.control.value or key).strip() or key
            if value!=mapping.get(key,key): on_map(key,value)

        # Every handler binds `commit` as a default argument, and this is not tidiness.
        # A lambda that names `commit` looks it up in this function's scope when it fires —
        # which, by then, is the LAST row's commit. Clicking away from the first speaker
        # therefore renamed the last one, with the first speaker's text. That is how two
        # speakers ended up with the same name, and why Enter appeared to work while
        # clicking away did not: `on_submit=commit` binds the object, a lambda does not.
        #
        # `syncing` is the other half. Flet only sends a control's new value to Python when
        # the control has a change listener, so without it `.value` here stays at the name
        # the row was built with however much is typed into it.
        field=syncing(ft.TextField(value=current,dense=True,text_size=t.TYPE_SECONDARY,
            height=t.FIELD_HEIGHT_DENSE,expand=True,tooltip=s.APPLY_NAME,
            disabled=not enabled,border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
            color=t.on_surface(),content_padding=ft.Padding(t.S12,t.S8,t.S12,t.S8),
            on_submit=commit if enabled else None,
            on_focus=(lambda e:on_typing(True)) if on_typing else None,
            on_blur=(lambda e,apply=commit:(on_typing(False) if on_typing else None,
                                            apply(e) if enabled else None)[0])))
        if refs is not None: refs[speaker]=field
        # Both actions sit on the line below the name, not beside it. Beside it, two 34px
        # controls on every row were the difference between a name field you can read a name
        # in and one you cannot. But a field with no visible way to apply it reads as a field
        # that does nothing, so the tick is here rather than gone: the name keeps its width
        # and the action keeps its button.
        tick = icon_button(ft.Icons.CHECK, s.APPLY_NAME,
                           (lambda e, run=commit, box=field:
                            run(SimpleNamespace(control=box))) if enabled else None,
                           size=16, disabled=not enabled)
        merge=(_merge_menu(speaker,[other for other in speakers if other!=speaker],
                           mapping,on_merge) if on_merge is not None else None)
        # Two lines, not three: the dot joins the name row, and the raw label joins the
        # counts underneath it. Same information, a third less panel to scroll through.
        rows.append(ft.Container(ft.Column([
            ft.Row([ft.Container(width=9,height=9,bgcolor=color,border_radius=t.R_PILL),field],
                spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([ft.Text(s.IDENTITY_META.format(speaker=speaker,count=count,
                    duration=format_timestamp(duration)),size=t.TYPE_CAPTION,color=t.muted(),
                    max_lines=1,overflow=ft.TextOverflow.ELLIPSIS,expand=True),
                tick,
                *( [merge] if merge is not None else [] )],
                spacing=t.S4,vertical_alignment=ft.CrossAxisAlignment.CENTER)],spacing=t.S4),
            padding=ft.Padding(0,t.S12,0,t.S12),
            border=ft.Border(bottom=ft.BorderSide(t.HAIRLINE,t.outline()))))
    return ft.ListView(rows,spacing=0,expand=True)
