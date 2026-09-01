from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import primary_button


def empty_state(icon:ft.IconData,title:str,body:str,action:ft.Control|None=None,
                available:float|None=None)->ft.Control:
    """A card sized to its contents, capped at 560px and centred in the content column.

    `available` is the width of the column this card sits in. The card is never wider than
    that, so the cap cannot become an overflow on a narrow window; height comes from the
    contents plus its padding rather than from a fixed rectangle.
    """
    width=t.EMPTY_STATE_MAX if available is None else min(t.EMPTY_STATE_MAX,float(available))
    controls:list[ft.Control]=[
        ft.Container(ft.Icon(icon,size=20,color=t.muted()),
            width=t.EMPTY_STATE_ICON,height=t.EMPTY_STATE_ICON,bgcolor=t.surface_variant(),
            border=ft.Border.all(1,t.outline()),border_radius=t.R_MD,alignment=ft.Alignment.CENTER),
        ft.Text(title,size=t.TYPE_SUBHEADING,weight=ft.FontWeight.W_500,color=t.on_surface(),
            text_align=ft.TextAlign.CENTER),
        ft.Text(body,size=t.TYPE_LABEL,color=t.muted(),text_align=ft.TextAlign.CENTER)]
    if action is not None: controls.append(action)
    card=ft.Container(
        ft.Column(controls,horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,spacing=t.EMPTY_STATE_RHYTHM,tight=True),
        width=width,padding=t.EMPTY_STATE_PADDING,bgcolor=t.surface(),
        border=ft.Border.all(1,t.outline()),border_radius=t.R_LG)
    return ft.Row([card],alignment=ft.MainAxisAlignment.CENTER)


def file_empty_state(on_choose:Callable,available:float|None=None)->ft.Control:
    return empty_state(ft.Icons.UPLOAD_FILE_OUTLINED,s.EMPTY_RECORDING_TITLE,s.EMPTY_RECORDING_BODY,
        primary_button(s.CHOOSE_FILE,on_choose,ft.Icons.FOLDER_OPEN),available)
