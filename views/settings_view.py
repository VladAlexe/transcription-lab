from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.buttons import primary_button,secondary_button
from providers import feature_state,provider_choices,provider_info
from theme import collapsible_card,note,page_title,section_title

LANGUAGES=(("ro",s.LANGUAGE_RO),("en",s.LANGUAGE_EN))
APPEARANCES=(("light",s.APPEARANCE_LIGHT),("dark",s.APPEARANCE_DARK),("system",s.APPEARANCE_SYSTEM))


def build(state:AppState,on_apply:Callable[...,None],on_choose_tools:Callable[[],None],
          on_reset_welcome:Callable[[],None])->ft.Control:
    settings=state.settings
    active=provider_info(settings.provider); capabilities=active.capabilities
    features=feature_state(capabilities)

    def dropdown(label:str,value:str,options:tuple[tuple[str,str],...],**kwargs)->ft.Dropdown:
        return ft.Dropdown(label=label,value=value,dense=True,border_radius=t.R_SM,border_color=t.outline(),
            options=[ft.DropdownOption(key=key,text=text) for key,text in options],**kwargs)

    def text_field(label:str,value:str,**kwargs)->ft.TextField:
        return ft.TextField(label=label,value=value,dense=True,border_radius=t.R_SM,border_color=t.outline(),
            focused_border_color=t.primary(),color=t.on_surface(),**kwargs)

    appearance=dropdown(s.SETTINGS_APPEARANCE,settings.appearance,APPEARANCES)
    provider=ft.Dropdown(label=s.SETTINGS_PROVIDER,value=active.key,dense=True,border_radius=t.R_SM,
        border_color=t.outline(),col={"xs":12,"md":4},
        options=[ft.DropdownOption(key=item.key,text=item.label) for item in provider_choices()])
    language=dropdown(s.SETTINGS_LANGUAGE,settings.language,LANGUAGES,col={"xs":12,"md":4})
    speakers=text_field(s.SETTINGS_EXPECTED_SPEAKERS,str(settings.expected_speakers or ""),
        hint_text=s.SETTINGS_EXPECTED_HINT,disabled=not features["speaker_naming"],col={"xs":12,"md":4})
    base_url=text_field(s.SETTINGS_ENDPOINT_URL,state.compatible_base_url,hint_text=s.SETTINGS_ENDPOINT_URL_HINT,
        visible=active.needs_endpoint,col={"xs":12,"md":8})
    model=text_field(s.SETTINGS_ENDPOINT_MODEL,state.compatible_model,hint_text=s.SETTINGS_ENDPOINT_MODEL_HINT,
        visible=active.needs_endpoint,col={"xs":12,"md":4})
    size=text_field(s.SETTINGS_CHUNK_LIMIT,str(settings.safe_chunk_mb),col={"xs":12,"md":4})
    bitrate=text_field(s.SETTINGS_BITRATE,str(settings.fallback_bitrate_kbps),col={"xs":12,"md":4})
    overlap=text_field(s.SETTINGS_OVERLAP,str(settings.overlap_seconds),col={"xs":12,"md":4})
    rewind=ft.Switch(s.SETTINGS_AUTO_REWIND,value=settings.auto_rewind_enabled)
    rewind_seconds=text_field(s.SETTINGS_AUTO_REWIND_SECONDS,str(settings.auto_rewind_seconds),
        col={"xs":12,"md":4})
    include=ft.Switch(s.SETTINGS_INCLUDE_PATH,value=settings.include_source_path_json)
    diagnostic=ft.Switch(s.SETTINGS_DIAGNOSTIC,value=settings.diagnostic_logging)

    hint=(s.SETTINGS_SPEAKERS_BOUND if active.key=="gladia"
          else s.SETTINGS_SPEAKERS_ADVISORY if features["speaker_naming"] else s.SETTINGS_SPEAKERS_UNUSED)
    tools=state.media_tools
    tool_status=f"{tools.source_type} · {tools.version}" if tools.is_valid else s.SETTINGS_FFMPEG_UNAVAILABLE

    interface_card=collapsible_card(s.SETTINGS_INTERFACE,ft.Column([appearance,
        secondary_button(s.SHOW_WELCOME_AGAIN,lambda e:on_reset_welcome())],spacing=t.S16))
    transcription_card=collapsible_card(s.SETTINGS_TRANSCRIPTION,ft.Column([
        ft.ResponsiveRow([provider,language,speakers],spacing=t.S16,run_spacing=t.S12),
        ft.ResponsiveRow([base_url,model],spacing=t.S16,run_spacing=t.S12,visible=active.needs_endpoint),
        ft.Text(s.SETTINGS_ENDPOINT_PRIVACY,size=t.TYPE_LABEL,color=t.muted(),visible=active.needs_endpoint),
        note(capabilities.summary(),"success" if capabilities.global_speakers else "warning"),
        ft.Text(active.transfer_note,size=t.TYPE_LABEL,color=t.on_surface_variant()),
        ft.Text(hint,size=t.TYPE_LABEL,color=t.muted())],spacing=t.S16))
    review_card=collapsible_card(s.SETTINGS_REVIEW,ft.Column([
        rewind,ft.ResponsiveRow([rewind_seconds],spacing=t.S16),
        ft.Text(s.SETTINGS_AUTO_REWIND_HINT,size=t.TYPE_LABEL,color=t.muted())],spacing=t.S12),
        key="settings.review")
    audio_card=collapsible_card(s.SETTINGS_AUDIO,ft.Column([
        ft.ResponsiveRow([size,bitrate,overlap],spacing=t.S16,run_spacing=t.S12),include,diagnostic],spacing=t.S16),
        s.SETTINGS_AUDIO_NOTE)
    ffmpeg_card=collapsible_card(s.SETTINGS_FFMPEG,ft.Column([
        ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE if tools.is_valid else ft.Icons.ERROR_OUTLINE,
            color=t.success() if tools.is_valid else t.error()),
            ft.Text(tool_status,size=t.TYPE_LABEL,color=t.on_surface_variant(),max_lines=2,expand=True),
            secondary_button(s.CHOOSE_FOLDER,lambda e:on_choose_tools())],spacing=t.S16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Text(tools.ffmpeg_path or s.SETTINGS_FFMPEG_NO_PATH,size=t.TYPE_MONO,font_family="Consolas",
            selectable=True,color=t.muted())],spacing=t.S12))

    def apply(event:ft.Event)->None:
        on_apply(appearance.value,float(size.value or 23),int(bitrate.value or 48),float(overlap.value or 0),
                 include.value,diagnostic.value,provider.value,language.value,speakers.value or "0",
                 base_url.value or "",model.value or "",rewind.value,rewind_seconds.value or "1.5")

    return ft.Column([page_title(s.SETTINGS_TITLE,s.SETTINGS_SUBTITLE),interface_card,transcription_card,review_card,audio_card,
        ffmpeg_card,ft.Row([primary_button(s.SETTINGS_SAVE,apply,ft.Icons.CHECK)],
            alignment=ft.MainAxisAlignment.END)],
        spacing=t.S24)
