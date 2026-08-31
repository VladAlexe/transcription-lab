from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from components.buttons import primary_button


def file_empty_state(on_choose:Callable)->ft.Control:
    return ft.Container(ft.Column([ft.Icon(ft.Icons.AUDIO_FILE_OUTLINED,size=34,color=t.ACCENT),
        ft.Text("Selectează o înregistrare",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
        ft.Text("M4A, WAV, MP3, MP4, AAC, FLAC sau WEBM",size=t.TYPE_SECONDARY,color=t.secondary_color()),
        primary_button("Alege fișierul",on_choose,ft.Icons.FOLDER_OPEN)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=t.S8),
        height=210,alignment=ft.Alignment.CENTER,bgcolor=t.surface_color(),border=ft.Border.all(1,t.border_color()),border_radius=t.R_CARD)

