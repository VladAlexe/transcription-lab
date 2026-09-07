from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.buttons import icon_button,primary_button,secondary_button
from components.progress_timeline import progress_timeline
from providers import provider_info
from theme import collapsible_card,note,page_title


def build(state:AppState,on_start:Callable[[str],None],on_cancel:Callable[[],None],elapsed:str="00:00")->ft.Control:
    provider=provider_info(state.settings.provider)
    capabilities=provider.capabilities
    # The key is entered in Settings, beside the provider that decides which key is needed.
    ready=bool(state.active_api_key)
    progress=state.transcription_progress
    operation=state.activity_log[-1] if state.activity_log else s.READY
    total=len(state.generated_chunks)
    # Whole-file providers create no fragments; the counter steps aside instead of breaking.
    current=max(1,int(progress*total)) if state.processing and total else 0
    stage=s.STAGE_FRAGMENT.format(current=current,total=total) if total else s.STAGE_WHOLE_FILE

    done=bool(state.transcript_segments) and not state.processing
    if done:
        # Starting again would discard the transcript underneath without saying so. New
        # project is the way back, and it asks about unsaved work first.
        return ft.Column([page_title(s.TRANSCRIPTION_TITLE,s.TRANSCRIPTION_DONE_SUBTITLE,step=2),
            ft.Container(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE,size=18,color=t.primary()),
                ft.Column([ft.Text(s.TRANSCRIPTION_DONE.format(turns=len(state.transcript_segments)),
                        size=t.TYPE_BODY,weight=ft.FontWeight.W_600,color=t.on_surface()),
                    ft.Text(s.TRANSCRIPTION_DONE_BODY,size=t.TYPE_META,
                        color=t.on_surface_variant())],spacing=1,tight=True,expand=True)],
                spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=t.CARD_PADDING,bgcolor=t.surface(),border_radius=t.RADIUS)],
            spacing=t.S16)

    credentials=ft.Container(ft.Column([
        ft.Row([ft.Column([
                ft.Text(provider.label,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,
                    color=t.on_surface()),
                ft.Text(provider.note,size=t.TYPE_META,color=t.muted(),max_lines=2)],
                spacing=1,tight=True,expand=True),
            primary_button(s.START_TRANSCRIPTION,
                lambda e:on_start(state.active_api_key),ft.Icons.PLAY_ARROW,
                disabled=state.processing or not ready)],
            spacing=t.S16,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        note(capabilities.summary(),"neutral" if capabilities.global_speakers else "warning"),
        ft.Text(s.API_MISSING_START if not ready else s.KEY_HELPER,
            size=t.TYPE_META,color=t.warning() if not ready else t.muted())],spacing=t.S12),
        padding=t.CARD_PADDING,bgcolor=t.surface(),border_radius=t.RADIUS)

    monitor=collapsible_card(s.TRANSCRIPTION_TITLE,ft.Column([
        ft.Row([ft.Column([ft.Text(operation,size=t.TYPE_HEADING,weight=ft.FontWeight.W_600,color=t.on_surface(),max_lines=2),
            ft.Text(s.MODEL_LINE.format(model=provider.model),size=t.TYPE_LABEL,color=t.muted())],spacing=t.S4,expand=True),
            ft.Text(f"{int(progress*100)}%",size=t.TYPE_TITLE,weight=ft.FontWeight.W_600,color=t.on_surface())],
            vertical_alignment=ft.CrossAxisAlignment.START),
        ft.ProgressBar(value=progress,color=t.primary(),bgcolor=t.surface_variant(),height=8,border_radius=t.R_PILL),
        ft.Row([ft.Text(stage,size=t.TYPE_LABEL,color=t.on_surface_variant(),expand=True,max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(s.ELAPSED.format(elapsed=elapsed),size=t.TYPE_LABEL,color=t.muted(),no_wrap=True),
            secondary_button(s.CANCEL,lambda e:on_cancel(),disabled=not state.processing)],
            spacing=t.S16,vertical_alignment=ft.CrossAxisAlignment.CENTER)],spacing=t.S24),
        key="transcription.monitor",summary=f"{int(progress*100)}%")

    stages=collapsible_card(s.PROGRESS_STAGES[2],progress_timeline(progress,bool(state.error_state)),
        key="transcription.stages",summary=stage)
    log="\n".join(state.activity_log[-80:]) or s.ACTIVITY_LOG_EMPTY
    diagnostics=ft.ExpansionTile(ft.Text(s.ACTIVITY_LOG,size=t.TYPE_SUBHEADING,color=t.on_surface()),
        subtitle=ft.Text(s.ACTIVITY_LOG_SUBTITLE,size=t.TYPE_LABEL,color=t.muted()),expanded=False,
        controls=[ft.Container(ft.Column([
            ft.Row([ft.Text(s.DIAGNOSTICS,size=t.TYPE_CAPTION,color=t.muted(),weight=ft.FontWeight.W_600),
                ft.Container(expand=True),
                icon_button(ft.Icons.CONTENT_COPY,s.COPY_DETAILS,
                    on_click=lambda e:e.page.clipboard.set(log))]),
            ft.Text(log,size=t.TYPE_MONO,font_family=t.MONO,selectable=True,color=t.on_surface_variant())],spacing=t.S8),
            padding=t.S16,bgcolor=t.surface_variant(),border_radius=t.R_SM)])

    return ft.Column([page_title(s.TRANSCRIPTION_TITLE,s.TRANSCRIPTION_SUBTITLE,step=2),
        credentials,monitor,stages,diagnostics,
        ft.Text(s.NEXT_TRANSCRIPTION,size=t.TYPE_LABEL,color=t.muted())],
        spacing=t.S24)
