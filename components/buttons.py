from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t


def primary_button(text:str,on_click:Callable|None,icon:ft.IconData|None=None,disabled:bool=False)->ft.Button:
    return ft.Button(text,icon=icon,on_click=on_click,disabled=disabled,height=40,bgcolor=t.ACCENT,color=ft.Colors.ON_PRIMARY,elevation=0,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=t.R_CONTROL),padding=ft.Padding(16,0,16,0)))


def secondary_button(text:str,on_click:Callable|None,icon:ft.IconData|None=None,disabled:bool=False)->ft.OutlinedButton:
    return ft.OutlinedButton(text,icon=icon,on_click=on_click,disabled=disabled,height=40,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=t.R_CONTROL),padding=ft.Padding(14,0,14,0),side=ft.BorderSide(1,t.border_color())))


def tertiary_button(text:str,on_click:Callable|None,icon:ft.IconData|None=None)->ft.TextButton:
    return ft.TextButton(text,icon=icon,on_click=on_click,height=36)

