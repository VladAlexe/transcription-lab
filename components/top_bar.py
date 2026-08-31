from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState


def top_bar(state:AppState,on_settings:Callable[[],None],on_theme:Callable[[],None],on_help:Callable[[],None])->ft.Control:
    filename=state.selected_file_metadata.filename if state.selected_file_metadata else "Proiect fără titlu"
    save="Modificări nesalvate" if state.dirty else "Salvat"
    api="API configurat" if bool(state.api_key) else "API neconfigurat"
    return ft.Container(ft.Row([ft.Column([ft.Text(filename,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,max_lines=1),
        ft.Text(save,size=t.TYPE_LABEL,color=t.WARNING if state.dirty else t.SUCCESS)],spacing=0),ft.Container(expand=True),
        ft.Container(ft.Text(api,size=t.TYPE_LABEL,color=t.secondary_color()),padding=ft.Padding(10,5,10,5),bgcolor=t.surface_alt_color(),border_radius=t.R_CONTROL),
        ft.IconButton(ft.Icons.SETTINGS_OUTLINED,tooltip="Setări",on_click=lambda e:on_settings()),
        ft.IconButton(ft.Icons.DARK_MODE_OUTLINED,tooltip="Schimbă tema",on_click=lambda e:on_theme()),
        ft.IconButton(ft.Icons.HELP_OUTLINE,tooltip="Ajutor",on_click=lambda e:on_help())],spacing=t.S8),
        height=t.TOP_BAR_HEIGHT,padding=ft.Padding(t.S16,0,t.S16,0),bgcolor=t.surface_color(),border=ft.Border(bottom=ft.BorderSide(1,t.border_color())))

