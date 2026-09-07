from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from audio_processing import estimated_chunk_count
from components.buttons import primary_button,secondary_button
from components.empty_state import file_empty_state
from providers import provider_info
from theme import collapsible_card,note,page_title
from time_range import format_timecode
from utils import human_size

# Signature: (start_text, end_text) -> error message or None. Validation lives in the app,
# rendering of the result lives here.
RangeValidator = Callable[[str, str], str | None]


def _hint(text:str)->ft.Control:
    """Helper line under a field. Flet's `helper` takes a Control, not a string."""
    return ft.Text(text,size=t.TYPE_CAPTION,color=t.muted())


def _metric(label:str,value:str)->ft.Control:
    return ft.Column([ft.Text(label.upper(),size=t.TYPE_CAPTION,color=t.muted(),weight=ft.FontWeight.W_600),
        ft.Text(value,size=t.TYPE_BODY,color=t.on_surface(),max_lines=2)],spacing=t.S4,col={"xs":6,"md":3})


def _range_card(state:AppState,on_range:RangeValidator,on_continue:Callable[[],None])->tuple[ft.Control,ft.Control]:
    duration=state.selected_file_metadata.duration if state.selected_file_metadata else 0
    start=ft.TextField(label=s.RANGE_START,value=format_timecode(state.range_start) if state.range_start else "",
        dense=True,border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
        hint_text="00:00:00",helper=_hint(s.RANGE_START_HELPER),col={"xs":12,"md":4})
    end=ft.TextField(label=s.RANGE_END,value=format_timecode(state.range_end) if state.range_end else "",
        dense=True,border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
        hint_text=format_timecode(duration),helper=_hint(s.RANGE_END_HELPER),col={"xs":12,"md":4})
    summary=ft.Text("",size=t.TYPE_LABEL,color=t.on_surface_variant())
    error=ft.Text("",size=t.TYPE_LABEL,color=t.error(),visible=False)
    proceed=primary_button(s.CONTINUE,lambda e:on_continue(),ft.Icons.ARROW_FORWARD,
        disabled=state.selected_file_metadata is None)

    def commit(event:ft.Event|None=None)->None:
        message=on_range(start.value or "",end.value or "")
        error.value=message or ""; error.visible=bool(message)
        start.error_text=message if message else None
        summary.value="" if message else _describe(state,duration)
        proceed.disabled=bool(message) or state.selected_file_metadata is None
        for control in (start,end,error,summary,proceed):
            try: control.update()
            except Exception: pass

    summary.value=_describe(state,duration)
    start.on_blur=commit; end.on_blur=commit; start.on_submit=commit; end.on_submit=commit
    body=ft.Column([ft.ResponsiveRow([start,end],spacing=t.S16,run_spacing=t.S12),error,summary,
        ft.Text(s.RANGE_COST_NOTE,size=t.TYPE_LABEL,color=t.muted())],spacing=t.S12)
    return collapsible_card(s.RANGE_TITLE,body,s.RANGE_SUBTITLE),proceed


def _describe(state:AppState,duration:float)->str:
    if state.range_start is None and state.range_end is None:
        return s.RANGE_FULL.format(duration=format_timecode(duration))
    begin=state.range_start or 0.0; finish=state.range_end if state.range_end is not None else duration
    return s.RANGE_PARTIAL.format(start=format_timecode(begin),end=format_timecode(finish),
        duration=format_timecode(max(0.0,finish-begin)),total=format_timecode(duration))


def _byok_card(provider_label:str,on_settings:Callable[[],None]|None)->ft.Control:
    """Bring your own key, said on the first screen rather than discovered on the third.

    A fresh install has no transcription account behind it. Nothing here is an error — the
    researcher can pick a file and look around perfectly well — so it is a quiet card, not
    a warning, and it names both places involved: the provider lives in Settings, the key
    is entered on the Transcription step.
    """
    body=ft.Column([ft.Text(s.BYOK_TITLE,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,
            color=t.on_surface()),
        ft.Text(s.BYOK_BODY,size=t.TYPE_META,color=t.on_surface_variant(),max_lines=2)],
        spacing=1,tight=True,expand=True)
    row:list[ft.Control]=[ft.Icon(ft.Icons.KEY_OUTLINED,size=17,color=t.muted()),body]
    if on_settings is not None:
        row.append(secondary_button(s.BYOK_ACTION,lambda e:on_settings(),ft.Icons.SETTINGS_OUTLINED))
    return ft.Container(ft.Row(row,spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.CARD_PADDING,t.S12,t.CARD_PADDING,t.S12),
        bgcolor=t.surface_variant(),border_radius=t.RADIUS)


def build(state:AppState,on_choose:Callable[[],None],on_remove:Callable[[],None],on_continue:Callable[[],None],
          on_quality:Callable[[bool],None],on_range:RangeValidator,
          content_width:float|None=None,on_open_project:Callable[[],None]|None=None,
          on_open_settings:Callable[[],None]|None=None)->ft.Control:
    info=state.selected_file_metadata
    provider=provider_info(state.settings.provider)
    needs_key=not state.active_api_key
    if not info:
        # One screen, no scrolling: the drop target, the key notice and the way back to a
        # saved project. It used to be a 480px empty state, a paragraph, then two cards.
        blocks:list[ft.Control]=[
            ft.Column([
                ft.Text(s.RECORDING_TITLE,size=t.TYPE_DISPLAY,weight=ft.FontWeight.W_600,
                    color=t.on_surface()),
                ft.Text(s.RECORDING_SUBTITLE,size=t.TYPE_META,color=t.muted())],
                spacing=2,tight=True),
            ft.Container(ft.Column([
                ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED,size=26,color=t.muted()),
                ft.Text(s.EMPTY_RECORDING_TITLE,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,
                    color=t.on_surface()),
                ft.Text(s.EMPTY_RECORDING_BODY,size=t.TYPE_META,color=t.muted()),
                ft.Container(height=t.S4),
                primary_button(s.CHOOSE_FILE,lambda e:on_choose(),ft.Icons.FOLDER_OPEN),
                ft.Text(s.EMPTY_RECORDING_HINT,size=t.TYPE_META,color=t.muted(),
                    text_align=ft.TextAlign.CENTER)],
                spacing=t.S8,tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=t.S32,bgcolor=t.surface(),border_radius=t.RADIUS,
                alignment=ft.Alignment.CENTER)]
        if not state.active_api_key:
            blocks.append(_byok_card(provider.label,on_open_settings))
        if on_open_project is not None:
            blocks.append(ft.Container(ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED,size=17,color=t.muted()),
                ft.Text(s.OPEN_EXISTING_TITLE,size=t.TYPE_BODY,weight=ft.FontWeight.W_500,
                    color=t.on_surface(),expand=True),
                secondary_button(s.OPEN_EXISTING_ACTION,lambda e:on_open_project())],
                spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(t.CARD_PADDING,t.S12,t.CARD_PADDING,t.S12),
                bgcolor=t.surface(),border_radius=t.RADIUS))
        return ft.Column(blocks,spacing=t.S12)

    quality_text=(s.QUALITY_ORIGINAL if state.settings.preserve_original
        else s.QUALITY_COMPATIBLE.format(bitrate=state.settings.fallback_bitrate_kbps))
    metrics=[(s.FIELD_DURATION,format_timecode(info.duration)),(s.FIELD_SIZE,human_size(info.size_bytes)),
        (s.FIELD_FORMAT,info.codec.upper()),(s.FIELD_CHANNELS,str(info.channels)),
        (s.FIELD_SAMPLE_RATE,f"{info.sample_rate:,} Hz"),(s.FIELD_SOURCE_QUALITY,quality_text),
        (s.FIELD_ESTIMATED_CHUNKS,str(estimated_chunk_count(info,state.settings.overlap_seconds,state.settings.safe_chunk_mb))),
        (s.FIELD_STRATEGY,s.STRATEGY_COPY if state.settings.preserve_original else s.STRATEGY_ENCODE)]
    header=ft.Row([ft.Container(ft.Icon(ft.Icons.AUDIO_FILE_OUTLINED,size=22,color=t.muted()),width=44,height=44,
        bgcolor=t.surface_variant(),border=ft.Border.all(1,t.outline()),border_radius=t.R_MD,alignment=ft.Alignment.CENTER),
        ft.Text(s.FIELD_SOURCE_QUALITY,size=t.TYPE_LABEL,color=t.muted(),expand=True)],spacing=t.S16)
    facts=" · ".join(f"{label}: {value}" for label,value in metrics)
    details=ft.Container(ft.Column([
        ft.Row([ft.Icon(ft.Icons.AUDIO_FILE_OUTLINED,size=18,color=t.muted()),
            ft.Column([ft.Text(info.filename,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,
                    color=t.on_surface(),max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(info.path,size=t.TYPE_META,color=t.muted(),max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS)],spacing=1,tight=True,expand=True),
            secondary_button(s.CHANGE_FILE,lambda e:on_choose())],
            spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Text(facts,size=t.TYPE_META,color=t.on_surface_variant())],spacing=t.S8),
        padding=t.CARD_PADDING,bgcolor=t.surface(),border_radius=t.RADIUS)

    quality=ft.RadioGroup(value="original" if state.settings.preserve_original else "compatible",
        on_change=lambda e:on_quality(e.control.value=="original"),
        content=ft.Column([ft.Radio(s.RADIO_ORIGINAL,value="original",label_style=ft.TextStyle(size=t.TYPE_SECONDARY)),
            ft.Radio(s.RADIO_COMPATIBLE,value="compatible",label_style=ft.TextStyle(size=t.TYPE_SECONDARY))],spacing=0))
    preparation=collapsible_card(s.QUALITY_TITLE,ft.Column([note(s.QUALITY_TRANSFER),quality],spacing=t.S16))
    range_card,proceed=_range_card(state,on_range,on_continue)

    return ft.Column([page_title(s.RECORDING_TITLE,s.RECORDING_SUBTITLE,step=1),details,range_card,preparation,
        ft.Row([ft.Text(s.NEXT_RECORDING,size=t.TYPE_LABEL,color=t.muted(),expand=True),
            secondary_button(s.CHANGE_FILE,lambda e:on_choose()),proceed],spacing=t.S12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER)],
        spacing=t.S24)
