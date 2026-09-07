"""Material 3 theme plus the shared surface primitives, both built from design tokens."""
from __future__ import annotations

import flet as ft

import design_tokens as t
import strings as s
from components.buttons import icon_button


def application_theme(dark: bool = False) -> ft.Theme:
    palette = t.scheme(dark)
    # `surface_variant` was dropped from Flet's ColorScheme; the design role still exists and is
    # applied directly by the controls that need it (see design_tokens.surface_variant).
    colors = ft.ColorScheme(
        primary=palette["primary"], on_primary=palette["on_primary"],
        primary_container=palette["primary_soft"], on_primary_container=palette["primary"],
        surface=palette["surface"], on_surface=palette["on_surface"],
        on_surface_variant=palette["on_surface_variant"],
        outline=palette["outline"], outline_variant=palette["outline_strong"],
        error=palette["error"], on_error=palette["on_primary"])
    # An editor's chrome: a hairline scrollbar with no track, compact density, and no
    # divider colour loud enough to read as a border.
    scrollbar = ft.ScrollbarTheme(thickness=6, radius=3, interactive=True,
                                  thumb_visibility=False, track_visibility=False,
                                  thumb_color=palette["scrollbar"], track_color=ft.Colors.TRANSPARENT,
                                  track_border_color=ft.Colors.TRANSPARENT,
                                  cross_axis_margin=2, main_axis_margin=2, min_thumb_length=32)
    return ft.Theme(color_scheme_seed=t.SEED, color_scheme=colors, use_material3=True,
                    font_family="Segoe UI Variable", scaffold_bgcolor=palette["background"],
                    divider_color=palette["outline"], scrollbar_theme=scrollbar,
                    visual_density=ft.VisualDensity.COMPACT)


def elevation() -> ft.BoxShadow:
    """One soft shadow, used by every card so depth stays consistent."""
    return ft.BoxShadow(blur_radius=18, spread_radius=0, color=t.shadow(), offset=ft.Offset(0, 2))


def card(content: ft.Control, padding: int = t.CARD_PADDING, expand: bool | int | None = None,
         variant: bool = False) -> ft.Container:
    """A calm, lifted panel: the only container style the screens use."""
    # No outline. A card is a lighter surface on a darker ground; that is the whole trick,
    # and it is why an interface with three tones needs a twentieth of the lines.
    return ft.Container(content=content, padding=padding, expand=expand,
                        bgcolor=t.surface_variant() if variant else t.surface(),
                        border_radius=t.RADIUS, shadow=None)


# Collapsed sections are remembered for the session, keyed by card. A view preference does not
# belong in application state, but it should survive a re-render while the researcher works.
COLLAPSED: dict[str, bool] = {}


def collapsible_card(title: str, body: ft.Control, subtitle: str = "", padding: int = t.CARD_PADDING,
                     collapsed: bool = False, key: str | None = None,
                     summary: str = "") -> ft.Container:
    """A card whose body can be minimised by the chevron in its header.

    Collapsed, it shows only the header, the chevron and a one-line summary. The open/closed
    state is remembered for the session so a re-render does not reopen everything.
    """
    slot = key or title
    collapsed = COLLAPSED.get(slot, collapsed)
    content = ft.Container(body, visible=not collapsed, padding=ft.Padding(0, t.S16, 0, 0))
    chevron = icon_button(ft.Icons.EXPAND_MORE if collapsed else ft.Icons.EXPAND_LESS,
                          s.EXPAND_SECTION if collapsed else s.COLLAPSE_SECTION, None)
    folded = ft.Text(summary, size=t.TYPE_LABEL, color=t.muted(),
                     visible=collapsed and bool(summary), no_wrap=True)

    def toggle(event: ft.Event) -> None:
        content.visible = not content.visible
        COLLAPSED[slot] = not content.visible
        folded.visible = not content.visible and bool(summary)
        chevron.icon = ft.Icons.EXPAND_LESS if content.visible else ft.Icons.EXPAND_MORE
        chevron.tooltip = s.COLLAPSE_SECTION if content.visible else s.EXPAND_SECTION
        try:
            content.update(); chevron.update(); folded.update()
        except Exception:
            pass

    chevron.on_click = toggle
    header = ft.Row([ft.Container(section_title(title, subtitle), expand=True), folded, chevron],
                    spacing=t.S12, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    return ft.Container(ft.Column([header, content], spacing=0), padding=padding,
                        bgcolor=t.surface(), border_radius=t.RADIUS)


def panel_title(text: str, trailing: ft.Control | None = None) -> ft.Control:
    """A panel header the way an editor writes one: small, upper-case, letter-spaced.

    A nineteen-pixel bold heading on a three-hundred-pixel panel is a poster. This says the
    same thing in a third of the height and stops competing with the content underneath.
    """
    row: list[ft.Control] = [ft.Text(text.upper(), size=t.TYPE_META,
                                     weight=ft.FontWeight.W_600, color=t.muted(), no_wrap=True,
                                     style=ft.TextStyle(letter_spacing=.6)),
                             ft.Container(expand=True)]
    if trailing is not None:
        row.append(trailing)
    return ft.Row(row, spacing=t.S8, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def section_title(text: str, subtitle: str = "") -> ft.Control:
    parts: list[ft.Control] = [ft.Text(text, size=t.TYPE_HEADING, weight=ft.FontWeight.W_600, color=t.on_surface())]
    if subtitle:
        parts.append(ft.Text(subtitle, size=t.TYPE_LABEL, color=t.on_surface_variant()))
    return ft.Column(parts, spacing=t.S4)


def page_title(text: str, subtitle: str = "", step: int | None = None, total: int = 4) -> ft.Control:
    """Screen heading. The optional eyebrow tells the researcher where they are in the flow."""
    parts: list[ft.Control] = []
    if step is not None:
        parts.append(ft.Text(s.STEP_EYEBROW.format(current=step, total=total),
                             size=t.TYPE_CAPTION, weight=ft.FontWeight.W_600, color=t.primary()))
    parts.append(ft.Text(text, size=t.TYPE_DISPLAY, weight=ft.FontWeight.W_600, color=t.on_surface()))
    if subtitle:
        parts.append(ft.Text(subtitle, size=t.TYPE_SUBTITLE, color=t.muted()))
    return ft.Column(parts, spacing=t.S8, tight=True)


def field_label(text: str) -> ft.Control:
    return ft.Text(text.upper(), size=t.TYPE_CAPTION, weight=ft.FontWeight.W_600,
                   color=t.muted(), spans=None)


def timestamp(text: str, size: float = t.TYPE_MONO) -> ft.Control:
    """Timestamps stay deliberately quiet: monospaced, muted, never competing with speech."""
    return ft.Text(text, size=size, color=t.muted(), font_family=t.MONO)


def note(text: str, tone: str = "neutral") -> ft.Control:
    palette = {"neutral": t.on_surface_variant(), "success": t.success(),
               "warning": t.warning(), "error": t.error()}
    icons = {"neutral": ft.Icons.INFO_OUTLINE, "success": ft.Icons.CHECK_CIRCLE,
             "warning": ft.Icons.WARNING_AMBER, "error": ft.Icons.ERROR_OUTLINE}
    color = palette.get(tone, t.on_surface_variant())
    # The icon carries the tone; the sentence stays in reading ink. A whole line of amber
    # competes with the screen's one accent and makes an ordinary notice feel like an alarm.
    return ft.Container(
        ft.Row([ft.Icon(icons.get(tone, ft.Icons.INFO_OUTLINE), size=16, color=color),
                ft.Text(text, size=t.TYPE_LABEL, color=t.on_surface_variant(), expand=True)], spacing=t.S8),
        padding=ft.Padding(t.S12, t.S8, t.S12, t.S8), bgcolor=t.surface_variant(),
        border_radius=t.RADIUS)


def speaker_chip(index: int, label: str, compact: bool = False) -> ft.Control:
    """A coloured dot plus the speaker's display name, used everywhere a speaker appears."""
    color = t.speaker_color(index)
    return ft.Row([
        ft.Container(width=9, height=9, bgcolor=color, border_radius=t.R_PILL),
        ft.Text(label, size=t.TYPE_LABEL if compact else t.TYPE_SUBHEADING,
                weight=ft.FontWeight.W_600, color=t.on_surface())], spacing=t.S8, tight=True)
