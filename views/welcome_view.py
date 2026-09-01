from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.brand import hero
from components.buttons import primary_button,secondary_button
from theme import card


def build(on_start:Callable[[],None],on_help:Callable[[],None])->ft.Control:
    facts=((ft.Icons.LOCK_OUTLINE,s.WELCOME_FACT_LOCAL),(ft.Icons.CLOUD_UPLOAD_OUTLINED,s.WELCOME_FACT_UPLOAD),
           (ft.Icons.KEY_OUTLINED,s.WELCOME_FACT_KEY))
    body=ft.Column([
        hero(),
        ft.Container(height=t.S8),
        ft.Text(s.WELCOME_TITLE,size=t.TYPE_DISPLAY,weight=ft.FontWeight.W_600,color=t.on_surface()),
        ft.Text(s.WELCOME_BODY,size=t.TYPE_BODY,color=t.on_surface_variant()),
        ft.Container(height=t.S8),
        card(ft.Column([ft.Row([ft.Icon(icon,size=18,color=t.primary()),
            ft.Text(text,size=t.TYPE_SECONDARY,color=t.on_surface(),expand=True)],spacing=t.S12) for icon,text in facts],spacing=t.S16)),
        ft.Container(height=t.S8),
        ft.Row([primary_button(s.WELCOME_START,lambda e:on_start(),ft.Icons.ARROW_FORWARD),
            secondary_button(s.WELCOME_HOW,lambda e:on_help())],spacing=t.S12),
        ft.Text(s.OPEN_EXISTING_BODY,size=t.TYPE_LABEL,color=t.muted())],
        spacing=t.S12,horizontal_alignment=ft.CrossAxisAlignment.START)
    return ft.Container(ft.Row([ft.Container(expand=1),ft.Container(body,expand=6),ft.Container(expand=1)],
        alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=t.background(),padding=t.S32,alignment=ft.Alignment.CENTER,expand=True)
