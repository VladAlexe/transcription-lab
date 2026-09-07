"""The Identities panel: one row per detected voice.

A row is a name you can correct and, when diarization split one person across two labels, a
quiet menu that folds one into the other. The menu is a popup — it opens over the panel, so
the panel keeps its width and every other row stays exactly where it was.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
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

        def commit(event,key=speaker,was=current)->None:
            # Enter, or simply clicking away. The tick button that used to sit here repeated
            # Enter and cost 34 pixels on every row of a narrow pane — which is most of the
            # reason the name field had no room to read a name in.
            value=(event.control.value or key).strip() or key
            if value!=was: on_map(key,value)

        field=ft.TextField(value=current,dense=True,text_size=t.TYPE_SECONDARY,
            height=t.FIELD_HEIGHT_DENSE,expand=True,tooltip=s.APPLY_NAME,
            disabled=not enabled,border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
            color=t.on_surface(),content_padding=ft.Padding(t.S12,t.S8,t.S12,t.S8),
            on_submit=commit if enabled else None,
            on_focus=(lambda e:on_typing(True)) if on_typing else None,
            on_blur=(lambda e:(on_typing(False) if on_typing else None,
                               commit(e) if enabled else None)[0]))
        if refs is not None: refs[speaker]=field
        # Merge sits under the name, not beside it. Beside it, a 34px control on every row
        # was the difference between a name field you can read a name in and one you cannot,
        # and folding two speakers together is a once-per-interview act — not something that
        # earns a permanent place next to the thing you actually type in.
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
                *( [merge] if merge is not None else [] )],
                spacing=t.S4,vertical_alignment=ft.CrossAxisAlignment.CENTER)],spacing=t.S4),
            padding=ft.Padding(0,t.S12,0,t.S12),
            border=ft.Border(bottom=ft.BorderSide(t.HAIRLINE,t.outline()))))
    return ft.ListView(rows,spacing=0,expand=True)
