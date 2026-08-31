from __future__ import annotations
from typing import Callable
import flet as ft
from document_export import format_timestamp
from models import TranscriptSegment
from speaker_reconciliation import apply_speaker_mapping
from theme import MUTED


def transcript_row(index:int,item:TranscriptSegment,mapping:dict[str,str],on_edit:Callable[[int],None],on_play:Callable[[int],None]|None=None)->ft.Control:
    actions=[ft.IconButton(ft.Icons.EDIT_OUTLINED,tooltip="Editează textul",on_click=lambda e:on_edit(index))]
    if on_play: actions.insert(0,ft.IconButton(ft.Icons.PLAY_ARROW,tooltip="Ascultă intervalul",on_click=lambda e:on_play(index)))
    return ft.Container(ft.Column([ft.Row([ft.Column([ft.Text(apply_speaker_mapping(item,mapping),weight=ft.FontWeight.W_600),
        ft.Text(item.speaker_id,size=11,color=MUTED)],spacing=1),ft.Container(expand=True),
        ft.Text(f"{format_timestamp(item.absolute_start)}–{format_timestamp(item.absolute_end)}",size=12,color=MUTED),*actions]),
        ft.Text(item.text,size=13,selectable=True)],spacing=8),padding=12,
        border=ft.Border(bottom=ft.BorderSide(1,t.border_color())))

