"""Settings: everything that configures a run, on one surface.

It used to be five collapsed cards of small controls, two of which did nothing at all —
`diagnostic_logging` and `retain_review_audio` were written when you pressed Save and read
by nobody. The fragmenting numbers were always visible even though only the OpenAI path
fragments anything, so on the default provider three of the fields were inert.

And the API key, the one thing a person opens Settings to enter, was on a different screen.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.buttons import primary_button, secondary_button
import annotations as an
from providers import provider_choices, provider_info
from theme import note, page_title, panel_title

APPEARANCES = (("light", "Light"), ("dark", "Dark"), ("system", "Match Windows"))
TEXT_SIZES = t.SCALES
LANGUAGES = s.LANGUAGES


def _group(title: str, body: ft.Control) -> ft.Control:
    """A heading and its fields. No card, no chevron, no border — the screen is one surface
    and a group is a heading with air above it."""
    return ft.Column([panel_title(title), body], spacing=t.S8, tight=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


def build(state: AppState, on_apply: Callable[..., None], on_choose_tools: Callable[[], None],
          on_reset_welcome: Callable[[], None],
          on_key: Callable[[str], None] | None = None) -> ft.Control:
    settings = state.settings
    active = provider_info(settings.provider)
    features = active.capabilities
    tools = state.media_tools

    def labelled(label: str, control: ft.Control, **col) -> ft.Control:
        """The label sits above the box, the way an editor's settings do, instead of
        floating into a notch cut out of its border."""
        return ft.Column([ft.Text(label, size=t.TYPE_META, color=t.muted()), control],
                         spacing=t.S4, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH, **col)

    def field(label: str, value: str, **kwargs) -> ft.Control:
        col = {"col": kwargs.pop("col")} if "col" in kwargs else {}
        return labelled(label, ft.TextField(value=value, dense=True, height=t.FIELD_HEIGHT,
                            border_radius=t.RADIUS, border_color=t.outline(),
                            focused_border_color=t.primary(), border_width=1,
                            focused_border_width=1, color=t.on_surface(),
                            content_padding=ft.Padding(t.S12, t.S4, t.S12, t.S4),
                            text_size=t.TYPE_BODY, **kwargs), **col)

    def choice(label: str, value: str, options: tuple[tuple[str, str], ...], **kwargs) -> ft.Control:
        col = {"col": kwargs.pop("col")} if "col" in kwargs else {}
        return labelled(label, ft.Dropdown(value=value, dense=True, height=t.FIELD_HEIGHT,
                           border_radius=t.RADIUS, border_color=t.outline(),
                           focused_border_color=t.primary(), text_size=t.TYPE_BODY,
                           options=[ft.DropdownOption(key=k, text=v) for k, v in options],
                           **kwargs), **col)

    provider = ft.Dropdown(value=active.key, dense=True, height=t.FIELD_HEIGHT,
                           border_radius=t.RADIUS, border_color=t.outline(),
                           focused_border_color=t.primary(), text_size=t.TYPE_BODY,
                           options=[ft.DropdownOption(key=i.key, text=i.label)
                                    for i in provider_choices()])
    # The key lives here now. It is what a person opens Settings for, and it used to be the
    # one thing Settings did not have.
    key = ft.TextField(value=state.active_api_key, password=True, can_reveal_password=True,
                       dense=True, height=t.FIELD_HEIGHT, border_radius=t.RADIUS,
                       border_color=t.outline(), focused_border_color=t.primary(),
                       border_width=1, focused_border_width=1, color=t.on_surface(),
                       content_padding=ft.Padding(t.S12, t.S4, t.S12, t.S4),
                       text_size=t.TYPE_BODY)
    language = choice(s.SETTINGS_LANGUAGE, settings.language, LANGUAGES, col={"xs": 12, "md": 6})
    speakers = field(s.SETTINGS_EXPECTED_SPEAKERS, str(settings.expected_speakers or ""),
                     hint_text=s.SETTINGS_EXPECTED_HINT,
                     disabled=not features.supports_diarization, col={"xs": 12, "md": 6})
    base_url = field(s.SETTINGS_ENDPOINT_URL, state.compatible_base_url,
                     hint_text=s.SETTINGS_ENDPOINT_URL_HINT, col={"xs": 12, "md": 6})
    model = field(s.SETTINGS_ENDPOINT_MODEL, state.compatible_model,
                  hint_text=s.SETTINGS_ENDPOINT_MODEL_HINT, col={"xs": 12, "md": 6})
    appearance = choice(s.SETTINGS_APPEARANCE, settings.appearance, APPEARANCES,
                        col={"xs": 12, "md": 6})
    text_size = choice(s.SETTINGS_TEXT_SIZE, f"{settings.type_scale:g}", TEXT_SIZES,
                       col={"xs": 12, "md": 6})
    rewind = ft.Switch(label=s.SETTINGS_AUTO_REWIND, value=settings.auto_rewind_enabled,
                       active_color=t.primary())
    rewind_seconds = field(s.SETTINGS_AUTO_REWIND_SECONDS, str(settings.auto_rewind_seconds),
                           col={"xs": 12, "md": 6})
    include = ft.Switch(label=s.SETTINGS_INCLUDE_PATH, value=settings.include_source_path_json,
                        active_color=t.primary())
    # Three highlighters, named. A colour with no key is decoration; named here it becomes a
    # code, and the names are printed as a legend in the exported Word file so a colleague
    # who never opened this application can still read the marking.
    names = list(settings.highlight_labels or [])
    highlights = [ft.TextField(value=names[i] if i < len(names) else "", dense=True,
                      height=t.FIELD_HEIGHT, border_radius=t.RADIUS, border_color=t.outline(),
                      focused_border_color=t.primary(), border_width=1, focused_border_width=1,
                      color=t.on_surface(), text_size=t.TYPE_BODY,
                      hint_text=s.SETTINGS_HIGHLIGHT_SLOT.format(number=slot),
                      content_padding=ft.Padding(t.S12, t.S4, t.S12, t.S4))
                  for i, slot in enumerate(an.SLOTS)]
    # Who is reviewing. It signs the comments in the Word file and is printed above the
    # transcript, so a document handed to a colleague says whose corrections it carries.
    reviewer = ft.TextField(value=settings.reviewer, dense=True, height=t.FIELD_HEIGHT,
                            border_radius=t.RADIUS, border_color=t.outline(),
                            focused_border_color=t.primary(), border_width=1,
                            focused_border_width=1, color=t.on_surface(),
                            text_size=t.TYPE_BODY, hint_text=s.SETTINGS_REVIEWER_HINT,
                            content_padding=ft.Padding(t.S12, t.S4, t.S12, t.S4))
    swatches = ft.ResponsiveRow([
        ft.Row([ft.Container(width=18, height=18, bgcolor=an.colour(slot), border_radius=t.R_SM,
                    border=ft.Border.all(t.HAIRLINE, t.outline())), box],
               spacing=t.S8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               col={"xs": 12, "md": 4})
        for slot, box in zip(an.SLOTS, highlights)], spacing=t.S12, run_spacing=t.S12)

    # Only the OpenAI path cuts the recording into fragments. On every other provider these
    # three numbers configure something that never happens, so they are not shown.
    fragments = active.key == "openai"
    size = field(s.SETTINGS_CHUNK_LIMIT, str(settings.safe_chunk_mb), col={"xs": 12, "md": 4})
    bitrate = field(s.SETTINGS_BITRATE, str(settings.fallback_bitrate_kbps), col={"xs": 12, "md": 4})
    overlap = field(s.SETTINGS_OVERLAP, str(settings.overlap_seconds), col={"xs": 12, "md": 4})

    transcription: list[ft.Control] = [
        ft.ResponsiveRow([labelled(s.SETTINGS_PROVIDER, provider, col={"xs": 12, "md": 6}),
                          labelled(active.key_label, key, col={"xs": 12, "md": 6})],
                         spacing=t.S12, run_spacing=t.S12),
        ft.Text(s.KEY_HELPER, size=t.TYPE_META, color=t.muted()),
        ft.ResponsiveRow([language, speakers], spacing=t.S12, run_spacing=t.S12)]
    if active.needs_endpoint:
        transcription.append(ft.ResponsiveRow([base_url, model], spacing=t.S12, run_spacing=t.S12))
        transcription.append(ft.Text(s.SETTINGS_ENDPOINT_PRIVACY, size=t.TYPE_META, color=t.muted()))
    transcription.append(note(active.capabilities.summary(),
                              "neutral" if active.capabilities.global_speakers else "warning"))
    transcription.append(ft.Text(active.transfer_note, size=t.TYPE_META, color=t.on_surface_variant()))

    groups: list[ft.Control] = [
        _group(s.SETTINGS_TRANSCRIPTION, ft.Column(transcription, spacing=t.S12)),
        _group(s.SETTINGS_REVIEW, ft.Column([
            ft.ResponsiveRow([rewind_seconds], spacing=t.S12), rewind,
            ft.Text(s.SETTINGS_AUTO_REWIND_HINT, size=t.TYPE_META, color=t.muted())],
            spacing=t.S12)),
        _group(s.SETTINGS_REVIEWER, ft.Column([
            ft.ResponsiveRow([labelled(s.SETTINGS_REVIEWER, reviewer, col={"xs": 12, "md": 6})],
                             spacing=t.S12),
            ft.Text(s.SETTINGS_REVIEWER_NOTE, size=t.TYPE_META, color=t.muted())], spacing=t.S8)),
        _group(s.SETTINGS_HIGHLIGHTS, ft.Column([
            swatches,
            ft.Text(s.SETTINGS_HIGHLIGHTS_HINT, size=t.TYPE_META, color=t.muted())],
            spacing=t.S8)),
        _group(s.SETTINGS_INTERFACE, ft.Column([
            ft.ResponsiveRow([appearance, text_size], spacing=t.S12, run_spacing=t.S12), include,
            secondary_button(s.SHOW_WELCOME_AGAIN, lambda e: on_reset_welcome())],
            spacing=t.S12))]
    if fragments:
        groups.insert(1, _group(s.SETTINGS_AUDIO, ft.Column([
            ft.ResponsiveRow([size, bitrate, overlap], spacing=t.S12, run_spacing=t.S12),
            ft.Text(s.SETTINGS_AUDIO_NOTE, size=t.TYPE_META, color=t.muted())], spacing=t.S12)))

    status = f"{tools.source_type} · {tools.version}" if tools.is_valid else s.SETTINGS_FFMPEG_UNAVAILABLE
    groups.append(_group(s.SETTINGS_FFMPEG, ft.Row([
        ft.Icon(ft.Icons.CHECK_CIRCLE if tools.is_valid else ft.Icons.ERROR_OUTLINE, size=17,
                color=t.primary() if tools.is_valid else t.error()),
        ft.Text(status, size=t.TYPE_META, color=t.on_surface_variant(), max_lines=2, expand=True),
        secondary_button(s.CHOOSE_FOLDER, lambda e: on_choose_tools())],
        spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.CENTER)))

    def apply(event: ft.Event) -> None:
        if on_key is not None:
            on_key(key.value or "")
        on_apply(appearance.value, float(size.value or 23), int(bitrate.value or 48),
                 float(overlap.value or 0), include.value, False, provider.value,
                 language.value, speakers.value or "0", base_url.value or "",
                 model.value or "", rewind.value, rewind_seconds.value or "1.5",
                 text_size.value or "1.0", [(box.value or "").strip() for box in highlights],
                 reviewer.value or "")

    body = ft.Column(groups, spacing=t.S24, tight=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    return ft.Column([
        page_title(s.SETTINGS_TITLE, s.SETTINGS_SUBTITLE),
        ft.Container(body, padding=t.CARD_PADDING, bgcolor=t.surface(), border_radius=t.RADIUS),
        ft.Row([primary_button(s.SETTINGS_SAVE, apply, ft.Icons.CHECK)],
               alignment=ft.MainAxisAlignment.END)], spacing=t.S16)
