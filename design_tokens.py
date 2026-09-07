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
# Three sizes, not eight. Hierarchy comes from weight and colour, which is what makes a
# dense tool feel calm; a ladder with eight rungs reads as eight competing voices. The
# remaining names are aliases onto those three so nothing has to be renamed everywhere.
# The three base sizes, and the scale the researcher can move them by. Text is the whole
# interface here — a transcript is nothing but text — so one number changes the density of
# the entire application rather than each screen carrying its own idea of small.
BASE_DISPLAY, BASE_BODY, BASE_META = 19, 14, 11
SCALES = (("0.9", "Smaller"), ("1.0", "Default"), ("1.15", "Larger"), ("1.3", "Largest"))

TYPE_DISPLAY = BASE_DISPLAY  # the only large text: a screen or panel title
TYPE_BODY = BASE_BODY        # everything a person reads: speech, field values, buttons
TYPE_META = BASE_META        # everything a person glances at: counts, labels, timestamps

TYPE_TITLE = TYPE_DISPLAY
TYPE_HEADING = TYPE_BODY
TYPE_SUBHEADING = TYPE_BODY
TYPE_SUBTITLE = TYPE_META
TYPE_SECONDARY = TYPE_BODY
TYPE_LABEL = TYPE_META
TYPE_CAPTION = TYPE_META
TYPE_MONO = TYPE_META        # timestamps

# ── Surfaces ──────────────────────────────────────────────────────────────────
# One card style everywhere: same radius, same hairline, same inner padding. A screen that
# mixes 16 and 24 inside otherwise identical panels reads as two designs stacked.
CARD_PADDING = 20
HAIRLINE = 1
# Surfaces separate by tone. A line is used only where two scrolling regions meet, which
# is about four places in the whole application instead of the twenty it used to be.

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
# One radius for everything with an edge. Mixing four of them is the difference between
# a designed interface and an assembled one.
RADIUS = 4
R_SM = RADIUS
R_MD = RADIUS
R_LG = RADIUS
R_PILL = 999

# ── Layout ────────────────────────────────────────────────────────────────────
TOP_BAR_HEIGHT = 48
STATUS_BAR_HEIGHT = 24       # the slim band along the bottom of the whole window
# One monospaced family, named once. Timings, counts and identifiers are data, and data set
# in a proportional face wanders as it changes; in a mono face the columns hold still.
MONO = "Consolas, Cascadia Mono, Menlo, monospace"
NAV_WIDTH = 220              # fixed while expanded
NAV_MINIMISED = 56           # an activity bar, not a sidebar

# ── Sidebar rhythm ────────────────────────────────────────────────────────────
WORDMARK_TOP = 18            # breathing room above the mark; nothing clipped
WORDMARK_LEFT = 16           # lines the mark up with the nav icons below it
WORDMARK_GAP = 10            # between the mark and the name
MARK_SIZE = 44               # the logo in the sidebar: an app icon, not a bullet
MARK_HERO = 76               # the same mark on Home
NAV_ITEM_HEIGHT = 44
NAV_ITEM_GAP = 12            # vertical gap between destinations
NAV_PILL_INSET = 8           # the selected pill never touches the rail edges
NAV_PILL_RADIUS = 10
NAV_ITEM_PADDING = 12        # inside the pill; icon lands at INSET + PADDING = 20

# ── Top bar rhythm ────────────────────────────────────────────────────────────
TOP_BAR_LEFT = 32            # same left padding as the content column below
ICON_BUTTON = 34             # square hit area
ICON_BUTTON_GAP = 4
CONTROLS_GAP = 24            # before the divider and the OS window controls

# ── Empty state ───────────────────────────────────────────────────────────────
EMPTY_STATE_MAX = 560        # capped, and never wider than the column it sits in
EMPTY_STATE_PADDING = 48
EMPTY_STATE_RHYTHM = 16
EMPTY_STATE_ICON = 40
# The editing pane, and the widest declared pane on the screen. Correcting a sentence is
# what this screen is for, so the box you correct it in gets the room: at 540 with 12 of
# padding, a line runs to about 72 characters — a readable measure rather than the column
# of three-word lines it started as.
INSPECTOR_WIDTH = 660        # fixed
INSPECTOR_PADDING = 12       # tighter than a card: the box inside is the point
WORKSPACE_MIN = 380          # the workspace never shares the row below this
# Under this the inspector is a slide-over, not a third column.
INSPECTOR_BREAKPOINT = NAV_WIDTH + WORKSPACE_MIN + INSPECTOR_WIDTH
MAX_CONTENT = 960            # hard cap on the inner content column
CONTENT_GUTTER = 32          # equal padding either side of that column
# A document screen is capped at a readable column. A workbench is not a document: the
# review screen is three panes side by side, so it takes the whole workspace and caps the
# spoken text instead (TRANSCRIPT_MEASURE below). Capping the panes wastes the desk.
WORKBENCH_GUTTER = 24
WORKBENCH_BAR_HEIGHT = 46    # title, counts and actions on one line, in place of a header block
# The review screen is three columns: the open turn, the transcript, the speaker list.
# The list gets a real width rather than a share of the column — as a proportion it shrank
# to about ninety pixels of name field on an ordinary window, which is unusable. The
# transcript keeps a floor, and below the point where both fit the list floats instead.
# The speaker list holds names and turn counts, nothing wider. It was sized when it was the
# only other pane; beside a 490 editor it was taking room from both the transcript and the
# text being corrected, for a column that is mostly white space.
IDENTITY_PANE_WIDTH = 184
# The speaker list may only take a column while the transcript still has a usable one beside
# it. This governs the whole three-column arrangement: at 1268 the sums are 56 rail + 660
# editor + 48 gutters + 184 speakers + 16 + 304 transcript, and the editor cannot grow past
# about 660 without pushing the speaker list out into a floating panel.
TRANSCRIPT_MIN_COLUMN = 300
# ── Reading ───────────────────────────────────────────────────────────────────
TRANSCRIPT_MEASURE = 640     # max width of the spoken text itself
TURN_GAP = 2                 # air between turns, in place of a border on every row
LINE_HEIGHT = 1.4
TURN_PADDING = 6             # inside a turn, top and bottom
# A turn shows two full lines of speech across the whole column. One line clipped at about
# thirty characters — which is what a three-column window left — made the transcript the
# one thing in the application that could not be read.
TURN_LINES = 2
TRANSCRIPT_ROW_HEIGHT = 76   # uniform rows keep virtualised scrolling exact (gap included)
CHECK_RULE = 3               # the accent bar marking a turn as reviewed
SKIP_SECONDS = 5             # how far the back/forward transport buttons jump
FIELD_HEIGHT = 38            # one height for every text field and dropdown
FIELD_HEIGHT_DENSE = 34      # inside overlays and the inspector, where space is tight
PLAYER_BAR_HEIGHT = 44       # a status bar, not a card competing with the text

# ── Brand ────────────────────────────────────────────────────────────────────
# The five colours of the logo, named as they were given. Everything with a hue in this
# application comes from here or from a tint of it, so the interface and the mark on the
# sidebar are demonstrably the same palette rather than two that happen to look similar.
AMBER = "#E8871E"        # Amber Earth  — the warm half of the mark
ROSE = "#945D5E"         # Smoky Rose   — the second half
TEAL = "#759588"         # Muted Teal   — the microphone body, and the accent family
GRANITE = "#424D44"      # Granite      — its shadow
CARBON = "#23231A"       # Carbon Black — the ink, and the dark theme's ground

# The accent is Muted Teal taken to the lightness each theme needs. The palette colour
# itself is a fill, not an ink: white on #759588 is 3.4:1, which is not a button label.
# Darkened for light (white sits on it at 5.1:1) and lifted for dark (carbon ink, 6.7:1).
PRIMARY_LIGHT = "#5B746A"
PRIMARY_DARK = "#8DAE9F"
SEED = PRIMARY_LIGHT

# ── Palettes ─────────────────────────────────────────────────────────────────
# Greys warmed a few degrees toward Carbon Black, which is where the logo's own ground sits.
# Not beige — the earlier warm scale tinted every surface like stationery. Just enough that
# the amber and the rose are not sitting on a cold blue-grey that argues with them.
_LIGHT = {
    "chrome": "#F1F0EE",              # recessed: rail, toolbar, player
    "background": "#E6E4E0",          # the seam between chrome and work
    "surface": "#FFFFFF",             # raised: the transcript, the open turn
    "surface_variant": "#F5F4F2",     # a quiet fill inside a surface
    "surface_raised": "#FFFFFF",
    "on_surface": "#1F1F1A",          # Carbon Black: text carries the contrast, not boxes
    "on_surface_variant": "#5C5B54",
    "muted": "#87857C",
    "outline": "#DEDCD7",
    "outline_strong": "#C5C2BB",
    "primary": PRIMARY_LIGHT,
    "on_primary": "#FFFFFF",
    "primary_soft": "#E6EBE8",
    "success": "#4A6F5E",
    # Amber Earth, darkened until it can be read as text on a light ground.
    "warning": "#9A5A12",
    # Red still, because a failure has to read as one, but pulled toward Smoky Rose so it
    # belongs to the family instead of arriving from a different palette.
    "error": "#B04B44",
    "shadow": "#100B0F14",
    # Amber Earth, translucent. Eight-digit colours are AARRGGBB, alpha first — written the
    # other way round "#FFFFFF26" parses as opaque #FFFF26, which is why the scrollbar in
    # the dark theme was a bright yellow bar that belonged to no palette at all.
    "scrollbar": "#66E8871E",
    # Amber Earth as given: a fill for the small marks that should catch the eye first.
    "accent_warm": AMBER,
    "on_accent_warm": CARBON,
    "mark_edge": "#D2D0CA",
}

_DARK = {
    "chrome": "#212119",
    "background": "#191915",
    "surface": "#292921",
    "surface_variant": "#31312A",
    "surface_raised": "#38382F",
    "on_surface": "#E9E7E0",
    "on_surface_variant": "#A9A79D",
    "muted": "#7E7C72",
    "outline": "#3B3B33",
    "outline_strong": "#4D4D44",
    "primary": PRIMARY_DARK,          # lifted for dark; carbon ink sits on it at 6.7:1
    "on_primary": CARBON,
    "primary_soft": "#293530",
    "success": PRIMARY_DARK,
    "warning": AMBER,                 # readable as given on a dark ground
    "error": "#E0908A",
    "shadow": "#59000000",
    "scrollbar": "#8CE8871E",
    "accent_warm": AMBER,
    "on_accent_warm": CARBON,
    "mark_edge": "#33000000",
}

# Speaker identity is its own family, cooler than the accent and never equal to it.
_SPEAKER_LIGHT = ("#3F6FA8", "#A2662F", "#6C63B5", "#9A4F7E", "#2F7F79", "#8A6A3B", "#4E7BA8", "#7C6A45")
_SPEAKER_DARK = ("#7FAEE0", "#DDA96B", "#A79EE8", "#D48FB6", "#66C2BA", "#D2AC78", "#8FBEEA", "#C7B489")

_DARK_ACTIVE = False


def set_dark(active: bool) -> None:
    global _DARK_ACTIVE
    _DARK_ACTIVE = active


def is_dark() -> bool:
    return _DARK_ACTIVE


_SCALE = 1.0


def type_scale() -> float:
    return _SCALE


def set_type_scale(scale: float) -> None:
    """Resize the whole interface from one number, before anything is built.

    The sizes are read as module attributes at build time, so setting them here reaches
    every screen at once — which is the only way a text-size preference can work without
    every control being taught about it.
    """
    global _SCALE, TYPE_DISPLAY, TYPE_BODY, TYPE_META
    global TYPE_TITLE, TYPE_HEADING, TYPE_SUBHEADING, TYPE_SUBTITLE
    global TYPE_SECONDARY, TYPE_LABEL, TYPE_CAPTION, TYPE_MONO
    _SCALE = max(0.8, min(float(scale or 1.0), 1.4))
    TYPE_DISPLAY = round(BASE_DISPLAY * _SCALE, 1)
    TYPE_BODY = round(BASE_BODY * _SCALE, 1)
    TYPE_META = round(BASE_META * _SCALE, 1)
    TYPE_TITLE = TYPE_DISPLAY
    TYPE_HEADING = TYPE_SUBHEADING = TYPE_SECONDARY = TYPE_BODY
    TYPE_SUBTITLE = TYPE_LABEL = TYPE_CAPTION = TYPE_MONO = TYPE_META


def _role(name: str) -> str:
    return (_DARK if _DARK_ACTIVE else _LIGHT)[name]


def background() -> str: return _role("background")
def mark_edge() -> str: return _role("mark_edge")
def accent_warm() -> str: return _role("accent_warm")
def on_accent_warm() -> str: return _role("on_accent_warm")
def chrome() -> str: return _role("chrome")
def surface() -> str: return _role("surface")
def surface_variant() -> str: return _role("surface_variant")
def surface_raised() -> str: return _role("surface_raised")
def on_surface() -> str: return _role("on_surface")
def on_surface_variant() -> str: return _role("on_surface_variant")
def muted() -> str: return _role("muted")
def outline() -> str: return _role("outline")
def outline_strong() -> str: return _role("outline_strong")
def primary() -> str: return _role("primary")


def primary_hover() -> str:
    """A deeper accent for hover and press. Overlaying the label colour instead made a
    filled button fade towards its own text on contact — it looked like it disappeared."""
    return "#2F6650" if not _DARK_ACTIVE else "#7ED0AA"
def on_primary() -> str: return _role("on_primary")
def primary_soft() -> str: return _role("primary_soft")


def scrollbar() -> str:
    """The thumb colour. An editor's scrollbar is a hint at the edge of the text, not a
    control with a track and a border around it."""
    return _role("scrollbar")
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
