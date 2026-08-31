from __future__ import annotations
from typing import Callable
import flet as ft
from app_state import AppState
from theme import ACCENT,MUTED,SIDEBAR_WIDTH


def sidebar(state:AppState,on_navigate:Callable[[int],None],on_settings:Callable[[],None],on_new:Callable[[],None],
            on_save:Callable[[],None],on_open:Callable[[],None])->ft.Control:
    labels=["Înregistrare","Transcriere","Vorbitori","Export"]
    items=[]
    for i,label in enumerate(labels):
        available=(i==0 or i==1 and state.selected_file_metadata is not None or i>=2 and bool(state.transcript_segments))
        complete=(i==0 and state.selected_file_metadata is not None) or (i==1 and bool(state.transcript_segments)) or (i==2 and state.current_workflow_step>2)
        selected=state.current_workflow_step==i
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE if complete else ft.Icons.RADIO_BUTTON_CHECKED if selected else ft.Icons.RADIO_BUTTON_UNCHECKED
        items.append(ft.Container(ft.Row([ft.Icon(icon,size=18,color=ACCENT if selected or complete else MUTED),ft.Text(f"{i+1}. {label}",size=13,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.NORMAL)],spacing=10),padding=ft.Padding(12,10,10,10),
            bgcolor=ft.Colors.with_opacity(.10,ACCENT) if selected else None,border_radius=8,
            on_click=(lambda e,index=i:on_navigate(index)) if available else None,opacity=1 if available else .45))
    return ft.Container(ft.Column([ft.Column([ft.Text("Transcriere",size=20,weight=ft.FontWeight.W_600),ft.Text("Interviuri de grup",size=12,color=MUTED)],spacing=1),
        ft.Divider(),*items,ft.Container(expand=True),ft.TextButton("Deschide proiect",icon=ft.Icons.FOLDER_OPEN,on_click=lambda e:on_open()),
        ft.TextButton("Salvează proiect",icon=ft.Icons.SAVE_OUTLINED,on_click=lambda e:on_save(),disabled=not bool(state.transcript_segments)),
        ft.TextButton("Proiect nou",icon=ft.Icons.ADD,on_click=lambda e:on_new()),
        ft.TextButton("Setări",icon=ft.Icons.SETTINGS_OUTLINED,on_click=lambda e:on_settings())],spacing=6),
        width=SIDEBAR_WIDTH,padding=18,bgcolor=t.surface_color(),border=ft.Border(right=ft.BorderSide(1,t.border_color())))

