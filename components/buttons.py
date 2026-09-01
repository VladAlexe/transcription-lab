"""Buttons, one weight each.

A screen carries exactly one filled sage button — the thing to do next. Everything else is
an outline or a text button in charcoal, so the eye lands on the primary action first and
nothing else argues with it. Icon buttons all get the same 40px hit area and the same soft
sage hover, so a control is discoverable by pointing at it.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t

BUTTON_HEIGHT = 42


def primary_button(text:str,on_click:Callable|None,icon:ft.IconData|None=None,disabled:bool=False)->ft.Button:
    """The one filled action per screen."""
    return ft.Button(text,icon=icon,on_click=on_click,disabled=disabled,height=BUTTON_HEIGHT,
        bgcolor=t.primary(),color=t.on_primary(),elevation=0,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=t.R_SM),padding=ft.Padding(t.S16,0,t.S16,0),
            overlay_color=t.on_primary()))


def secondary_button(text:str,on_click:Callable|None,icon:ft.IconData|None=None,disabled:bool=False)->ft.OutlinedButton:
    """Quiet outline: available, but not the thing to do next."""
    return ft.OutlinedButton(text,icon=icon,on_click=on_click,disabled=disabled,height=BUTTON_HEIGHT,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=t.R_SM),padding=ft.Padding(t.S16,0,t.S16,0),
            side=ft.BorderSide(t.HAIRLINE,t.outline_strong()),color=t.on_surface(),
            overlay_color=t.primary_soft()))


def tertiary_button(text:str,on_click:Callable|None,icon:ft.IconData|None=None,disabled:bool=False)->ft.TextButton:
    """No border at all: undo, dismiss, and other ways back out."""
    return ft.TextButton(text,icon=icon,on_click=on_click,disabled=disabled,height=38,
        style=ft.ButtonStyle(color=t.on_surface_variant(),overlay_color=t.primary_soft(),
            shape=ft.RoundedRectangleBorder(radius=t.R_SM),padding=ft.Padding(t.S12,0,t.S12,0)))


def icon_button(icon:ft.IconData,tooltip:str,on_click:Callable|None,size:float=18,
                color:str|None=None,disabled:bool=False)->ft.IconButton:
    """A 40px square hit area around a small glyph, with a soft sage hover.

    An 18px icon is a 18px target unless it is given one; every icon control in the app
    goes through here so they are all the same size to point at and all react the same way.
    """
    return ft.IconButton(icon,tooltip=tooltip,on_click=on_click,disabled=disabled,
        icon_size=size,icon_color=color or t.on_surface_variant(),
        width=t.ICON_BUTTON,height=t.ICON_BUTTON,padding=0,
        hover_color=t.primary_soft(),focus_color=t.primary_soft(),
        splash_radius=t.ICON_BUTTON/2,
        style=ft.ButtonStyle(shape=ft.CircleBorder(),overlay_color=t.primary_soft()))
