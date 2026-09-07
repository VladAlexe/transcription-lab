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
from components.buttons import secondary_button

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
        height=t.TOP_BAR_HEIGHT,bgcolor=t.chrome())


def save_status(dirty:bool,target:str)->str:
    """One line saying whether there is unsaved work and which file it belongs to."""
    if not target: return s.SAVE_STATUS_NEW if dirty else s.SAVE_STATUS_UNTITLED
    return (s.SAVE_STATUS_UNSAVED if dirty else s.SAVE_STATUS_SAVED).format(name=target)


def top_bar(state:AppState,on_settings:Callable[[],None],on_theme:Callable[[],None],on_help:Callable[[],None],
            refs:dict|None=None,on_minimize:Callable[[],None]|None=None,
            on_maximize:Callable[[],None]|None=None,on_close:Callable[[],None]|None=None,
            maximized:bool=False,on_save:Callable[[],None]|None=None,
            save_target:str="",on_save_as:Callable[[],None]|None=None,
            lead_offset:float=0.0)->ft.Control:
    filename=state.selected_file_metadata.filename if state.selected_file_metadata else s.UNTITLED_PROJECT
    # Where Ctrl+S will actually write, said on screen rather than in the Save button's
    # tooltip. The terse Saved / Unsaved dot lives in the status band along the bottom;
    # this line is beside the Save button, so it answers the question that belongs there.
    status=ft.Text(save_status(state.dirty,save_target),size=t.TYPE_LABEL,
        color=t.warning() if state.dirty else t.on_surface_variant(),
        max_lines=1,no_wrap=True,overflow=ft.TextOverflow.ELLIPSIS)
    if refs is not None: refs["status"]=status

    # Left zone: a two-line stack, vertically centred, starting at the content column's own
    # left padding rather than hard against the sidebar divider.
    # The bar spans the window, so its left zone is indented past the sidebar: the file the
    # window is about lines up with the work it is about, and the strip above the sidebar
    # stays a plain drag area rather than a second column of text over the wordmark.
    identity=drag_handle(ft.Container(
        ft.Column([ft.Text(filename,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,
            color=t.on_surface(),max_lines=1,no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,tooltip=filename),status],
            spacing=1,tight=True,alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.Padding(max(t.S16,lead_offset+t.S16),0,t.S16,0),
        height=t.TOP_BAR_HEIGHT,expand=True,alignment=ft.Alignment.CENTER_LEFT))

    def action(icon:ft.IconData,tooltip:str,handler:Callable[[],None])->ft.Control:
        return ft.IconButton(icon,tooltip=tooltip,on_click=lambda e:handler(),
            icon_color=t.on_surface_variant(),icon_size=19,
            width=t.ICON_BUTTON,height=t.ICON_BUTTON)

    # Save sits beside the Saved / Unsaved changes line it answers to, on every screen, so
    # the project can be written at any moment instead of only from an icon in the sidebar.
    saveable=bool(state.transcript_segments)
    save=secondary_button(s.SAVE_PROJECT,(lambda e:on_save()) if on_save and saveable else None,
        ft.Icons.SAVE_OUTLINED,disabled=not (on_save and saveable))
    if not saveable: save.tooltip=s.SAVE_PROJECT_EMPTY
    elif save_target: save.tooltip=s.SAVE_PROJECT_TO.format(name=save_target)
    else: save.tooltip=s.SAVE_PROJECT_TOOLTIP
    save.height=36
    save_as=ft.PopupMenuButton(
        items=[ft.PopupMenuItem(content=ft.Text(s.SAVE_AS,size=t.TYPE_SECONDARY,color=t.on_surface()),
            on_click=lambda e:on_save_as() if on_save_as else None)],
        icon=ft.Icons.EXPAND_MORE,icon_color=t.on_surface_variant(),icon_size=16,
        tooltip=s.SAVE_AS,disabled=not (on_save_as and saveable),
        width=28,height=36,padding=0,shape=ft.RoundedRectangleBorder(radius=t.R_SM))
    if refs is not None: refs["save_button"]=save; refs["save_as_button"]=save_as

    icons=ft.Row([action(ft.Icons.SETTINGS_OUTLINED,s.SETTINGS,on_settings),
        action(ft.Icons.DARK_MODE_OUTLINED,s.TOGGLE_THEME,on_theme),
        action(ft.Icons.HELP_OUTLINE,s.HELP,on_help)],spacing=t.ICON_BUTTON_GAP,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)
    # The chip only appears while there is no key. Once there is one it has nothing to say,
    # and it said it on every screen including the one you cannot act on.
    # The API key chip is gone from here. The status band along the bottom carries the key,
    # the provider and the language at all times and leads to Settings when clicked, so a
    # second badge in the title bar was the same sentence twice on every screen.
    lead:list[ft.Control]=[save,save_as,ft.Container(width=t.S16)]
    right=ft.Row([*lead,icons],spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)

    controls:list[ft.Control]=[identity,right]
    if on_minimize and on_maximize and on_close:
        controls.append(window_controls(on_minimize,on_maximize,on_close,maximized,refs))
    else:
        controls.append(ft.Container(width=t.S16))
    return ft.Container(ft.Row(controls,spacing=0,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.TOP_BAR_HEIGHT,bgcolor=t.chrome(),
        border=ft.Border(bottom=ft.BorderSide(t.HAIRLINE,t.outline())))
