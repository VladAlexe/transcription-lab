from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from app_state import AppState
from components.buttons import primary_button
from components.speaker_panel import speaker_panel
from components.transcript_list import transcript_list
from models import TranscriptSegment
from speaker_reconciliation import speaker_statistics,apply_speaker_mapping
from theme import surface

PAGE_SIZE=80


def build(state:AppState,on_map:Callable[[str,str],None],on_select:Callable[[int],None],on_play:Callable[[int],None],
          on_export:Callable[[],None],selected_index:int|None,offset:int,on_page:Callable[[int],None])->ft.Control:
    stats=speaker_statistics(state.transcript_segments)
    left=ft.Container(ft.Column([ft.Text("Identități",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
        ft.Text(f"{len(stats)} etichete detectate",size=t.TYPE_LABEL,color=t.secondary_color()),
        speaker_panel(stats,state.speaker_mapping,on_map)],spacing=t.S8,expand=True),width=285,padding=ft.Padding(0,0,t.S16,0),
        border=ft.Border(right=ft.BorderSide(1,t.border_color())))
    center=ft.Column([ft.Row([ft.Column([ft.Text("Vorbitori",size=t.TYPE_PAGE,weight=ft.FontWeight.W_600),
        ft.Text("Reconciliază etichetele și revizuiește intervențiile.",size=t.TYPE_SECONDARY,color=t.secondary_color())],spacing=t.S4),
        ft.Container(expand=True),primary_button("Continuă la export",lambda e:on_export(),ft.Icons.ARROW_FORWARD)]),
        ft.Container(ft.Row([ft.Icon(ft.Icons.WARNING_AMBER,size=17,color=t.WARNING),
            ft.Text("Etichetele sunt stabilite separat pentru fiecare fragment. Verifică identitatea înainte de export.",size=t.TYPE_LABEL)],spacing=t.S8),
            padding=t.S12,bgcolor=t.surface_alt_color(),border=ft.Border.all(1,t.border_color()),border_radius=t.R_CONTROL),
        transcript_list(state.transcript_segments,state.speaker_mapping,selected_index,offset,PAGE_SIZE,on_select,on_play,on_page)],spacing=t.S12,expand=True)
    return ft.Row([left,ft.Container(center,padding=ft.Padding(t.S16,0,0,0),expand=True)],spacing=0,expand=True)


def inspector(state:AppState,index:int|None,on_save:Callable[[int,str],None],on_revert:Callable[[int],None],on_play:Callable[[int],None])->ft.Control:
    if index is None or index>=len(state.transcript_segments):
        return ft.Column([ft.Text("Inspector",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
            ft.Text("Selectează o intervenție pentru detalii și corecturi.",size=t.TYPE_SECONDARY,color=t.secondary_color())],spacing=t.S8)
    item=state.transcript_segments[index]; field=ft.TextField(label="Text corectat",value=item.text,multiline=True,min_lines=8,max_lines=18,text_size=t.TYPE_BODY)
    return ft.Column([ft.Text("Intervenție selectată",size=t.TYPE_SECTION,weight=ft.FontWeight.W_600),
        ft.Text(item.speaker_id,size=t.TYPE_LABEL,color=t.secondary_color()),
        ft.Text(apply_speaker_mapping(item,state.speaker_mapping),size=t.TYPE_BODY,weight=ft.FontWeight.W_600),ft.Divider(color=t.border_color()),
        ft.Text("TEXT ORIGINAL",size=t.TYPE_LABEL,color=t.secondary_color(),weight=ft.FontWeight.W_600),
        ft.Text(item.original_text,size=t.TYPE_BODY,selectable=True),field,
        primary_button("Salvează corectura",lambda e:on_save(index,field.value or ""),ft.Icons.CHECK),
        ft.TextButton("Revino la original",icon=ft.Icons.RESTORE,on_click=lambda e:on_revert(index)),
        ft.TextButton("Ascultă intervalul",icon=ft.Icons.PLAY_ARROW,on_click=lambda e:on_play(index))],spacing=t.S12,scroll=ft.ScrollMode.AUTO)

