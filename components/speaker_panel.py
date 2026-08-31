from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from document_export import format_timestamp


def speaker_panel(stats:dict[str,tuple[int,float]],mapping:dict[str,str],on_map:Callable[[str,str],None])->ft.Control:
    rows=[]
    for index,(speaker,(count,duration)) in enumerate(stats.items()):
        field=ft.TextField(value=mapping.get(speaker,speaker),dense=True,text_size=t.TYPE_BODY,height=38,expand=True)
        rows.append(ft.Container(ft.Column([ft.Row([ft.Container(width=8,height=8,bgcolor=t.SPEAKER_COLORS[index%len(t.SPEAKER_COLORS)],border_radius=4),
            ft.Text(speaker,size=t.TYPE_LABEL,color=t.secondary_color(),expand=True)]),
            ft.Row([field,ft.IconButton(ft.Icons.CHECK,tooltip="Aplică numele",on_click=lambda e,s=speaker,f=field:on_map(s,f.value or s),icon_size=18)]),
            ft.Text(f"{count} intervenții · {format_timestamp(duration)}",size=t.TYPE_LABEL,color=t.secondary_color())],spacing=t.S4),
            padding=ft.Padding(0,t.S8,0,t.S8),border=ft.Border(bottom=ft.BorderSide(1,t.border_color()))))
    return ft.ListView(rows,spacing=0,expand=True)

