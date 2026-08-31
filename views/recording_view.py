from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState
from audio_processing import estimated_chunk_count
from components.buttons import primary_button,secondary_button
from components.empty_state import file_empty_state
from document_export import format_timestamp
from theme import surface
from utils import human_size


def _header()->ft.Control:
    return ft.Column([ft.Text("Fișier",size=t.TYPE_PAGE,weight=ft.FontWeight.W_600),
        ft.Text("Selectează înregistrarea și verifică strategia de procesare.",size=t.TYPE_SECONDARY,color=t.secondary_color())],spacing=t.S4)


def build(state:AppState,on_choose:Callable[[],None],on_remove:Callable[[],None],on_continue:Callable[[],None],on_quality:Callable[[bool],None])->ft.Control:
    info=state.selected_file_metadata
    if not info: body=file_empty_state(lambda e:on_choose())
    else:
        quality="Original comprimat" if state.settings.preserve_original else f"AAC mono · {state.settings.fallback_bitrate_kbps} kbps"
        strategy="Copiere flux când este sigură; recodare automată la nevoie" if state.settings.preserve_original else "Recodare fragment cu fragment"
        data=[("Durată",format_timestamp(info.duration)),("Dimensiune",human_size(info.size_bytes)),("Format",info.codec.upper()),
            ("Canale",str(info.channels)),("Eșantionare",f"{info.sample_rate:,} Hz"),("Calitate sursă",quality),
            ("Fragmente estimate",str(estimated_chunk_count(info,state.settings.overlap_seconds,state.settings.safe_chunk_mb))),
            ("Strategie",strategy)]
        body=surface(ft.Column([ft.Row([ft.Container(ft.Icon(ft.Icons.AUDIO_FILE_OUTLINED,size=26,color=t.ACCENT),width=48,height=48,
            bgcolor=ft.Colors.with_opacity(.08,t.ACCENT),border_radius=t.R_CONTROL,alignment=ft.Alignment.CENTER),ft.Column([ft.Text(info.filename,size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
            ft.Text(info.path,size=t.TYPE_LABEL,color=t.secondary_color(),selectable=True,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)],spacing=t.S4,expand=True)]),
            ft.Divider(height=1,color=t.border_color()),ft.ResponsiveRow([ft.Column([ft.Text(k.upper(),size=10.5,color=t.secondary_color(),weight=ft.FontWeight.W_600),
                ft.Text(v,size=t.TYPE_BODY,max_lines=2)],col={"xs":6,"md":3}) for k,v in data],run_spacing=t.S12)],spacing=t.S16))
    quality=ft.RadioGroup(value="original" if state.settings.preserve_original else "compatibil",on_change=lambda e:on_quality(e.control.value=="original"),
        content=ft.Row([ft.Radio("Păstrează sursa comprimată când este sigur",value="original"),ft.Radio("Compatibilitate AAC mono",value="compatibil")],wrap=True))
    return ft.Column([_header(),body,surface(ft.Row([ft.Column([ft.Text("Pregătire audio",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
        ft.Text("Originalul nu este modificat. Numai fragmentele temporare sunt trimise către OpenAI.",size=t.TYPE_SECONDARY,color=t.secondary_color())],expand=True),quality])),
        ft.Container(expand=True),ft.Row([secondary_button("Schimbă fișierul",lambda e:on_choose(),disabled=info is None),
            primary_button("Continuă",lambda e:on_continue(),ft.Icons.ARROW_FORWARD,disabled=info is None)],alignment=ft.MainAxisAlignment.END)],spacing=t.S16,expand=True)

