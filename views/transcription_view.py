from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.buttons import icon_button,primary_button,secondary_button
from components.progress_timeline import progress_timeline
from providers import provider_info
from theme import card,collapsible_card,note,page_title,section_title


def build(state:AppState,on_start:Callable[[str],None],on_cancel:Callable[[],None],elapsed:str="00:00")->ft.Control:
    provider=provider_info(state.settings.provider)
    capabilities=provider.capabilities
    key=ft.TextField(label=provider.key_label,password=True,can_reveal_password=True,value=state.active_api_key,
        dense=True,height=46,border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
        color=t.on_surface(),expand=True,helper=ft.Text(s.KEY_HELPER,size=t.TYPE_CAPTION,color=t.muted()))
    progress=state.transcription_progress
    operation=state.activity_log[-1] if state.activity_log else s.READY
    total=len(state.generated_chunks)
    # Whole-file providers create no fragments; the counter steps aside instead of breaking.
    current=max(1,int(progress*total)) if state.processing and total else 0
    stage=s.STAGE_FRAGMENT.format(current=current,total=total) if total else s.STAGE_WHOLE_FILE

    credentials=collapsible_card(provider.label,ft.Column([
        # NOT a wrapped Row: Flet renders wrap=True as a Flutter Wrap, which cannot lay out an
        # expanding child — the key field would collapse to zero width and disappear. A plain Row
        # with one expanding child cannot overflow either, because that child absorbs the slack.
        ft.Row([key,primary_button(s.START_TRANSCRIPTION,lambda e:on_start(key.value or ""),ft.Icons.PLAY_ARROW,
            disabled=state.processing)],spacing=t.S16,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        note(capabilities.summary(),"success" if capabilities.global_speakers else "warning"),
        ft.Text(provider.note,size=t.TYPE_LABEL,color=t.muted())],spacing=t.S16),
        key="transcription.provider",
        summary=s.API_CONFIGURED if state.active_api_key else s.API_MISSING)

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
            ft.Text(log,size=t.TYPE_MONO,font_family="Consolas",selectable=True,color=t.on_surface_variant())],spacing=t.S8),
            padding=t.S16,bgcolor=t.surface_variant(),border_radius=t.R_SM)])

    return ft.Column([page_title(s.TRANSCRIPTION_TITLE,s.TRANSCRIPTION_SUBTITLE,step=2),
        credentials,monitor,stages,diagnostics,
        ft.Text(s.NEXT_TRANSCRIPTION,size=t.TYPE_LABEL,color=t.muted())],
        spacing=t.S24)
