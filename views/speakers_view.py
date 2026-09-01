"""The review screen: identities on the left, the transcript in the middle, one turn open
on the right.

Three regions with fixed shares. Nothing a tool does may change them — find and replace
floats above this screen rather than inside it, and the merge menu is a popup — so the
geometry below is the geometry the researcher sees for the whole session.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from app_state import AppState
from components.audio_transport import audio_missing_banner,audio_transport
from components.buttons import icon_button,primary_button,secondary_button,tertiary_button
from components.speaker_panel import speaker_panel
from components.transcript_list import transcript_list
from models import TranscriptSegment
from playback_sync import low_confidence_marks
from providers import feature_state
from speaker_reconciliation import speaker_statistics,apply_speaker_mapping
from document_export import format_timestamp
from theme import note,page_title

PAGE_SIZE=80


def speaker_index(state:AppState)->dict[str,int]:
    """Stable colour slot per speaker, shared by the panel, the rows and the inspector."""
    return {speaker:index for index,speaker in enumerate(sorted({item.speaker_id for item in state.transcript_segments}))}


def identity_column_fits(content_width:float|None)->bool:
    """Whether the speaker list can sit beside the transcript without squeezing it.

    Two panes in one column only works while both keep a usable width. Below that the list
    floats instead — better than a name field too narrow to read and a transcript too narrow
    to scan, which is what a proportional split gave on an ordinary window.
    """
    return float(content_width or t.MAX_CONTENT)>=t.IDENTITY_PANE_WIDTH+t.S16+t.TRANSCRIPT_MIN_COLUMN


@dataclass(frozen=True)
class Placement:
    """Where each of the two side panes goes on this window."""
    identities: str          # "column" | "float" | "hidden"
    detail: str              # "pane" | "float" | "hidden"

    @property
    def floating(self) -> tuple[str,...]:
        return tuple(name for name,value in (("identities",self.identities),("detail",self.detail))
                     if value=="float")


def pane_placement(content_width:float|None,docked:bool,identities_hidden:bool=False,
                   find_open:bool=False)->Placement:
    """Decide the whole screen at once, so two surfaces can never end up on top of each other.

    The rules, in order:

      * The open turn takes the right-hand pane whenever the window is wide enough for a
        third column, and floats otherwise.
      * The speaker list takes the left column whenever the transcript keeps a usable width
        beside it — and always when the turn is floating, because then there is no third
        column to make room for.
      * At most one thing ever floats. Two floating surfaces would sit over one another with
        no way to tell which is on top, so a floating pane steps aside while a transient
        tool is open and comes back when it closes.
    """
    detail="pane" if docked else "float"
    if identities_hidden: identities="hidden"
    elif identity_column_fits(content_width) or not docked: identities="column"
    else: identities="float"
    if find_open:
        if identities=="float": identities="hidden"
        if detail=="float": detail="hidden"
    placement=Placement(identities,detail)
    assert len(placement.floating)<=1, placement
    return placement


def reading_measure(content_width:float|None,identity_width:float=0.0)->float:
    """How wide the spoken text is allowed to run.

    The desk can be any size; a line of prose cannot. This caps the text at a comfortable
    measure while never exceeding the column it actually sits in — the floor is deliberately
    below TRANSCRIPT_MIN_COLUMN so the cap can never be wider than the space it is given.
    """
    available=float(content_width or t.MAX_CONTENT)
    if identity_width: available-=identity_width+t.S16
    return max(160.0,min(float(t.TRANSCRIPT_MEASURE),available-t.TIMESTAMP_GUTTER-2*t.S16))


def _diarization_caption(state:AppState)->ft.Control|None:
    """How the speakers were found, said once, beside the speakers themselves.

    This used to be a full-width strip above the transcript on every render — a permanent
    sentence about something the researcher cannot change, sitting between them and the
    interview. It is information about the identity list, so it lives on the identity list.
    """
    features=feature_state(state.effective_capabilities)
    if features["manual_speaker_split"]: return None          # the count line already says it
    if features["speaker_reconciliation"]:
        return ft.Row([ft.Icon(ft.Icons.WARNING_AMBER,size=13,color=t.warning()),
            ft.Text(s.DIARIZATION_FRAGMENTED,size=t.TYPE_CAPTION,color=t.on_surface_variant(),
                expand=True)],spacing=t.S4,vertical_alignment=ft.CrossAxisAlignment.CENTER)
    return ft.Text(s.DIARIZATION_GLOBAL,size=t.TYPE_CAPTION,color=t.muted())


def _workbench_bar(state:AppState,speakers:int,on_open_find:Callable[[],None]|None,
                   on_export:Callable[[],None],on_toggle_identities:Callable[[],None]|None=None,
                   identities_hidden:bool=False)->ft.Control:
    """One 56px line where a heading block used to be.

    The eyebrow and the subtitle said what the sidebar already shows and what the researcher
    learned on their first run. What they cannot get anywhere else is the size of what they
    are holding, so that is what the line carries instead.
    """
    segments=state.transcript_segments
    duration=format_timestamp(segments[-1].absolute_end) if segments else format_timestamp(0)
    meta=s.WORKBENCH_META.format(turns=len(segments),speakers=speakers,duration=duration)
    # Title and count stack, so neither has to compete with the other for the same line, and
    # the actions get a whole column of their own with even spacing between them.
    identity=ft.Column([
        ft.Text(s.SPEAKERS_TITLE,size=t.TYPE_DISPLAY,weight=ft.FontWeight.W_600,
            color=t.on_surface(),no_wrap=True),
        ft.Text(meta,size=t.TYPE_LABEL,color=t.muted(),no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS)],spacing=2,tight=True)
    actions:list[ft.Control]=[]
    if on_toggle_identities is not None:
        actions.append(icon_button(ft.Icons.PEOPLE_OUTLINE,
            s.EXPAND_IDENTITIES if identities_hidden else s.COLLAPSE_IDENTITIES,
            lambda e:on_toggle_identities(),
            color=t.muted() if identities_hidden else t.primary()))
    actions.append(secondary_button(s.FIND_REPLACE,(lambda e:on_open_find()) if on_open_find else None,
        ft.Icons.FIND_REPLACE,disabled=on_open_find is None))
    actions.append(primary_button(s.CONTINUE_TO_EXPORT,lambda e:on_export(),ft.Icons.ARROW_FORWARD))
    # The bar spans the whole content width, above the panes. Inside a pane it was squeezed
    # by the pane, and the primary action was the first thing to be cut off.
    return ft.Container(ft.Row([ft.Container(identity,expand=True,padding=ft.Padding(0,0,t.S24,0)),
        ft.Row(actions,spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER)],
        spacing=0,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.WORKBENCH_BAR_HEIGHT)


def _uncertain_strip(state:AppState,on_next:Callable[[],None]|None)->ft.Control|None:
    """Only shown when the provider actually scores confidence — otherwise there is nothing
    to count, and a control that always reads zero is worse than no control."""
    if not feature_state(state.effective_capabilities)["confidence_display"]: return None
    marks=low_confidence_marks(state.transcript_segments)
    # Nothing flagged is not news. A row that can only ever say "all clear" is one more
    # thing to read past on every render, so it simply is not drawn.
    if not marks: return None
    word_level=any(mark.word_level for mark in marks)
    label=(s.LOW_CONFIDENCE_COUNT if word_level else s.LOW_CONFIDENCE_TURNS).format(count=len(marks))
    return ft.Container(ft.Row([ft.Icon(ft.Icons.HELP_OUTLINE,size=16,color=t.on_surface_variant()),
        ft.Text(label,size=t.TYPE_LABEL,color=t.on_surface(),expand=True),
        secondary_button(s.LOW_CONFIDENCE_NEXT,(lambda e:on_next()) if on_next else None,
            ft.Icons.ARROW_FORWARD,disabled=on_next is None)],
        spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.S16,t.S8,t.S16,t.S8),bgcolor=t.surface_variant(),
        border=ft.Border.all(t.HAIRLINE,t.outline()),border_radius=t.R_SM)


def identities_pane(state:AppState,on_map:Callable[[str,str],None],refs:dict|None=None,
                    on_typing:Callable[[bool],None]|None=None,
                    on_merge:Callable[[str,str],None]|None=None,
                    on_close:Callable[[],None]|None=None,heading:bool=True)->ft.Control:
    """The speaker list, as the screen's right-hand pane.

    It used to be a proportional column on the left, which on an ordinary window left the
    name field about ninety pixels wide — too narrow to read a name in, let alone edit one.
    A fixed pane gives it a width that does not shrink as the transcript grows.
    """
    stats=speaker_statistics(state.transcript_segments)
    colors=speaker_index(state)
    diarized=feature_state(state.effective_capabilities)["speaker_naming"]
    panel_refs=refs.setdefault("speakers",{}) if refs is not None else None
    rows:list[ft.Control]=[]
    if heading:
        head:list[ft.Control]=[ft.Text(s.IDENTITIES,size=t.TYPE_HEADING,weight=ft.FontWeight.W_600,
            color=t.on_surface(),expand=True)]
        if on_close is not None:
            head.append(icon_button(ft.Icons.CLOSE,s.COLLAPSE_IDENTITIES,lambda e:on_close(),size=17))
        rows.append(ft.Row(head,spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return ft.Column([*rows,
        ft.Text(s.IDENTITIES_COUNT.format(count=len(stats)) if diarized else s.IDENTITIES_NONE,
            size=t.TYPE_LABEL,color=t.muted()),
        _diarization_caption(state) or ft.Container(height=0),
        ft.Container(height=t.S8),
        speaker_panel(stats,state.speaker_mapping,colors,on_map,diarized,panel_refs,on_typing,
            on_merge if diarized else None)],spacing=t.S4,expand=True)


def build(state:AppState,on_select:Callable[[int],None],on_play:Callable[[int],None],
          on_export:Callable[[],None],selected_index:int|None,offset:int,on_page:Callable[[int],None],
          refs:dict|None=None,content_width:float|None=None,
          on_locate_audio:Callable[[],None]|None=None,on_dismiss_audio:Callable[[],None]|None=None,
          on_next_uncertain:Callable[[],None]|None=None,on_open_find:Callable[[],None]|None=None,
          on_toggle_identities:Callable[[],None]|None=None,identities_hidden:bool=False,
          identities:ft.Control|None=None,order:list[int]|None=None,
          progress:ft.Control|None=None)->ft.Control:
    """The workbench: one bar across the top, then the speaker list beside the transcript.

    The speaker list is the left column, at a declared width rather than a share of the
    space. The open turn is the screen's right-hand pane and is supplied by the shell, so
    the two never contend for the same room and neither can be squeezed by the other.
    """
    stats=speaker_statistics(state.transcript_segments)
    colors=speaker_index(state)
    row_refs=refs.setdefault("rows",{}) if refs is not None else None

    # The list only takes the column when both panes still fit; the caller floats it otherwise.
    identity_width=float(t.IDENTITY_PANE_WIDTH) if identities is not None else 0.0
    measure=reading_measure(content_width,identity_width)
    shown=list(range(len(state.transcript_segments))) if order is None else order
    listing=transcript_list(state.transcript_segments,shown,state.speaker_mapping,colors,
        selected_index,offset,PAGE_SIZE,on_select,on_page,row_refs,measure)
    # Nothing between the bar and the text is permanent. Every row below appears only when
    # it has something to say, so an ordinary transcript starts straight under the bar.
    column:list[ft.Control]=[]
    # Progress sits directly under the bar, above everything conditional: it is the one
    # thing on this screen that is always worth a glance.
    if progress is not None: column.append(progress)
    # The reconnect prompt is dismissible: the transcript is fully usable without audio.
    if state.audio_missing and not state.audio_banner_dismissed and on_locate_audio and on_dismiss_audio:
        column.append(audio_missing_banner(on_locate_audio,on_dismiss_audio))
    uncertain=_uncertain_strip(state,on_next_uncertain)
    if uncertain is not None: column.append(uncertain)
    column.append(listing)
    reading=ft.Container(ft.Column(column,spacing=t.S12,expand=True),expand=True,
        padding=ft.Padding(t.S16 if identities is not None else 0,0,0,0),
        clip_behavior=ft.ClipBehavior.HARD_EDGE)

    panes:list[ft.Control]=[]
    if identities is not None:
        # Declared width, no expand: a container given both grows to the row and ignores the
        # width, which is exactly how this column ended up ninety pixels wide before.
        panes.append(ft.Container(identities,width=identity_width,
            padding=ft.Padding(0,0,t.S16,0),clip_behavior=ft.ClipBehavior.HARD_EDGE,
            border=ft.Border(right=ft.BorderSide(t.HAIRLINE,t.outline()))))
    panes.append(reading)
    return ft.Column([
        _workbench_bar(state,len(stats),on_open_find,on_export,on_toggle_identities,identities_hidden),
        ft.Row(panes,spacing=0,expand=True)],spacing=t.S12,expand=True)


def word_ribbon(item:TranscriptSegment,on_seek:Callable[[float],None])->ft.Control:
    """The turn as clickable words, in the same slot the editor occupies.

    It is a mode of the one text surface rather than a second copy of the text below it:
    showing the same sentence three times — original, words, corrected — filled the panel
    and left nothing to read.
    """
    spans=[ft.TextSpan(f"{word.text} ",
        style=ft.TextStyle(size=t.TYPE_BODY,color=t.on_surface(),height=t.LINE_HEIGHT),
        on_click=(lambda e,start=word.start:on_seek(start))) for word in item.words if word.text]
    return ft.Container(ft.Column([
        ft.Text(spans=spans,selectable=True),
        ft.Text(s.SEEK_WORDS,size=t.TYPE_CAPTION,color=t.muted())],spacing=t.S8),
        padding=t.S12,border=ft.Border.all(t.HAIRLINE,t.outline()),border_radius=t.R_SM,
        bgcolor=t.surface_variant())


def _reassign_dropdown(item:TranscriptSegment,state:AppState,index:int,
                       on_reassign:Callable[[int,str],None]|None,
                       on_typing:Callable[[bool],None]|None)->ft.Control:
    """The turn was actually someone else: a compact select, applied on choice.

    It sits in the inspector action row rather than opening anything of its own. Moving one
    turn is a small correction and should cost one click, not a panel.
    """
    speakers=sorted({turn.speaker_id for turn in state.transcript_segments})
    return ft.Dropdown(value=item.speaker_id,expand=True,dense=True,
        height=t.FIELD_HEIGHT_DENSE,text_size=t.TYPE_SECONDARY,
        label=s.REASSIGN_LABEL,label_style=ft.TextStyle(size=t.TYPE_LABEL,color=t.muted()),
        tooltip=s.REASSIGN_TOOLTIP,
        border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
        color=t.on_surface(),content_padding=ft.Padding(t.S12,t.S4,t.S8,t.S4),
        disabled=on_reassign is None or len(speakers)<2,
        options=[ft.DropdownOption(key=speaker,
            text=state.speaker_mapping.get(speaker,speaker)) for speaker in speakers],
        on_focus=(lambda e:on_typing(True)) if on_typing else None,
        on_blur=(lambda e:on_typing(False)) if on_typing else None,
        on_select=(lambda e:on_reassign(index,e.control.value or item.speaker_id)) if on_reassign else None)


def inspector(state:AppState,index:int|None,on_save:Callable[[int,str],None],on_revert:Callable[[int],None],
              on_play:Callable[[int],None],refs:dict|None=None,
              on_close:Callable[[],None]|None=None,on_seek:Callable[[float],None]|None=None,
              on_typing:Callable[[bool],None]|None=None,
              on_stamp:Callable[[],None]|None=None,
              on_reassign:Callable[[int,str],None]|None=None,
              on_checked:Callable[[int,bool],None]|None=None,
              words_mode:bool=False,on_words_mode:Callable[[],None]|None=None,
              show_original:bool=False,on_show_original:Callable[[],None]|None=None)->ft.Control:
    """One turn, shown once.

    The panel holds a single text surface. It is the editor by default and the clickable
    word ribbon when the researcher asks for it — two modes of one block rather than two
    blocks. The untouched original is not shown at all unless the text has actually been
    changed and the researcher asks to compare.
    """
    def heading(title:str)->ft.Control:
        row=[ft.Text(title,size=t.TYPE_HEADING,weight=ft.FontWeight.W_600,color=t.on_surface(),expand=True)]
        if on_close is not None:
            row.append(icon_button(ft.Icons.CLOSE,s.CLOSE_INSPECTOR,lambda e:on_close(),size=17))
        return ft.Row(row,spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER)

    if index is None or index>=len(state.transcript_segments):
        return ft.Column([heading(s.INSPECTOR_EMPTY_TITLE),
            ft.Text(s.INSPECTOR_EMPTY_BODY,size=t.TYPE_SECONDARY,color=t.on_surface_variant())],spacing=t.S8)
    item=state.transcript_segments[index]
    features=feature_state(state.effective_capabilities)
    colors=speaker_index(state)
    edited=item.corrected_text is not None
    timed=bool(features["word_timestamps"] and item.words and on_seek)

    field=ft.TextField(label=s.INSPECTOR_CORRECTED,value=item.text,multiline=True,min_lines=6,max_lines=14,
        text_size=t.TYPE_BODY,border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
        color=t.on_surface(),label_style=ft.TextStyle(size=t.TYPE_LABEL,color=t.muted()),
        on_focus=(lambda e:on_typing(True)) if on_typing else None,
        on_blur=(lambda e:on_typing(False)) if on_typing else None)
    if refs is not None: refs["inspector_field"]=field
    # The one text slot. Words mode is only offered when the provider actually timed words.
    surface=word_ribbon(item,on_seek) if (words_mode and timed) else field

    checked=ft.Checkbox(s.MARK_CHECKED,value=item.checked,tooltip=s.MARK_CHECKED_TOOLTIP,
        active_color=t.primary(),check_color=t.on_primary(),
        label_style=ft.TextStyle(size=t.TYPE_LABEL,color=t.on_surface_variant()),
        disabled=on_checked is None,
        on_change=(lambda e:on_checked(index,bool(e.control.value))) if on_checked else None)
    if refs is not None: refs["inspector_checked"]=checked

    meta:list[ft.Control]=[]
    if features["confidence_display"] and item.confidence is not None:
        meta.append(ft.Text(s.INSPECTOR_CONFIDENCE.format(percent=int(item.confidence*100)),
            size=t.TYPE_LABEL,color=t.on_surface_variant()))
    if features["word_timestamps"] and item.words:
        meta.append(ft.Text(s.INSPECTOR_WORDS.format(count=len(item.words)),size=t.TYPE_LABEL,color=t.muted()))

    actions:list[ft.Control]=[_reassign_dropdown(item,state,index,on_reassign,on_typing)]
    if timed and on_words_mode is not None:
        actions.append(icon_button(ft.Icons.EDIT_OUTLINED if words_mode else ft.Icons.TOUCH_APP_OUTLINED,
            s.EDIT_TEXT if words_mode else s.SEEK_WORDS,lambda e:on_words_mode(),
            color=t.primary() if words_mode else None))
    actions.append(icon_button(ft.Icons.SCHEDULE,s.INSERT_TIMESTAMP,
        (lambda e:on_stamp()) if on_stamp else None,disabled=on_stamp is None or words_mode))
    actions.append(icon_button(ft.Icons.RESTORE,s.REVERT_CORRECTION,lambda e:on_revert(index)))
    actions.append(icon_button(ft.Icons.PLAY_ARROW,s.PLAY_RANGE,lambda e:on_play(index)))

    body:list[ft.Control]=[
        heading(s.INSPECTOR_TITLE),
        ft.Row([ft.Container(width=10,height=10,border_radius=t.R_PILL,bgcolor=t.speaker_color(colors.get(item.speaker_id,0))),
            ft.Text(apply_speaker_mapping(item,state.speaker_mapping),size=t.TYPE_SUBHEADING,
                weight=ft.FontWeight.W_600,color=t.on_surface(),expand=True),checked],
            spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([ft.Text(item.speaker_id,size=t.TYPE_CAPTION,color=t.muted(),expand=True),*meta],
            spacing=t.S8),
        ft.Divider(height=1,color=t.outline()),
        surface,
        ft.Row(actions,spacing=t.S4,vertical_alignment=ft.CrossAxisAlignment.CENTER)]
    # The original only exists as a thing to look at once the text has been changed.
    if edited and on_show_original is not None:
        body.append(ft.Row([tertiary_button(s.HIDE_ORIGINAL if show_original else s.SHOW_ORIGINAL,
            lambda e:on_show_original(),ft.Icons.HISTORY_TOGGLE_OFF)],spacing=0))
        if show_original:
            body.append(ft.Container(ft.Text(item.original_text,size=t.TYPE_SECONDARY,
                color=t.on_surface_variant(),selectable=True),padding=t.S12,
                bgcolor=t.surface_variant(),border_radius=t.R_SM,
                border=ft.Border.all(t.HAIRLINE,t.outline())))
    body.append(secondary_button(s.SAVE_CORRECTION,lambda e:on_save(index,field.value or ""),
        ft.Icons.CHECK,disabled=words_mode))
    body.append(ft.Text(s.MARK_NEXT_HINT,size=t.TYPE_CAPTION,color=t.muted()))
    return ft.Column(body,spacing=t.S12,scroll=ft.ScrollMode.AUTO)
