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
from components.inputs import syncing
import annotations as an
from providers import provider_choices, provider_info
from theme import note, page_title, panel_title

APPEARANCES = (("light", "Light"), ("dark", "Dark"), ("system", "Match Windows"))
TEXT_SIZES = t.SCALES
LANGUAGES = s.LANGUAGES
# Responsive spans, named once: a field takes half a row, or a third where three sit
# together. They belong to the label wrapper, because that is what a ResponsiveRow lays out.
FULL = {"xs": 12}
HALF = {"xs": 12, "md": 6}
THIRD = {"xs": 12, "md": 4}


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

    def labelled(label: str, control: ft.Control, span: dict | None = None) -> ft.Control:
        """The label above the box, the way an editor's settings do, instead of floating
        into a notch cut out of its border.

        This wraps a control for layout and returns the wrapper, so it must never be what a
        caller keeps hold of — see the note on `field`. `span` is the ResponsiveRow column
        width, and it goes on the wrapper because the wrapper is what the row lays out.
        """
        return ft.Column([ft.Text(label, size=t.TYPE_META, color=t.muted()), control],
                         spacing=t.S4, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                         col=span or FULL)

    def field(value: str, **kwargs) -> ft.TextField:
        """One text input, and nothing around it.

        This used to return the label wrapper while `apply` below read `.value` off whatever
        it returned. A Column has no `.value`, so pressing Save raised an AttributeError on
        the first field it touched, and nothing on this screen could be saved at all — not
        the highlight names, not the reviewer, not the language. Returning the control, and
        wrapping only where the row is built, is what makes that mistake unavailable.
        """
        return syncing(ft.TextField(value=value, dense=True, height=t.FIELD_HEIGHT,
                            border_radius=t.RADIUS, border_color=t.outline(),
                            focused_border_color=t.primary(), border_width=1,
                            focused_border_width=1, color=t.on_surface(),
                            content_padding=ft.Padding(t.S12, t.S4, t.S12, t.S4),
                            text_size=t.TYPE_BODY, **kwargs))

    def choice(value: str, options: tuple[tuple[str, str], ...], **kwargs) -> ft.Dropdown:
        """One select, and nothing around it. Same rule as `field`."""
        return syncing(ft.Dropdown(value=value, dense=True, height=t.FIELD_HEIGHT,
                           border_radius=t.RADIUS, border_color=t.outline(),
                           focused_border_color=t.primary(), text_size=t.TYPE_BODY,
                           options=[ft.DropdownOption(key=k, text=v) for k, v in options],
                           **kwargs))

    provider = syncing(ft.Dropdown(value=active.key, dense=True, height=t.FIELD_HEIGHT,
                           border_radius=t.RADIUS, border_color=t.outline(),
                           focused_border_color=t.primary(), text_size=t.TYPE_BODY,
                           options=[ft.DropdownOption(key=i.key, text=i.label)
                                    for i in provider_choices()]))
    # The key lives here now. It is what a person opens Settings for, and it used to be the
    # one thing Settings did not have.
    key = syncing(ft.TextField(value=state.active_api_key, password=True, can_reveal_password=True,
                       dense=True, height=t.FIELD_HEIGHT, border_radius=t.RADIUS,
                       border_color=t.outline(), focused_border_color=t.primary(),
                       border_width=1, focused_border_width=1, color=t.on_surface(),
                       content_padding=ft.Padding(t.S12, t.S4, t.S12, t.S4),
                       text_size=t.TYPE_BODY))
    language = choice(settings.language, LANGUAGES)
    speakers = field(str(settings.expected_speakers or ""), hint_text=s.SETTINGS_EXPECTED_HINT,
                     disabled=not features.supports_diarization)
    base_url = field(state.compatible_base_url, hint_text=s.SETTINGS_ENDPOINT_URL_HINT)
    model = field(state.compatible_model, hint_text=s.SETTINGS_ENDPOINT_MODEL_HINT)
    appearance = choice(settings.appearance, APPEARANCES)
    text_size = choice(f"{settings.type_scale:g}", TEXT_SIZES)
    rewind = syncing(ft.Switch(label=s.SETTINGS_AUTO_REWIND, value=settings.auto_rewind_enabled,
                               active_color=t.primary()))
    rewind_seconds = field(str(settings.auto_rewind_seconds))
    include = syncing(ft.Switch(label=s.SETTINGS_INCLUDE_PATH,
                                value=settings.include_source_path_json,
                                active_color=t.primary()))
    # Three highlighters, named. A colour with no key is decoration; named here it becomes a
    # code, and the names are printed as a legend in the exported Word file so a colleague
    # who never opened this application can still read the marking.
    names = list(settings.highlight_labels or [])
    highlights = [field(names[i] if i < len(names) else "",
                        hint_text=s.SETTINGS_HIGHLIGHT_SLOT.format(number=slot))
                  for i, slot in enumerate(an.SLOTS)]
    # Who is reviewing. It signs the comments in the Word file and is printed above the
    # transcript, so a document handed to a colleague says whose corrections it carries.
    reviewer = field(settings.reviewer, hint_text=s.SETTINGS_REVIEWER_HINT)
    swatches = ft.ResponsiveRow([
        ft.Row([ft.Container(width=18, height=18, bgcolor=an.colour(slot), border_radius=t.R_SM,
                    border=ft.Border.all(t.HAIRLINE, t.outline())), box],
               spacing=t.S8, vertical_alignment=ft.CrossAxisAlignment.CENTER, col=THIRD)
        for slot, box in zip(an.SLOTS, highlights)], spacing=t.S12, run_spacing=t.S12)

    # Only the OpenAI path cuts the recording into fragments. On every other provider these
    # three numbers configure something that never happens, so they are not shown.
    fragments = active.key == "openai"
    size = field(str(settings.safe_chunk_mb))
    bitrate = field(str(settings.fallback_bitrate_kbps))
    overlap = field(str(settings.overlap_seconds))

    transcription: list[ft.Control] = [
        ft.ResponsiveRow([labelled(s.SETTINGS_PROVIDER, provider, HALF),
                          labelled(active.key_label, key, HALF)],
                         spacing=t.S12, run_spacing=t.S12),
        ft.Text(s.KEY_HELPER, size=t.TYPE_META, color=t.muted()),
        ft.ResponsiveRow([labelled(s.SETTINGS_LANGUAGE, language, HALF),
                          labelled(s.SETTINGS_EXPECTED_SPEAKERS, speakers, HALF)],
                         spacing=t.S12, run_spacing=t.S12)]
    if active.needs_endpoint:
        transcription.append(ft.ResponsiveRow(
            [labelled(s.SETTINGS_ENDPOINT_URL, base_url, HALF),
             labelled(s.SETTINGS_ENDPOINT_MODEL, model, HALF)],
            spacing=t.S12, run_spacing=t.S12))
        transcription.append(ft.Text(s.SETTINGS_ENDPOINT_PRIVACY, size=t.TYPE_META, color=t.muted()))
    transcription.append(note(active.capabilities.summary(),
                              "neutral" if active.capabilities.global_speakers else "warning"))
    transcription.append(ft.Text(active.transfer_note, size=t.TYPE_META, color=t.on_surface_variant()))

    groups: list[ft.Control] = [
        _group(s.SETTINGS_TRANSCRIPTION, ft.Column(transcription, spacing=t.S12)),
        _group(s.SETTINGS_REVIEW, ft.Column([
            ft.ResponsiveRow([labelled(s.SETTINGS_AUTO_REWIND_SECONDS, rewind_seconds, HALF)],
                             spacing=t.S12), rewind,
            ft.Text(s.SETTINGS_AUTO_REWIND_HINT, size=t.TYPE_META, color=t.muted())],
            spacing=t.S12)),
        _group(s.SETTINGS_REVIEWER, ft.Column([
            ft.ResponsiveRow([labelled(s.SETTINGS_REVIEWER, reviewer, HALF)], spacing=t.S12),
            ft.Text(s.SETTINGS_REVIEWER_NOTE, size=t.TYPE_META, color=t.muted())], spacing=t.S8)),
        _group(s.SETTINGS_HIGHLIGHTS, ft.Column([
            swatches,
            ft.Text(s.SETTINGS_HIGHLIGHTS_HINT, size=t.TYPE_META, color=t.muted())],
            spacing=t.S8)),
        _group(s.SETTINGS_INTERFACE, ft.Column([
            ft.ResponsiveRow([labelled(s.SETTINGS_APPEARANCE, appearance, HALF),
                              labelled(s.SETTINGS_TEXT_SIZE, text_size, HALF)],
                             spacing=t.S12, run_spacing=t.S12), include,
            secondary_button(s.SHOW_WELCOME_AGAIN, lambda e: on_reset_welcome())],
            spacing=t.S12))]
    if fragments:
        groups.insert(1, _group(s.SETTINGS_AUDIO, ft.Column([
            ft.ResponsiveRow([labelled(s.SETTINGS_CHUNK_LIMIT, size, THIRD),
                              labelled(s.SETTINGS_BITRATE, bitrate, THIRD),
                              labelled(s.SETTINGS_OVERLAP, overlap, THIRD)],
                             spacing=t.S12, run_spacing=t.S12),
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
