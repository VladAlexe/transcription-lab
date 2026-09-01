from __future__ import annotations
import flet as ft
import design_tokens as t
import strings as s


def progress_timeline(progress:float,error:bool=False)->ft.Control:
    stages=s.PROGRESS_STAGES
    active=min(len(stages)-1,int(progress*len(stages))); controls=[]
    for index,label in enumerate(stages):
        complete=progress>=1 or index<active
        current=index==active and progress<1
        icon=(ft.Icons.ERROR_OUTLINE if error and current else ft.Icons.CHECK if complete
              else ft.Icons.MORE_HORIZ if current else ft.Icons.CIRCLE_OUTLINED)
        color=(t.error() if error and current else t.success() if complete
               else t.primary() if current else t.muted())
        marker=ft.Container(ft.Icon(icon,size=15,color=color),width=30,height=30,
            bgcolor=t.primary_soft() if current and not error else None,
            border=ft.Border.all(1,color),border_radius=t.R_PILL,alignment=ft.Alignment.CENTER)
        controls.append(ft.Column([marker,ft.Text(label,size=t.TYPE_CAPTION,color=color,text_align=ft.TextAlign.CENTER)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=t.S8,expand=True))
    return ft.Row(controls,alignment=ft.MainAxisAlignment.SPACE_AROUND)
