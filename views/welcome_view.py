from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from components.buttons import primary_button,secondary_button
from theme import surface


def build(on_start:Callable[[],None],on_help:Callable[[],None])->ft.Control:
    facts=[(ft.Icons.LOCK_OUTLINE,"Înregistrarea originală rămâne local."),(ft.Icons.CLOUD_UPLOAD_OUTLINED,"Numai fragmentele temporare sunt trimise către OpenAI."),
           (ft.Icons.KEY_OUTLINED,"Cheia API nu este salvată.")]
    return ft.Container(ft.Column([ft.Container(ft.Icon(ft.Icons.MIC_NONE,size=28,color=ft.Colors.ON_PRIMARY),width=48,height=48,bgcolor=t.ACCENT,border_radius=12,alignment=ft.Alignment.CENTER),
        ft.Text("Transcriere pentru interviuri de grup",size=28,weight=ft.FontWeight.W_600),
        ft.Text("Procesează înregistrări lungi, identifică intervențiile și exportă documente Word.",size=t.TYPE_BODY,color=t.secondary_color(),width=600),
        ft.Container(height=t.S8),surface(ft.Column([ft.Row([ft.Icon(icon,size=18,color=t.ACCENT),ft.Text(text,size=t.TYPE_BODY)]) for icon,text in facts],spacing=t.S12),padding=t.S16),
        ft.Row([primary_button("Începe",lambda e:on_start(),ft.Icons.ARROW_FORWARD),secondary_button("Cum funcționează",lambda e:on_help())])],
        spacing=t.S16,horizontal_alignment=ft.CrossAxisAlignment.START),width=680,padding=t.S32,alignment=ft.Alignment.CENTER)

