from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState
from components.buttons import primary_button
from document_export import format_timestamp
from speaker_reconciliation import apply_speaker_mapping
from theme import surface


def _format_card(name:str,description:str,icon:ft.IconData,kind:str,path:str,on_save:Callable[[str],None])->ft.Control:
    return ft.Container(ft.Column([ft.Row([ft.Icon(icon,size=22,color=t.ACCENT),ft.Text(name,size=t.TYPE_SECTION,weight=ft.FontWeight.W_600)]),
        ft.Text(description,size=t.TYPE_SECONDARY,color=t.secondary_color()),ft.Container(expand=True),
        ft.Text(path or "Nicio destinație aleasă",size=t.TYPE_LABEL,color=t.SUCCESS if path else t.secondary_color(),max_lines=2),
        primary_button(f"Salvează {name}",lambda e:on_save(kind))],spacing=t.S8),padding=t.S16,height=190,
        bgcolor=t.surface_color(),border=ft.Border.all(1,t.border_color()),border_radius=t.R_CARD,col={"xs":12,"md":4})


def build(state:AppState,on_save:Callable[[str],None],on_metadata:Callable[...,None])->ft.Control:
    info=state.selected_file_metadata; meta=state.export_metadata; segs=state.transcript_segments
    summary=f"{len(segs)} intervenții · {len({apply_speaker_mapping(s,state.speaker_mapping) for s in segs})} participanți · {format_timestamp(info.duration) if info else '—'}"
    title=ft.TextField(label="Titlul documentului",value=meta.title,dense=True); project=ft.TextField(label="Identificator interviu",value=meta.project_id,dense=True)
    date=ft.TextField(label="Data interviului",value=meta.interview_date,dense=True); notes=ft.TextField(label="Observații",value=meta.notes,multiline=True,min_lines=2,max_lines=3)
    timestamps=ft.Checkbox("Include marcaje temporale",value=meta.include_timestamps); notice=ft.Checkbox("Include nota de transcriere automată",value=meta.include_notice)
    labels=ft.Checkbox("Include etichetele originale în JSON",value=meta.include_original_labels)
    def commit(e:ft.Event|None=None)->None:on_metadata(title.value or "",project.value or "",date.value or "",notes.value or "",timestamps.value,notice.value,labels.value)
    for control in (title,project,date,notes,timestamps,notice,labels): control.on_change=commit
    cards=ft.ResponsiveRow([_format_card("Word","Document formatat pentru revizuire și arhivare.",ft.Icons.DESCRIPTION_OUTLINED,"docx",state.export_paths.get("docx",""),on_save),
        _format_card("Text","Transcript simplu, lizibil în orice editor.",ft.Icons.TEXT_SNIPPET_OUTLINED,"txt",state.export_paths.get("txt",""),on_save),
        _format_card("JSON","Date structurate pentru corecții și reutilizare.",ft.Icons.DATA_OBJECT,"json",state.export_paths.get("json",""),on_save)],spacing=t.S12,run_spacing=t.S12)
    return ft.Column([ft.Column([ft.Text("Export",size=t.TYPE_PAGE,weight=ft.FontWeight.W_600),ft.Text(summary,size=t.TYPE_SECONDARY,color=t.secondary_color())],spacing=t.S4),
        surface(ft.Column([ft.Text("Opțiuni document",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),ft.ResponsiveRow([title,project,date]),notes,
            ft.Row([timestamps,notice,labels],wrap=True)],spacing=t.S12)),cards],spacing=t.S16,scroll=ft.ScrollMode.AUTO,expand=True)

