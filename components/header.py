from __future__ import annotations
import flet as ft
from theme import MUTED


def section_header(title:str,subtitle:str,status:str="")->ft.Control:
    return ft.Row([ft.Column([ft.Text(title,size=24,weight=ft.FontWeight.W_600),ft.Text(subtitle,size=13,color=MUTED)],spacing=3),
                   ft.Text(status,size=12,color=MUTED)],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

