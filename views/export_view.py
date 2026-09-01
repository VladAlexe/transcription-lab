from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.buttons import primary_button,secondary_button
from speaker_reconciliation import apply_speaker_mapping
from theme import collapsible_card,page_title,section_title
from time_range import format_timecode


def _format_card(name:str,description:str,icon:ft.IconData,kind:str,path:str,on_save:Callable[[str],None],
                 accent:bool=False)->ft.Control:
    # Word is the primary export; the other two are equal alternatives, so they stay neutral.
    button=(primary_button if accent else secondary_button)(s.EXPORT_SAVE.format(format=name),lambda e:on_save(kind))
    return ft.Container(ft.Column([
        ft.Container(ft.Icon(icon,size=20,color=t.muted()),width=44,height=44,bgcolor=t.surface_variant(),
            border=ft.Border.all(t.HAIRLINE,t.outline()),border_radius=t.R_MD,alignment=ft.Alignment.CENTER),
        ft.Text(name,size=t.TYPE_SUBHEADING,weight=ft.FontWeight.W_600,color=t.on_surface()),
        ft.Text(description,size=t.TYPE_LABEL,color=t.on_surface_variant()),
        ft.Container(expand=True),
        ft.Text(path or s.EXPORT_NO_DESTINATION,size=t.TYPE_CAPTION,max_lines=2,
            color=t.primary() if path else t.muted()),
        button],spacing=t.S12),
        padding=t.CARD_PADDING,height=250,bgcolor=t.surface(),border=ft.Border.all(t.HAIRLINE,t.outline()),
        border_radius=t.R_LG,col={"xs":12,"md":4})


def build(state:AppState,on_save:Callable[[str],None],on_metadata:Callable[...,None])->ft.Control:
    info=state.selected_file_metadata; meta=state.export_metadata; segments=state.transcript_segments
    speakers=len({apply_speaker_mapping(item,state.speaker_mapping) for item in segments})
    summary=s.EXPORT_SUMMARY.format(turns=len(segments),speakers=speakers,
        duration=format_timecode(info.duration) if info else "—")

    def text_field(label:str,value:str,**kwargs)->ft.TextField:
        return ft.TextField(label=label,value=value,dense=True,border_radius=t.R_SM,border_color=t.outline(),
            focused_border_color=t.primary(),color=t.on_surface(),**kwargs)

    title=text_field(s.EXPORT_DOC_TITLE,meta.title,col={"xs":12,"md":4})
    project=text_field(s.EXPORT_PROJECT_ID,meta.project_id,col={"xs":12,"md":4})
    date=text_field(s.EXPORT_DATE,meta.interview_date,col={"xs":12,"md":4})
    notes=text_field(s.EXPORT_NOTES,meta.notes,multiline=True,min_lines=2,max_lines=4)
    timestamps=ft.Checkbox(s.EXPORT_TIMESTAMPS,value=meta.include_timestamps)
    notice=ft.Checkbox(s.EXPORT_NOTICE,value=meta.include_notice)
    labels=ft.Checkbox(s.EXPORT_ORIGINAL_LABELS,value=meta.include_original_labels)

    def commit(event:ft.Event|None=None)->None:
        on_metadata(title.value or "",project.value or "",date.value or "",notes.value or "",
                    timestamps.value,notice.value,labels.value)
    for control in (title,project,date,notes,timestamps,notice,labels): control.on_change=commit

    options=collapsible_card(s.EXPORT_OPTIONS,ft.Column([
        ft.ResponsiveRow([title,project,date],spacing=t.S16,run_spacing=t.S12),notes,
        ft.Row([timestamps,notice,labels],wrap=True,spacing=t.S16)],spacing=t.S16))
    cards=ft.ResponsiveRow([
        _format_card(s.EXPORT_WORD,s.EXPORT_WORD_BODY,ft.Icons.DESCRIPTION_OUTLINED,"docx",state.export_paths.get("docx",""),on_save,True),
        _format_card(s.EXPORT_TEXT,s.EXPORT_TEXT_BODY,ft.Icons.TEXT_SNIPPET_OUTLINED,"txt",state.export_paths.get("txt",""),on_save),
        _format_card(s.EXPORT_JSON,s.EXPORT_JSON_BODY,ft.Icons.DATA_OBJECT,"json",state.export_paths.get("json",""),on_save)],
        spacing=t.S16,run_spacing=t.S16)
    return ft.Column([page_title(s.EXPORT_TITLE,summary,step=4),options,cards,
        ft.Text(s.NEXT_EXPORT,size=t.TYPE_LABEL,color=t.muted())],spacing=t.S24)
