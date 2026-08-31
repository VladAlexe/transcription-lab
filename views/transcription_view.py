from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState
from components.buttons import primary_button,secondary_button
from components.progress_timeline import progress_timeline
from theme import surface
from transcription import MODEL


def build(state:AppState,on_start:Callable[[str],None],on_cancel:Callable[[],None],elapsed:str="00:00")->ft.Control:
    key=ft.TextField(label="Cheie API OpenAI",password=True,can_reveal_password=True,value=state.api_key,dense=True,height=42)
    progress=state.transcription_progress; operation=state.activity_log[-1] if state.activity_log else "Pregătit pentru transcriere"
    current=max(1,int(progress*max(1,len(state.generated_chunks)))) if state.processing else 0
    main=surface(ft.Column([ft.Row([ft.Column([ft.Text(operation,size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
        ft.Text(f"Model {MODEL}",size=t.TYPE_LABEL,color=t.secondary_color())],expand=True),
        ft.Text(f"{int(progress*100)}%",size=22,weight=ft.FontWeight.W_600,color=t.ACCENT)]),
        ft.ProgressBar(value=progress,color=t.ACCENT,bgcolor=ft.Colors.with_opacity(.08,t.ACCENT),height=6),
        ft.Row([ft.Text(f"Fragment {current} din {len(state.generated_chunks) or '—'}",size=t.TYPE_LABEL,color=t.secondary_color()),
            ft.Container(expand=True),ft.Text(f"Timp scurs {elapsed}",size=t.TYPE_LABEL,color=t.secondary_color()),
            secondary_button("Anulează",lambda e:on_cancel(),disabled=not state.processing)],spacing=t.S12)],spacing=t.S16))
    log="\n".join(state.activity_log[-80:]) or "Activitatea tehnică va apărea aici."
    return ft.Column([ft.Column([ft.Text("Transcriere",size=t.TYPE_PAGE,weight=ft.FontWeight.W_600),
        ft.Text("Fragmentele sunt procesate secvențial; interfața rămâne disponibilă.",size=t.TYPE_SECONDARY,color=t.secondary_color())],spacing=t.S4),
        surface(ft.Column([key,ft.Row([ft.Text("Cheia nu este salvată. ChatGPT și API au facturări separate.",size=t.TYPE_LABEL,color=t.secondary_color(),expand=True),
            primary_button("Începe transcrierea",lambda e:on_start(key.value or ""),ft.Icons.PLAY_ARROW,disabled=state.processing)])],spacing=t.S12)),
        main,surface(ft.Column([ft.Text("Etapele procesării",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),progress_timeline(progress,bool(state.error_state))]),padding=t.S16),
        ft.ExpansionTile("Jurnal de activitate",subtitle="Detalii compacte pentru diagnostic",expanded=False,
            controls=[ft.Container(ft.Column([ft.Row([ft.Text("DIAGNOSTIC",size=t.TYPE_LABEL,color=t.secondary_color()),ft.Container(expand=True),
                ft.IconButton(ft.Icons.CONTENT_COPY,tooltip="Copiază detaliile",on_click=lambda e:e.page.clipboard.set(log))]),
                ft.Text(log,size=t.TYPE_MONO,font_family="Consolas",selectable=True)],spacing=t.S8),padding=t.S12,bgcolor=t.surface_alt_color(),border_radius=t.R_CONTROL)])
    ],spacing=t.S16,scroll=ft.ScrollMode.AUTO,expand=True)

