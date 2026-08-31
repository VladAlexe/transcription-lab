from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState

DESTINATIONS=(("Fișier",ft.Icons.AUDIO_FILE_OUTLINED),("Transcriere",ft.Icons.GRAPHIC_EQ),
              ("Vorbitori",ft.Icons.PEOPLE_OUTLINE),("Export",ft.Icons.IOS_SHARE_OUTLINED))


def navigation_rail(state:AppState,collapsed:bool,on_navigate:Callable[[int],None],on_new:Callable[[],None],on_save:Callable[[],None],on_open:Callable[[],None])->ft.Control:
    items=[]
    for index,(label,icon) in enumerate(DESTINATIONS):
        available=index==0 or index==1 and state.selected_file_metadata is not None or index>=2 and bool(state.transcript_segments)
        complete=(index==0 and state.selected_file_metadata is not None) or (index==1 and bool(state.transcript_segments)) or (index==2 and state.current_workflow_step>2)
        selected=state.current_workflow_step==index
        marker=ft.Container(width=3,height=30,bgcolor=t.ACCENT if selected else ft.Colors.TRANSPARENT,border_radius=2)
        status=ft.Icon(ft.Icons.CHECK_CIRCLE,size=12,color=t.SUCCESS) if complete else ft.Container(width=12)
        body=ft.Row([marker,ft.Icon(icon,size=20,color=t.ACCENT if selected else t.secondary_color()),
            ft.Text(label,size=t.TYPE_SECONDARY,weight=ft.FontWeight.W_600 if selected else ft.FontWeight.NORMAL,visible=not collapsed),
            ft.Container(expand=True,visible=not collapsed),status],spacing=t.S8)
        items.append(ft.Container(body,height=44,padding=ft.Padding(6,0,10,0),bgcolor=ft.Colors.with_opacity(.08,t.ACCENT) if selected else None,
            border_radius=t.R_CONTROL,opacity=1 if available else .42,tooltip=label if available else f"Finalizează pasul anterior pentru {label}",
            on_click=(lambda e,i=index:on_navigate(i)) if available else None))
    return ft.Container(ft.Column([ft.Row([ft.Container(ft.Icon(ft.Icons.MIC_NONE,size=22,color=ft.Colors.ON_PRIMARY),width=36,height=36,
        bgcolor=t.ACCENT,border_radius=9,alignment=ft.Alignment.CENTER),ft.Text("Transcriere",size=t.TYPE_APP,weight=ft.FontWeight.W_600,visible=not collapsed)],spacing=t.S8),
        ft.Container(height=t.S16),*items,ft.Container(expand=True),
        ft.IconButton(ft.Icons.FOLDER_OPEN,tooltip="Deschide proiect",on_click=lambda e:on_open()),
        ft.IconButton(ft.Icons.SAVE_OUTLINED,tooltip="Salvează proiect",disabled=not bool(state.transcript_segments),on_click=lambda e:on_save()),
        ft.IconButton(ft.Icons.ADD,tooltip="Proiect nou",on_click=lambda e:on_new())],horizontal_alignment=ft.CrossAxisAlignment.CENTER if collapsed else ft.CrossAxisAlignment.START),
        width=t.NAV_COLLAPSED if collapsed else t.NAV_EXPANDED,padding=t.S12,bgcolor=t.surface_alt_color(),border=ft.Border(right=ft.BorderSide(1,t.border_color())))

