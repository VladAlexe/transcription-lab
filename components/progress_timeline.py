from __future__ import annotations
import flet as ft
import design_tokens as t

STAGES=("Analiză","Pregătire audio","Transcriere","Combinare","Finalizare")


def progress_timeline(progress:float,error:bool=False)->ft.Control:
    active=min(4,int(progress*5)); controls=[]
    for i,label in enumerate(STAGES):
        complete=progress>=1 or i<active; current=i==active and progress<1
        icon=ft.Icons.ERROR_OUTLINE if error and current else ft.Icons.CHECK if complete else ft.Icons.MORE_HORIZ if current else ft.Icons.CIRCLE_OUTLINED
        color=t.ERROR if error and current else t.SUCCESS if complete else t.ACCENT if current else t.secondary_color()
        controls.append(ft.Column([ft.Container(ft.Icon(icon,size=15,color=color),width=28,height=28,border=ft.Border.all(1,color),border_radius=14,alignment=ft.Alignment.CENTER),
            ft.Text(label,size=t.TYPE_LABEL,color=color,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=t.S4,expand=True))
    return ft.Row(controls,alignment=ft.MainAxisAlignment.SPACE_AROUND)

