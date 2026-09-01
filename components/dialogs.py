from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import icon_button,primary_button,secondary_button,tertiary_button


def modal_dialog(page:ft.Page,title:str,body:ft.Control,actions:list[ft.Control],icon:ft.IconData=ft.Icons.INFO_OUTLINE)->None:
    page.show_dialog(ft.AlertDialog(modal=True,bgcolor=t.surface(),
        title=ft.Row([ft.Icon(icon,size=21,color=t.primary()),ft.Text(title,size=t.TYPE_TITLE,weight=ft.FontWeight.W_600,color=t.on_surface())],spacing=t.S12),
        content=ft.Container(body,width=480),actions=actions,actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=t.R_LG),content_padding=ft.Padding(t.S24,t.S12,t.S24,t.S16)))


def message_dialog(page:ft.Page,title:str,message:str)->None:
    modal_dialog(page,title,ft.Text(message,size=t.TYPE_BODY,color=t.on_surface(),selectable=True),
        [primary_button(s.CLOSE,lambda e:page.pop_dialog())])


def confirm_dialog(page:ft.Page,title:str,message:str,on_confirm:Callable[[],None],
                   confirm_label:str|None=None)->None:
    """One question, one way forward, one way back. The confirm button names the action."""
    def yes(e:ft.Event)->None: page.pop_dialog();on_confirm()
    modal_dialog(page,title,ft.Text(message,size=t.TYPE_BODY,color=t.on_surface()),
        [tertiary_button(s.DISCARD,lambda e:page.pop_dialog()),
         primary_button(confirm_label or s.PROCEED,yes)],ft.Icons.WARNING_AMBER)


def missing_ffmpeg_dialog(page:ft.Page,on_select:Callable[[],None],on_instructions:Callable[[],None])->None:
    command="winget install --id Gyan.FFmpeg -e"
    def copy(e:ft.Event)->None: page.clipboard.set(command)
    body=ft.Column([ft.Text(s.FFMPEG_MISSING_BODY,size=t.TYPE_BODY,color=t.on_surface()),
        ft.Container(ft.Column([ft.Text(s.FFMPEG_NOT_FOUND.format(tool="ffmpeg"),size=t.TYPE_MONO,font_family="Consolas",color=t.on_surface_variant()),
            ft.Text(s.FFMPEG_NOT_FOUND.format(tool="ffprobe"),size=t.TYPE_MONO,font_family="Consolas",color=t.on_surface_variant())],spacing=t.S4),
            padding=t.S12,bgcolor=t.surface_variant(),border=ft.Border.all(1,t.outline()),border_radius=t.R_SM),
        ft.Row([ft.Text(command,size=t.TYPE_MONO,font_family="Consolas",selectable=True,expand=True,color=t.on_surface()),
            icon_button(ft.Icons.CONTENT_COPY,s.COPY_COMMAND,copy)])],spacing=t.S12,tight=True)
    modal_dialog(page,s.FFMPEG_MISSING_TITLE,body,[tertiary_button(s.FFMPEG_INSTRUCTIONS,lambda e:on_instructions()),
        secondary_button(s.CHOOSE_FOLDER,lambda e:on_select()),primary_button(s.CLOSE,lambda e:page.pop_dialog())],ft.Icons.BUILD_OUTLINED)


def notification(page:ft.Page,message:str)->None:
    """A neutral toast for something that worked. Red is reserved for something that did not."""
    page.show_dialog(ft.SnackBar(ft.Text(message,size=t.TYPE_SECONDARY,color=t.surface()),
        bgcolor=t.on_surface(),show_close_icon=True,
        shape=ft.RoundedRectangleBorder(radius=t.R_SM)))


def error_notification(page:ft.Page,message:str)->None:
    page.show_dialog(ft.SnackBar(ft.Text(message,size=t.TYPE_BODY,color=t.on_primary()),bgcolor=t.error(),show_close_icon=True))
