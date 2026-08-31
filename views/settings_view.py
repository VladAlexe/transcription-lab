from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState
from components.buttons import primary_button,secondary_button
from theme import surface


def build(state:AppState,on_apply:Callable[...,None],on_choose_tools:Callable[[],None],on_reset_welcome:Callable[[],None])->ft.Control:
    settings=state.settings
    appearance=ft.Dropdown(label="Aspect",value=settings.appearance,options=[ft.DropdownOption(key="light",text="Luminos"),ft.DropdownOption(key="dark",text="Întunecat"),ft.DropdownOption(key="system",text="Sistem")],dense=True)
    size=ft.TextField(label="Limită fragment (MB)",value=str(settings.safe_chunk_mb),dense=True);bitrate=ft.TextField(label="AAC fallback (kbps)",value=str(settings.fallback_bitrate_kbps),dense=True)
    overlap=ft.TextField(label="Suprapunere (secunde)",value=str(settings.overlap_seconds),dense=True)
    include=ft.Switch("Include calea sursei în JSON",value=settings.include_source_path_json);diagnostic=ft.Switch("Jurnalizare diagnostică",value=settings.diagnostic_logging)
    tools=state.media_tools; tool_text=f"{tools.source_type} · {tools.version}" if tools.is_valid else "Indisponibil"
    return ft.Column([ft.Column([ft.Text("Setări",size=t.TYPE_PAGE,weight=ft.FontWeight.W_600),ft.Text("Aspect, procesare audio și instrumente locale.",size=t.TYPE_SECONDARY,color=t.secondary_color())],spacing=t.S4),
        surface(ft.Column([ft.Text("Interfață",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),appearance,
            secondary_button("Afișează din nou introducerea",lambda e:on_reset_welcome())],spacing=t.S12)),
        surface(ft.Column([ft.Text("Procesare audio",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),ft.ResponsiveRow([size,bitrate,overlap]),include,diagnostic],spacing=t.S12)),
        surface(ft.Column([ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE if tools.is_valid else ft.Icons.ERROR_OUTLINE,color=t.SUCCESS if tools.is_valid else t.ERROR),
            ft.Column([ft.Text("FFmpeg",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),ft.Text(tool_text,size=t.TYPE_LABEL,color=t.secondary_color())],expand=True),
            secondary_button("Alege folderul",lambda e:on_choose_tools())]),ft.Text(tools.ffmpeg_path or "Nicio cale configurată",size=t.TYPE_MONO,font_family="Consolas",selectable=True,color=t.secondary_color())],spacing=t.S8)),
        ft.Row([ft.Container(expand=True),primary_button("Salvează setările",lambda e:on_apply(appearance.value,float(size.value or 23),int(bitrate.value or 48),float(overlap.value or 0),include.value,diagnostic.value))])],spacing=t.S16,scroll=ft.ScrollMode.AUTO,expand=True)

