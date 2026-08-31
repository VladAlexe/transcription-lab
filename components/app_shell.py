from __future__ import annotations
import flet as ft
import design_tokens as t


def app_shell(nav:ft.Control,top:ft.Control,workspace:ft.Control,inspector:ft.Control|None=None)->ft.Control:
    center=ft.Column([top,ft.Container(workspace,padding=t.S24,expand=True)],spacing=0,expand=True)
    controls=[nav,center]
    if inspector is not None: controls.append(ft.Container(inspector,width=t.INSPECTOR_WIDTH,padding=t.S16,bgcolor=t.surface_alt_color(),
        border=ft.Border(left=ft.BorderSide(1,t.border_color()))))
    return ft.Row(controls,spacing=0,expand=True)

