from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
from components.buttons import secondary_button
from document_export import format_timestamp
from models import TranscriptSegment
from speaker_reconciliation import apply_speaker_mapping


def transcript_item(index:int,item:TranscriptSegment,mapping:dict[str,str],selected:bool,on_select:Callable[[int],None],on_play:Callable[[int],None])->ft.Control:
    return ft.Container(ft.Row([ft.Text(f"{format_timestamp(item.absolute_start)[3:]}–{format_timestamp(item.absolute_end)[3:]}",
            width=92,size=t.TYPE_LABEL,color=t.secondary_color(),font_family="Consolas"),
        ft.Column([ft.Row([ft.Text(apply_speaker_mapping(item,mapping),size=t.TYPE_BODY,weight=ft.FontWeight.W_600),
            ft.Text(item.speaker_id,size=t.TYPE_LABEL,color=t.secondary_color(),visible=selected)]),
            ft.Text(item.text,size=t.TYPE_BODY,selectable=True,max_lines=4,overflow=ft.TextOverflow.ELLIPSIS)],spacing=t.S4,expand=True),
        ft.IconButton(ft.Icons.PLAY_ARROW,tooltip="Ascultă intervenția",on_click=lambda e:on_play(index),icon_size=18),
        ft.Icon(ft.Icons.CHEVRON_RIGHT,size=18,color=t.secondary_color())],vertical_alignment=ft.CrossAxisAlignment.START),
        padding=ft.Padding(t.S12,t.S12,t.S8,t.S12),bgcolor=ft.Colors.with_opacity(.08,t.ACCENT) if selected else None,
        border=ft.Border(bottom=ft.BorderSide(1,t.border_color())),on_click=lambda e:on_select(index))


def transcript_list(segments:list[TranscriptSegment],mapping:dict[str,str],selected_index:int|None,offset:int,page_size:int,
                    on_select:Callable[[int],None],on_play:Callable[[int],None],on_page:Callable[[int],None])->ft.Control:
    subset=segments[offset:offset+page_size]
    rows=[transcript_item(offset+i,item,mapping,selected_index==offset+i,on_select,on_play) for i,item in enumerate(subset)]
    total_pages=max(1,(len(segments)+page_size-1)//page_size); current=offset//page_size+1
    return ft.Column([ft.ListView(rows,expand=True,spacing=0),ft.Row([secondary_button("Anterior",lambda e:on_page(max(0,offset-page_size)),disabled=offset==0),
        ft.Text(f"Pagina {current} din {total_pages}",size=t.TYPE_LABEL,color=t.secondary_color()),
        secondary_button("Următor",lambda e:on_page(offset+page_size),disabled=offset+page_size>=len(segments))],alignment=ft.MainAxisAlignment.CENTER)],expand=True)

