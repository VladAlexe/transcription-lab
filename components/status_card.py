from __future__ import annotations
import flet as ft
from theme import MUTED, card


def status_card(title:str,detail:str,status:str)->ft.Control:
    return card(ft.Row([ft.Icon(ft.Icons.GRAPHIC_EQ,size=22),ft.Column([ft.Text(title,weight=ft.FontWeight.W_600),
        ft.Text(detail,size=12,color=MUTED)]),ft.Text(status,size=12,color=MUTED)],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),padding=14)

