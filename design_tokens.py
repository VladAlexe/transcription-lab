"""The single source of truth for spacing, type, radius, and colour.

Nothing in `views/` or `components/` defines a colour of its own: every surface, border,
and label reads a semantic role from here, so light and dark stay consistent by
construction. `set_dark()` is called once per render, before any view is built.
"""
from __future__ import annotations

# ── Spacing scale ─────────────────────────────────────────────────────────────
SPACING = (4, 8, 12, 16, 24, 32)
S4, S8, S12, S16, S24, S32 = SPACING

# ── Type scale ────────────────────────────────────────────────────────────────
# One ladder, five rungs the eye can actually tell apart. The screen title is the largest
# thing on any screen but never dwarfs it: 26 over a 15px body is a clear step, not a shout.
TYPE_DISPLAY = 26            # screen H1, semibold
TYPE_SUBTITLE = 14           # the line under an H1, muted
TYPE_TITLE = 19              # dialog and overlay headers
TYPE_HEADING = 15            # section titles, medium
TYPE_SUBHEADING = 14
TYPE_BODY = 15               # spoken text, at LINE_HEIGHT
TYPE_SECONDARY = 13
TYPE_LABEL = 12
TYPE_CAPTION = 11
TYPE_MONO = 11               # timestamps, muted

# ── Surfaces ──────────────────────────────────────────────────────────────────
# One card style everywhere: same radius, same hairline, same inner padding. A screen that
# mixes 16 and 24 inside otherwise identical panels reads as two designs stacked.
CARD_PADDING = 20
HAIRLINE = 1

# ── Overlays ──────────────────────────────────────────────────────────────────
# The root rule: a transient tool floats above the content, it never joins the page flow.
# Nothing behind it moves, and nothing it contains reaches full width or full height.
OVERLAY_MAX_WIDTH = 520      # a floating tool never grows past this
OVERLAY_MIN_WIDTH = 320      # below this the tool would be unusable, so it stops shrinking
OVERLAY_INSET = 24           # from the right edge of the content area
OVERLAY_TOP = 16             # it drops just under the top bar, clear of the screen title
OVERLAY_PADDING = 20
OVERLAY_RADIUS = 14
FLOATING_LIST_HEIGHT = 440   # a floating list needs a height; a docked pane takes the column
FLOATING_PANEL_HEIGHT = 520  # the open turn, when the window cannot give it a column

# ── Corner radius ─────────────────────────────────────────────────────────────
R_SM = 8
R_MD = 12
R_LG = 16
R_PILL = 999

# ── Layout ────────────────────────────────────────────────────────────────────
TOP_BAR_HEIGHT = 64
NAV_WIDTH = 220              # fixed while expanded
NAV_MINIMISED = 72           # the researcher can minimise the rail to icons

# ── Sidebar rhythm ────────────────────────────────────────────────────────────
WORDMARK_TOP = 20            # breathing room above the mark; nothing clipped
WORDMARK_LEFT = 20           # lines the mark up with the nav icons below it
WORDMARK_GAP = 10            # between the mark and the name
NAV_ITEM_HEIGHT = 44
NAV_ITEM_GAP = 12            # vertical gap between destinations
NAV_PILL_INSET = 8           # the selected pill never touches the rail edges
NAV_PILL_RADIUS = 10
NAV_ITEM_PADDING = 12        # inside the pill; icon lands at INSET + PADDING = 20

# ── Top bar rhythm ────────────────────────────────────────────────────────────
TOP_BAR_LEFT = 32            # same left padding as the content column below
CHIP_GAP = 20                # between the API chip and the icon cluster
ICON_BUTTON = 40             # square hit area
ICON_BUTTON_GAP = 4
CONTROLS_GAP = 24            # before the divider and the OS window controls

# ── Empty state ───────────────────────────────────────────────────────────────
EMPTY_STATE_MAX = 560        # capped, and never wider than the column it sits in
EMPTY_STATE_PADDING = 48
EMPTY_STATE_RHYTHM = 16
EMPTY_STATE_ICON = 40
INSPECTOR_WIDTH = 340        # fixed
WORKSPACE_MIN = 580          # the workspace never shares the row below this
# 220 + 580 + 340. Under this the inspector is a slide-over, not a third column.
INSPECTOR_BREAKPOINT = NAV_WIDTH + WORKSPACE_MIN + INSPECTOR_WIDTH
MAX_CONTENT = 960            # hard cap on the inner content column
CONTENT_GUTTER = 32          # equal padding either side of that column
# A document screen is capped at a readable column. A workbench is not a document: the
# review screen is three panes side by side, so it takes the whole workspace and caps the
# spoken text instead (TRANSCRIPT_MEASURE below). Capping the panes wastes the desk.
WORKBENCH_GUTTER = 24
WORKBENCH_BAR_HEIGHT = 64    # title, counts and actions on one line, in place of a header block
SELECTION_RULE = 3           # the sage edge that marks the turn being edited
# The Speakers screen is three columns: the speaker list, the transcript, the open turn.
# The list gets a real width rather than a share of the column — as a proportion it shrank
# to about ninety pixels of name field on an ordinary window, which is unusable. The
# transcript keeps a floor, and below the point where both fit the list floats instead.
IDENTITY_PANE_WIDTH = 280
TRANSCRIPT_MIN_COLUMN = 300
IDENTITY_PANEL_SHARE = 3     # kept for the collapsed-rail arithmetic
TRANSCRIPT_SHARE = 6
# ── Reading ───────────────────────────────────────────────────────────────────
TRANSCRIPT_MEASURE = 640     # max width of the spoken text itself
TURN_GAP = 10                # air between turns, in place of a border on every row
LINE_HEIGHT = 1.4
TURN_PADDING = 8             # inside a turn, top and bottom
# A turn in the list is a meta line and one line of speech: the whole turn is one click away
# in the inspector, so the list is for finding your place, not for reading in.
TRANSCRIPT_ROW_HEIGHT = 64   # uniform rows keep the sticky speaker header exact (gap included)
TIMESTAMP_GUTTER = 56        # "00:12:04" at the mono size, with air after it
CHECK_RULE = 3               # the sage bar marking a turn as reviewed
SELECTION_TINT = True        # selection is a fill, not an edge — the edge belongs to checked
FIELD_HEIGHT = 44            # one height for every text field and dropdown
FIELD_HEIGHT_DENSE = 40      # inside overlays and the inspector, where space is tight
PLAYER_BAR_HEIGHT = 56       # a slim footer, not a card competing with the text
COLLAPSED_PANEL_WIDTH = 48

# ── Brand ─────────────────────────────────────────────────────────────────────
# Sampled from assets/icon.png: the logo is charcoal ink with a sage accent.
BRAND_INK = "#282D31"
BRAND_SAGE = "#758D83"
# The mark's sage is too light to carry white label text (3.4:1). The interface accent is a
# darkened sage that reaches 4.7:1, so buttons stay legible while reading as the same colour.
SEED = "#5F7A68"

# ── Palettes. Roles, not raw names: every entry below has a dark counterpart. ──
_LIGHT = {
    "background": "#F5F4F1",          # warm light grey, not blue-white
    "surface": "#FFFFFF",
    "surface_variant": "#EFEEEA",
    "surface_raised": "#FFFFFF",
    "on_surface": BRAND_INK,
    "on_surface_variant": "#5C635F",
    "muted": "#7C837F",
    "outline": "#E2E0DA",
    "outline_strong": "#C9C7C0",
    "primary": "#5F7A68",
    "on_primary": "#FFFFFF",
    "primary_soft": "#E9EFEA",
    "success": "#2E7D64",
    "warning": "#9A6B1F",
    "error": "#B3403A",
    "shadow": "#1B211E14",            # 8% ink: depth you feel rather than see
}

_DARK = {
    "background": "#14171A",
    "surface": "#1B1F22",
    "surface_variant": "#22272A",
    "surface_raised": "#252A2E",
    "on_surface": "#ECEAE5",
    "on_surface_variant": "#A6ADA8",
    "muted": "#7E8783",
    "outline": "#2C3236",
    "outline_strong": "#3C4348",
    "primary": "#A8BCAE",             # lightened sage; label ink sits on it at 8.2:1
    "on_primary": "#1B211E",
    "primary_soft": "#232C26",
    "success": "#6FC7A2",
    "warning": "#D9A45C",
    "error": "#E08078",
    "shadow": "#00000040",
}

# Speaker chips: eight hues that stay distinguishable beside the sage accent without
# competing with it. Muted on purpose — these mark people, not states.
_SPEAKER_LIGHT = ("#5F7A68", "#8A6A3B", "#4C6B84", "#7A5478", "#96603C", "#3F7370", "#6B6F92", "#7C6A45")
_SPEAKER_DARK = ("#A8BCAE", "#D2AC78", "#8FB4D0", "#C69BC2", "#DCA079", "#79BDB8", "#A9ADD8", "#C7B489")

_DARK_ACTIVE = False


def set_dark(active: bool) -> None:
    global _DARK_ACTIVE
    _DARK_ACTIVE = active


def is_dark() -> bool:
    return _DARK_ACTIVE


def _role(name: str) -> str:
    return (_DARK if _DARK_ACTIVE else _LIGHT)[name]


def background() -> str: return _role("background")
def surface() -> str: return _role("surface")
def surface_variant() -> str: return _role("surface_variant")
def surface_raised() -> str: return _role("surface_raised")
def on_surface() -> str: return _role("on_surface")
def on_surface_variant() -> str: return _role("on_surface_variant")
def muted() -> str: return _role("muted")
def outline() -> str: return _role("outline")
def outline_strong() -> str: return _role("outline_strong")
def primary() -> str: return _role("primary")
def on_primary() -> str: return _role("on_primary")
def primary_soft() -> str: return _role("primary_soft")
def success() -> str: return _role("success")
def warning() -> str: return _role("warning")
def error() -> str: return _role("error")
def shadow() -> str: return _role("shadow")


def speaker_color(index: int) -> str:
    palette = _SPEAKER_DARK if _DARK_ACTIVE else _SPEAKER_LIGHT
    return palette[index % len(palette)]


def scheme(dark: bool) -> dict[str, str]:
    """The full palette for a mode, used to build the Material 3 colour scheme."""
    return dict(_DARK if dark else _LIGHT)
