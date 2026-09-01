"""The title bar: three zones, everything vertically centred in a 64px band.

Spacing is declared rather than inherited — chip, icon cluster, divider and the OS window
controls each have a named gap, so the right-hand side cannot crowd itself.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState

WINDOW_BUTTON_WIDTH=46


def _window_button(icon:ft.IconData,tooltip:str,handler:Callable[[],None],danger:bool=False)->ft.IconButton:
    return ft.IconButton(icon,tooltip=tooltip,on_click=lambda e:handler(),icon_size=16,
        icon_color=t.on_surface_variant(),width=WINDOW_BUTTON_WIDTH,height=t.TOP_BAR_HEIGHT,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0),
            overlay_color={ft.ControlState.HOVERED:t.error() if danger else t.surface_variant()},
            color={ft.ControlState.HOVERED:t.on_primary() if danger else t.on_surface()}))


def window_controls(on_minimize:Callable[[],None],on_maximize:Callable[[],None],on_close:Callable[[],None],
                    maximized:bool=False,refs:dict|None=None)->ft.Control:
    maximize=_window_button(ft.Icons.FILTER_NONE if maximized else ft.Icons.CROP_SQUARE,
        s.WINDOW_RESTORE if maximized else s.WINDOW_MAXIMIZE,on_maximize)
    if refs is not None: refs["maximize_button"]=maximize
    buttons=ft.Row([_window_button(ft.Icons.REMOVE,s.WINDOW_MINIMIZE,on_minimize),maximize,
        _window_button(ft.Icons.CLOSE,s.WINDOW_CLOSE,on_close,danger=True)],spacing=0)
    # A clear gap, then a hairline rule, then the controls — they never sit against the icons.
    return ft.Row([ft.Container(width=t.CONTROLS_GAP),
        ft.Container(width=1,height=t.S24,bgcolor=t.outline()),buttons],spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)


def drag_handle(content:ft.Control)->ft.Control:
    return ft.WindowDragArea(content,expand=True,maximizable=True)


def window_chrome(on_minimize:Callable[[],None],on_maximize:Callable[[],None],on_close:Callable[[],None],
                  maximized:bool=False)->ft.Control:
    return ft.Container(ft.Row([
        drag_handle(ft.Container(ft.Row([ft.Text(s.APP_NAME,size=t.TYPE_LABEL,color=t.muted())],
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(t.TOP_BAR_LEFT,0,t.S16,0),height=t.TOP_BAR_HEIGHT)),
        window_controls(on_minimize,on_maximize,on_close,maximized)],spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.TOP_BAR_HEIGHT,bgcolor=t.surface(),border=ft.Border(bottom=ft.BorderSide(1,t.outline())))


def top_bar(state:AppState,on_settings:Callable[[],None],on_theme:Callable[[],None],on_help:Callable[[],None],
            refs:dict|None=None,on_minimize:Callable[[],None]|None=None,
            on_maximize:Callable[[],None]|None=None,on_close:Callable[[],None]|None=None,
            maximized:bool=False)->ft.Control:
    filename=state.selected_file_metadata.filename if state.selected_file_metadata else s.UNTITLED_PROJECT
    status=ft.Text(s.UNSAVED if state.dirty else s.SAVED,size=t.TYPE_LABEL,
        color=t.warning() if state.dirty else t.success())
    api=ft.Text(s.API_CONFIGURED if state.active_api_key else s.API_MISSING,size=t.TYPE_LABEL,
        color=t.on_surface_variant(),max_lines=1,no_wrap=True)
    if refs is not None: refs["status"]=status; refs["api"]=api

    # Left zone: a two-line stack, vertically centred, starting at the content column's own
    # left padding rather than hard against the sidebar divider.
    identity=drag_handle(ft.Container(
        ft.Column([ft.Text(filename,size=t.TYPE_SUBHEADING,weight=ft.FontWeight.W_600,color=t.on_surface(),
            max_lines=1,no_wrap=True),status],spacing=2,tight=True,
            alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.Padding(t.TOP_BAR_LEFT,0,t.S16,0),height=t.TOP_BAR_HEIGHT,
        alignment=ft.Alignment.CENTER_LEFT))

    def action(icon:ft.IconData,tooltip:str,handler:Callable[[],None])->ft.Control:
        return ft.IconButton(icon,tooltip=tooltip,on_click=lambda e:handler(),
            icon_color=t.on_surface_variant(),icon_size=19,
            width=t.ICON_BUTTON,height=t.ICON_BUTTON)

    chip=ft.Container(api,padding=ft.Padding(t.S12,6,t.S12,6),bgcolor=t.surface_variant(),
        border_radius=t.R_PILL)
    icons=ft.Row([action(ft.Icons.SETTINGS_OUTLINED,s.SETTINGS,on_settings),
        action(ft.Icons.DARK_MODE_OUTLINED,s.TOGGLE_THEME,on_theme),
        action(ft.Icons.HELP_OUTLINE,s.HELP,on_help)],spacing=t.ICON_BUTTON_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)
    right=ft.Row([chip,ft.Container(width=t.CHIP_GAP),icons],spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)

    controls:list[ft.Control]=[identity,right]
    if on_minimize and on_maximize and on_close:
        controls.append(window_controls(on_minimize,on_maximize,on_close,maximized,refs))
    else:
        controls.append(ft.Container(width=t.S16))
    return ft.Container(ft.Row(controls,spacing=0,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.TOP_BAR_HEIGHT,bgcolor=t.surface(),border=ft.Border(bottom=ft.BorderSide(1,t.outline())))
