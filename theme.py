from __future__ import annotations
import flet as ft
import design_tokens as t


def application_theme(dark:bool=False)->ft.Theme:
    scheme=ft.ColorScheme(primary=t.ACCENT,on_primary=t.SURFACE,
        surface=t.DARK_SURFACE if dark else t.SURFACE,on_surface=t.DARK_TEXT if dark else t.TEXT,
        outline=t.DARK_BORDER if dark else t.BORDER,error=t.ERROR)
    return ft.Theme(color_scheme=scheme,use_material3=True,font_family="Segoe UI Variable",
        scaffold_bgcolor=t.DARK_BG if dark else t.BG,visual_density=ft.VisualDensity.COMPACT)


def surface(content:ft.Control,padding:int=t.S16,expand:bool|int|None=None,secondary:bool=False)->ft.Container:
    return ft.Container(content=content,padding=padding,expand=expand,
        bgcolor=t.surface_alt_color() if secondary else t.surface_color(),border=ft.Border.all(1,t.border_color()),border_radius=t.R_CARD)

