from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from components.buttons import primary_button,secondary_button,tertiary_button


def modal_dialog(page:ft.Page,title:str,body:ft.Control,actions:list[ft.Control],icon:ft.IconData=ft.Icons.INFO_OUTLINE)->None:
    page.show_dialog(ft.AlertDialog(modal=True,title=ft.Row([ft.Icon(icon,size=21,color=t.ACCENT),ft.Text(title,size=18,weight=ft.FontWeight.W_600)],spacing=t.S8),
        content=ft.Container(body,width=470),actions=actions,actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=t.R_DIALOG),content_padding=ft.Padding(t.S24,t.S12,t.S24,t.S16)))


def message_dialog(page:ft.Page,title:str,message:str)->None:
    modal_dialog(page,title,ft.Text(message,size=t.TYPE_BODY,selectable=True),[primary_button("Închide",lambda e:page.pop_dialog())])


def confirm_dialog(page:ft.Page,title:str,message:str,on_confirm:Callable[[],None])->None:
    def yes(e:ft.Event)->None: page.pop_dialog();on_confirm()
    modal_dialog(page,title,ft.Text(message,size=t.TYPE_BODY),[tertiary_button("Renunță",lambda e:page.pop_dialog()),primary_button("Continuă",yes)],ft.Icons.WARNING_AMBER)


def missing_ffmpeg_dialog(page:ft.Page,on_select:Callable[[],None],on_instructions:Callable[[],None])->None:
    command="winget install --id Gyan.FFmpeg -e"
    def copy(e:ft.Event)->None: page.clipboard.set(command)
    body=ft.Column([ft.Text("Aplicația nu a găsit instrumentele necesare pentru procesarea audio.",size=t.TYPE_BODY),
        ft.Container(ft.Column([ft.Text("ffmpeg: negăsit",size=t.TYPE_MONO,font_family="Consolas"),
            ft.Text("ffprobe: negăsit",size=t.TYPE_MONO,font_family="Consolas")]),padding=t.S12,bgcolor=t.surface_alt_color(),
            border=ft.Border.all(1,t.border_color()),border_radius=t.R_CONTROL),
        ft.Row([ft.Text(command,size=t.TYPE_MONO,font_family="Consolas",selectable=True,expand=True),
            ft.IconButton(ft.Icons.CONTENT_COPY,tooltip="Copiază comanda",on_click=copy)])],spacing=t.S12,tight=True)
    modal_dialog(page,"FFmpeg nu este disponibil",body,[tertiary_button("Instrucțiuni",lambda e:on_instructions()),
        secondary_button("Alege folderul",lambda e:on_select()),primary_button("Închide",lambda e:page.pop_dialog())],ft.Icons.BUILD_OUTLINED)


def error_notification(page:ft.Page,message:str)->None:
    page.show_dialog(ft.SnackBar(ft.Text(message,size=t.TYPE_BODY),bgcolor=t.ERROR,show_close_icon=True))

