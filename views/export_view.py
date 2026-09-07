from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.buttons import primary_button,secondary_button
from speaker_reconciliation import apply_speaker_mapping
from theme import page_title,panel_title
from time_range import format_timecode


def _format_card(name:str,description:str,icon:ft.IconData,kind:str,path:str,on_save:Callable[[str],None],
                 accent:bool=False)->ft.Control:
    """One format, one row. It was a 250px tall card with a 44px icon tile above a heading
    above two paragraphs above a button — three of those side by side filled a screen to
    offer three buttons."""
    button=(primary_button if accent else secondary_button)(s.EXPORT_SAVE.format(format=name),
        lambda e:on_save(kind))
    return ft.Container(ft.Row([
        ft.Icon(icon,size=18,color=t.muted()),
        ft.Column([ft.Text(name,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,color=t.on_surface()),
            ft.Text(description,size=t.TYPE_META,color=t.on_surface_variant(),max_lines=2)],
            spacing=1,tight=True,expand=True),
        ft.Text(path or "",size=t.TYPE_META,color=t.primary(),max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,no_wrap=True),
        button],spacing=t.S16,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.CARD_PADDING,t.S12,t.CARD_PADDING,t.S12))


def build(state:AppState,on_save:Callable[[str],None],on_metadata:Callable[...,None])->ft.Control:
    info=state.selected_file_metadata; meta=state.export_metadata; segments=state.transcript_segments
    speakers=len({apply_speaker_mapping(item,state.speaker_mapping) for item in segments})
    summary=s.EXPORT_SUMMARY.format(turns=len(segments),speakers=speakers,
        duration=format_timecode(info.duration) if info else "—")

    def text_field(label:str,value:str,**kwargs)->ft.TextField:
        return ft.TextField(label=label,value=value,dense=True,border_radius=t.RADIUS,
            border_color=t.outline(),focused_border_color=t.primary(),color=t.on_surface(),
            text_size=t.TYPE_BODY,label_style=ft.TextStyle(size=t.TYPE_META,color=t.muted()),
            **kwargs)

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

    # One surface: the fields that describe the document, then the three ways to save it.
    # Two collapsible cards and a row of three tall tiles was a screen and a half of
    # scrolling to press one button.
    options=ft.Container(ft.Column([
        panel_title(s.EXPORT_OPTIONS),
        ft.ResponsiveRow([title,project,date],spacing=t.S12,run_spacing=t.S12),notes,
        ft.Row([timestamps,notice,labels],spacing=t.S16)],spacing=t.S12,tight=True),
        padding=ft.Padding(t.CARD_PADDING,0,t.CARD_PADDING,0))
    formats=ft.Column([
        _format_card(s.EXPORT_WORD,s.EXPORT_WORD_BODY,ft.Icons.DESCRIPTION_OUTLINED,"docx",
            state.export_paths.get("docx",""),on_save,True),
        ft.Divider(height=1,color=t.outline()),
        _format_card(s.EXPORT_TEXT,s.EXPORT_TEXT_BODY,ft.Icons.TEXT_SNIPPET_OUTLINED,"txt",
            state.export_paths.get("txt",""),on_save),
        ft.Divider(height=1,color=t.outline()),
        _format_card(s.EXPORT_JSON,s.EXPORT_JSON_BODY,ft.Icons.DATA_OBJECT,"json",
            state.export_paths.get("json",""),on_save)],spacing=0,tight=True)
    # Who signs the comments, said where the document is made rather than only in Settings.
    # It is the one thing on the Word file a researcher discovers after sending it.
    named=(state.settings.reviewer or "").strip()
    signature=ft.Container(ft.Row([
        ft.Icon(ft.Icons.DRIVE_FILE_RENAME_OUTLINE,size=15,
            color=t.on_surface_variant() if named else t.warning()),
        ft.Text(s.EXPORT_SIGNED_BY.format(name=named) if named else s.EXPORT_SIGNED_NOBODY,
            size=t.TYPE_META,color=t.on_surface_variant(),expand=True,max_lines=2)],
        spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.CARD_PADDING,0,t.CARD_PADDING,0))
    return ft.Column([page_title(s.EXPORT_TITLE,summary,step=4),
        ft.Container(ft.Column([options,signature,ft.Container(height=t.S8),formats],spacing=t.S12),
            padding=ft.Padding(0,t.CARD_PADDING,0,t.S8),bgcolor=t.surface(),
            border_radius=t.RADIUS),
        ft.Text(s.NEXT_EXPORT,size=t.TYPE_META,color=t.muted())],spacing=t.S16)
