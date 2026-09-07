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
from components.audio_transport import audio_missing_banner
from components.buttons import icon_button,primary_button,secondary_button,tertiary_button
from components.marking import comment_list,marking_bar as marking,preview as mark_preview
from components.speaker_panel import speaker_panel
from components.transcript_list import transcript_list
from models import TranscriptSegment
from providers import feature_state
from speaker_reconciliation import speaker_statistics,apply_speaker_mapping
from document_export import format_timestamp
from theme import note,panel_title

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

    It used to take a timestamp gutter off the top as well. There is no gutter: the stamp
    moved onto the line above the speech long ago and the subtraction stayed behind, quietly
    costing every row fifty-six pixels of the sentence it was supposed to be showing.
    """
    available=float(content_width or t.MAX_CONTENT)
    if identity_width: available-=identity_width+t.S16
    return max(160.0,min(float(t.TRANSCRIPT_MEASURE),available-2*t.S16))


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


# What the toolbar costs before anything is dropped, in the order it is dropped. Measured
# from the tokens rather than guessed: a Row cannot shrink an intrinsic child, so a bar with
# more in it than fits does not compress — it clips, and what it clips is the last thing in
# the row, which is the button that leaves the screen.
BAR_PROGRESS = 250           # ring, count, filter and resume inside their pill
BAR_ICONS = 2*(t.ICON_BUTTON+t.S8)   # the speaker toggle and find, with their gaps
BAR_EXPORT_LABELLED = 190    # icon, "Continue to export", padding
BAR_TITLE = 190              # the screen name and the turn counts beside it


def _workbench_bar(state:AppState,speakers:int,on_open_find:Callable[[],None]|None,
                   on_export:Callable[[],None],on_toggle_identities:Callable[[],None]|None=None,
                   identities_hidden:bool=False,progress:ft.Control|None=None,
                   width:float|None=None)->ft.Control:
    """One line where four bands used to be.

    The screen title, the counts, the progress and the actions were four stacked strips
    before the first word of the interview. The rail already says which screen this is, so
    the title carries the one thing nothing else can tell you — how large the thing in front
    of you is — and everything else joins it on the same line.
    """
    segments=state.transcript_segments
    duration=format_timestamp(segments[-1].absolute_end) if segments else format_timestamp(0)
    meta=s.WORKBENCH_META.format(turns=len(segments),speakers=speakers,duration=duration)
    # Three columns leave the toolbar about five hundred pixels on an ordinary window, and
    # everything in it has a width of its own. So the pieces are dropped in order of what
    # can be learnt elsewhere: the screen name is in the sidebar and the status band, the
    # counts are in the progress pill, and only the way out of the screen is irreplaceable.
    room=float(width or t.MAX_CONTENT)
    fixed=(BAR_PROGRESS if progress is not None else 0)+BAR_ICONS
    labelled=room>=fixed+BAR_EXPORT_LABELLED
    titled=room>=fixed+BAR_EXPORT_LABELLED+BAR_TITLE

    leading:list[ft.Control]=[]
    if titled:
        leading=[ft.Row([
            ft.Text(s.SPEAKERS_TITLE,size=t.TYPE_DISPLAY,weight=ft.FontWeight.W_600,
                color=t.on_surface(),no_wrap=True),
            ft.Text(meta,size=t.TYPE_META,color=t.muted(),no_wrap=True,
                overflow=ft.TextOverflow.ELLIPSIS,expand=True)],
            spacing=t.S12,vertical_alignment=ft.CrossAxisAlignment.CENTER,expand=True)]
    else:
        leading=[ft.Container(expand=True,tooltip=f"{s.SPEAKERS_TITLE} · {meta}")]

    actions:list[ft.Control]=[]
    if progress is not None: actions.append(progress)
    if on_toggle_identities is not None:
        actions.append(icon_button(ft.Icons.PEOPLE_OUTLINE,
            s.EXPAND_IDENTITIES if identities_hidden else s.COLLAPSE_IDENTITIES,
            lambda e:on_toggle_identities(),
            color=t.muted() if identities_hidden else t.primary()))
    actions.append(icon_button(ft.Icons.FIND_REPLACE,s.FIND_REPLACE,
        (lambda e:on_open_find()) if on_open_find else None,disabled=on_open_find is None))
    if labelled:
        actions.append(primary_button(s.CONTINUE_TO_EXPORT,lambda e:on_export(),
            ft.Icons.ARROW_FORWARD))
    else:
        # Still the accent, still the only filled control on the screen — just without the
        # words, which is better than the words with their end cut off.
        actions.append(ft.IconButton(ft.Icons.ARROW_FORWARD,tooltip=s.CONTINUE_TO_EXPORT,
            on_click=lambda e:on_export(),icon_color=t.on_primary(),icon_size=18,
            width=t.ICON_BUTTON,height=t.ICON_BUTTON,bgcolor=t.primary(),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=t.R_SM))))
    return ft.Container(ft.Row([*leading,
        ft.Row(actions,spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER)],
        spacing=t.S16,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=t.WORKBENCH_BAR_HEIGHT)


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
        close=(icon_button(ft.Icons.CLOSE,s.COLLAPSE_IDENTITIES,lambda e:on_close(),size=15)
               if on_close is not None else None)
        rows.append(panel_title(s.IDENTITIES,close))
    return ft.Column([*rows,
        ft.Text(s.IDENTITIES_COUNT.format(count=len(stats)) if diarized else s.IDENTITIES_NONE,
            size=t.TYPE_LABEL,color=t.muted()),
        _diarization_caption(state) or ft.Container(height=0),
        ft.Container(height=t.S8),
        speaker_panel(stats,state.speaker_mapping,colors,on_map,diarized,panel_refs,on_typing,
            on_merge if diarized else None)],spacing=t.S4,expand=True)


def build(state:AppState,on_select:Callable[[int],None],on_play:Callable[[int],None],
          on_export:Callable[[],None],selected_index:int|None,on_page:Callable[[int],None]|None=None,
          refs:dict|None=None,content_width:float|None=None,
          on_locate_audio:Callable[[],None]|None=None,on_dismiss_audio:Callable[[],None]|None=None,
          on_open_find:Callable[[],None]|None=None,
          on_toggle_identities:Callable[[],None]|None=None,identities_hidden:bool=False,
          identities:ft.Control|None=None,order:list[int]|None=None,
          progress:ft.Control|None=None)->ft.Control:
    """The workbench: one toolbar, then the transcript, with the speaker list beside it.

    The speaker list takes the left column at a declared width when there is room for both;
    the open turn is the right-hand pane and is supplied by the shell. Everything that is
    not the transcript is either a fixed width or absent, so the transcript gets whatever is
    left rather than whatever survives.
    """
    stats=speaker_statistics(state.transcript_segments)
    colors=speaker_index(state)

    identity_width=float(t.IDENTITY_PANE_WIDTH) if identities is not None else 0.0
    measure=reading_measure(content_width,identity_width)
    shown=list(range(len(state.transcript_segments))) if order is None else order
    listing=transcript_list(state.transcript_segments,shown,state.speaker_mapping,colors,
        selected_index,on_select,refs,measure)

    column:list[ft.Control]=[]
    # Only what is actionable, and only when it is. On an ordinary transcript the toolbar
    # sits straight on the text.
    if state.audio_missing and not state.audio_banner_dismissed and on_locate_audio and on_dismiss_audio:
        column.append(audio_missing_banner(on_locate_audio,on_dismiss_audio))
    column.append(listing)
    reading=ft.Container(ft.Column(column,spacing=t.S8,expand=True),expand=True,
        padding=ft.Padding(0,0,t.S8 if identities is not None else 0,0),
        clip_behavior=ft.ClipBehavior.HARD_EDGE)

    panes:list[ft.Control]=[reading]
    if identities is not None:
        # Declared width, no expand: a container given both grows to the row and ignores
        # the width, which is how this column once ended up ninety pixels wide.
        # It sits on the far side: the editing pane and the transcript are the two surfaces
        # you look at together, so nothing goes between them.
        panes.append(ft.Container(identities,width=identity_width,
            padding=t.CARD_PADDING,bgcolor=t.surface(),border_radius=t.RADIUS,
            clip_behavior=ft.ClipBehavior.HARD_EDGE))
    return ft.Column([
        _workbench_bar(state,len(stats),on_open_find,on_export,on_toggle_identities,
            identities_hidden,progress,content_width),
        ft.Row(panes,spacing=0,expand=True)],spacing=t.S8,expand=True)


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
        padding=t.S12,border_radius=t.R_SM,bgcolor=t.surface_variant())


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
        hint_text=s.REASSIGN_LABEL,tooltip=s.REASSIGN_TOOLTIP,
        border_radius=t.R_SM,border_color=t.outline(),focused_border_color=t.primary(),
        color=t.on_surface(),content_padding=ft.Padding(t.S12,t.S4,t.S8,t.S4),
        disabled=on_reassign is None or len(speakers)<2,
        options=[ft.DropdownOption(key=speaker,
            text=state.speaker_mapping.get(speaker,speaker)) for speaker in speakers],
        on_focus=(lambda e:on_typing(True)) if on_typing else None,
        on_blur=(lambda e:on_typing(False)) if on_typing else None,
        on_select=(lambda e:on_reassign(index,e.control.value or item.speaker_id)) if on_reassign else None)


def mode_switch(words_mode:bool,on_words_mode:Callable[[],None])->ft.Control:
    """Two named options above the text, instead of one icon among four others.

    Switching between correcting the wording and clicking a word to hear it is the single
    most repeated move on this screen. It was a small unlabelled icon sharing a row with
    revert and play, which made a constant action feel like a hidden one. Here it is a
    labelled switch sitting directly on top of the thing it switches, and Ctrl+K does the
    same without the mouse.
    """
    def option(label:str,active:bool,icon:ft.IconData)->ft.Control:
        # An editor tab, not a pill: square, flush with the surface below it, and marked by
        # a rule along its top edge. The open one is the same colour as the text under it,
        # so the two read as one sheet rather than as a control sitting above a box.
        return ft.Container(ft.Row([ft.Icon(icon,size=14,
                color=t.primary() if active else t.muted()),
            ft.Text(label,size=t.TYPE_LABEL,
                weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
                color=t.on_surface() if active else t.on_surface_variant(),no_wrap=True)],
            spacing=t.S8,tight=True),
            padding=ft.Padding(t.S12,t.S8,t.S12,t.S8),
            bgcolor=t.surface() if active else None,
            border=ft.Border(top=ft.BorderSide(2,t.primary() if active else ft.Colors.TRANSPARENT)),
            ink=True,ink_color=t.primary_soft(),
            on_click=None if active else (lambda e:on_words_mode()))
    strip=ft.Container(ft.Row([option(s.MODE_EDIT,not words_mode,ft.Icons.EDIT_OUTLINED),
        option(s.MODE_WORDS,words_mode,ft.Icons.TOUCH_APP_OUTLINED),
        ft.Container(expand=True)],spacing=0),
        bgcolor=t.surface_variant(),
        border=ft.Border(bottom=ft.BorderSide(t.HAIRLINE,t.outline())))
    return strip


def inspector(state:AppState,index:int|None,on_save:Callable[[int,str],None],on_revert:Callable[[int],None],
              on_play:Callable[[int],None],refs:dict|None=None,
              on_close:Callable[[],None]|None=None,on_seek:Callable[[float],None]|None=None,
              on_typing:Callable[[bool],None]|None=None,
              on_stamp:Callable[[],None]|None=None,
              on_reassign:Callable[[int,str],None]|None=None,
              on_checked:Callable[[int,bool],None]|None=None,
              words_mode:bool=False,on_words_mode:Callable[[],None]|None=None,
              show_original:bool=False,on_show_original:Callable[[],None]|None=None,
              on_locate:Callable[[],None]|None=None,
              on_note:Callable[[int,str],None]|None=None,note_open:bool=False,
              on_toggle_note:Callable[[],None]|None=None,
              on_mark:Callable[[int,int,int,str,str],None]|None=None,
              on_selection_comment:Callable[[int,int,int],None]|None=None,
              on_clear_marks:Callable[[int,int,int],None]|None=None,
              on_drop_mark:Callable[[int,object],None]|None=None,
              highlight_labels:list[str]|None=None)->ft.Control:
    """One turn, shown once.

    The panel holds a single text surface. It is the editor by default and the clickable
    word ribbon when the researcher asks for it — two modes of one block rather than two
    blocks. The untouched original is not shown at all unless the text has actually been
    changed and the researcher asks to compare.
    """
    def heading(title:str)->ft.Control:
        actions:list[ft.Control]=[]
        if on_locate is not None:
            actions.append(icon_button(ft.Icons.MY_LOCATION,s.INSPECTOR_LOCATE,
                lambda e:on_locate(),size=15))
        if on_close is not None:
            actions.append(icon_button(ft.Icons.CLOSE,s.CLOSE_INSPECTOR,lambda e:on_close(),size=15))
        return panel_title(title,ft.Row(actions,spacing=0) if actions else None)

    if index is None or index>=len(state.transcript_segments):
        return ft.Column([heading(s.INSPECTOR_TITLE),
            ft.Text(s.INSPECTOR_EMPTY_BODY,size=t.TYPE_SECONDARY,color=t.on_surface_variant()),
            ft.Text(s.INSPECTOR_EMPTY_HINT,size=t.TYPE_CAPTION,color=t.muted())],spacing=t.S8)
    item=state.transcript_segments[index]
    features=feature_state(state.effective_capabilities)
    colors=speaker_index(state)
    edited=item.corrected_text is not None
    timed=bool(features["word_timestamps"] and item.words and on_seek)

    field=ft.TextField(value=item.text,multiline=True,min_lines=8,max_lines=18,
        text_size=t.TYPE_BODY,border_radius=t.RADIUS,border_color=t.outline(),
        focused_border_color=t.primary(),focused_border_width=1,border_width=1,
        content_padding=ft.Padding(t.S12,t.S8,t.S12,t.S8),color=t.on_surface(),
        on_focus=(lambda e:on_typing(True)) if on_typing else None,
        on_blur=(lambda e:on_typing(False)) if on_typing else None)
    # Every keystroke reports back. Without this the value on the Python side is whatever
    # it was when the box last lost focus, so Ctrl+Enter pressed with the caret still in
    # the box saved the OLD sentence — which is why some edits were kept and some were not.
    field.on_change=lambda e:setattr(field,"value",e.control.value)
    if refs is not None: refs["inspector_field"]=field
    # The one text slot, with its own switch on top. Words mode is only offered when the
    # provider actually timed the words.
    slot:list[ft.Control]=[]
    if timed and on_words_mode is not None:
        slot.append(mode_switch(words_mode,on_words_mode))
    slot.append(word_ribbon(item,on_seek) if (words_mode and timed) else field)
    # STRETCH here as well. Fixing only the outer column left the box inside this one at
    # its intrinsic width, which is why widening the panel changed nothing twice over: a
    # Column's alignment does not reach through a Column nested inside it.
    surface=ft.Column(slot,spacing=t.S8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    checked=ft.Checkbox(s.MARK_CHECKED,value=item.checked,tooltip=s.MARK_CHECKED_TOOLTIP,
        active_color=t.primary(),check_color=t.on_primary(),
        label_style=ft.TextStyle(size=t.TYPE_LABEL,color=t.on_surface_variant()),
        disabled=on_checked is None,
        on_change=(lambda e:on_checked(index,bool(e.control.value))) if on_checked else None)
    if refs is not None: refs["inspector_checked"]=checked

    # Marking a phrase: bold, one of three highlighters, or a comment on those words alone.
    # Offered only in the editor, because a selection is what it acts on and the word ribbon
    # has no selection — its words are buttons that seek the recording.
    marks=list(getattr(item,"annotations",None) or [])
    marking_offered=on_mark is not None and not (words_mode and timed)
    if marking_offered:
        surface.controls.append(marking(field,marks,highlight_labels,
            lambda a,b,kind,slot:on_mark(index,a,b,kind,slot),
            (lambda a,b:on_selection_comment(index,a,b)) if on_selection_comment else (lambda a,b:None),
            (lambda a,b:on_clear_marks(index,a,b)) if on_clear_marks else (lambda a,b:None),
            refs))

    rule=lambda:ft.Container(height=t.HAIRLINE,bgcolor=t.outline())

    # Who said it, and when. The panel could say everything about a turn except the one
    # thing checked first and by ear — where in the recording it is. The stamp is the play
    # control now, which also takes an unlabelled icon out of the row below.
    name=apply_speaker_mapping(item,state.speaker_mapping)
    stamp=ft.Container(ft.Row([ft.Icon(ft.Icons.PLAY_ARROW,size=13,color=t.primary()),
            ft.Text(f"{format_timestamp(item.absolute_start)}–{format_timestamp(item.absolute_end)}",
                size=t.TYPE_CAPTION,font_family=t.MONO,color=t.on_surface_variant(),no_wrap=True)],
            spacing=3,tight=True,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(t.S8,3,t.S8,3),border_radius=t.R_SM,bgcolor=t.surface_variant(),
        ink=True,ink_color=t.primary_soft(),tooltip=s.PLAY_RANGE,
        on_click=lambda e:on_play(index))

    # One line of provenance where four used to stack. The raw diarization label appears
    # only when it differs from the name; until it is renamed it is the same fact twice.
    facts=[s.INSPECTOR_POSITION.format(index=index+1,total=len(state.transcript_segments))]
    # The raw diarization label only earns its place where labels are per fragment and
    # matching a turn to one is part of the work. On a global transcript the name says it,
    # and the Speakers pane lists the raw label under every name anyway.
    if features["speaker_reconciliation"]: facts.append(item.speaker_id)
    if features["confidence_display"] and item.confidence is not None:
        facts.append(s.INSPECTOR_CONFIDENCE.format(percent=int(item.confidence*100)))
    if features["word_timestamps"] and item.words:
        facts.append(s.INSPECTOR_WORDS.format(count=len(item.words)))

    # Save sits directly under the box it saves, taking the width, with the two corrections
    # that undo or time-stamp it beside. It used to come after the marking preview and the
    # comment list, which on a marked turn put the screen's most repeated action below the
    # fold of its own panel.
    save=secondary_button(s.SAVE_CORRECTION,lambda e:on_save(index,field.value or ""),
        ft.Icons.CHECK,disabled=words_mode)
    save.expand=True; save.tooltip=s.SAVE_CORRECTION_TOOLTIP
    committing=ft.Row([save,
        icon_button(ft.Icons.SCHEDULE,s.INSERT_TIMESTAMP,
            (lambda e:on_stamp()) if on_stamp else None,disabled=on_stamp is None or words_mode),
        icon_button(ft.Icons.RESTORE,s.REVERT_CORRECTION,lambda e:on_revert(index))],
        spacing=t.S4,vertical_alignment=ft.CrossAxisAlignment.CENTER)

    body:list[ft.Control]=[
        heading(s.INSPECTOR_TITLE),
        ft.Row([ft.Container(width=8,height=8,border_radius=t.R_PILL,
                bgcolor=t.speaker_color(colors.get(item.speaker_id,0))),
            ft.Text(name,size=t.TYPE_BODY,weight=ft.FontWeight.W_600,color=t.on_surface(),
                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS,expand=True),stamp],
            spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([ft.Text(" · ".join(facts),size=t.TYPE_CAPTION,color=t.muted(),
                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS,expand=True),checked],
            spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        rule(),
        surface,
        committing]

    # What the marking produced, read after the text rather than before the save button.
    if marking_offered and marks:
        body.append(ft.Text(s.MARK_PREVIEW,size=t.TYPE_CAPTION,color=t.muted()))
        body.append(mark_preview(item.text,marks,highlight_labels))
        body.extend(comment_list(marks,(lambda m:on_drop_mark(index,m)) if on_drop_mark else None))

    # Everything below the rule is occasional: the turn belongs to someone else, it needs a
    # note, or the original wording is worth a look. None of it is in the way of correcting.
    occasional:list[ft.Control]=[]
    row:list[ft.Control]=[
        ft.Text(s.REASSIGN_LABEL,size=t.TYPE_CAPTION,color=t.muted(),no_wrap=True),
        _reassign_dropdown(item,state,index,on_reassign,on_typing)]
    if on_toggle_note is not None:
        carries=bool((item.note or "").strip())
        row.append(icon_button(ft.Icons.COMMENT if carries else ft.Icons.ADD_COMMENT_OUTLINED,
            s.NOTE_PRESENT if carries else s.NOTE_ADD,lambda e:on_toggle_note(),
            color=t.primary() if carries else None))
    occasional.append(ft.Row(row,spacing=t.S4,vertical_alignment=ft.CrossAxisAlignment.CENTER))
    # Labelled, not a third icon in the row above: it only appears on a turn that has been
    # changed, and on that turn it is worth being able to read what it does.
    if edited and on_show_original is not None:
        occasional.append(ft.Row([tertiary_button(
            s.HIDE_ORIGINAL if show_original else s.SHOW_ORIGINAL,
            lambda e:on_show_original(),ft.Icons.HISTORY_TOGGLE_OFF)],spacing=0))
    if edited and show_original:
        occasional.append(ft.Container(ft.Text(item.original_text,size=t.TYPE_SECONDARY,
            color=t.on_surface_variant(),selectable=True),padding=t.S12,
            bgcolor=t.surface_variant(),border_radius=t.R_SM))
    if on_note is not None and (note_open or (item.note or "").strip()):
        note=ft.TextField(label=s.NOTE_LABEL,value=item.note,multiline=True,min_lines=2,max_lines=5,
            text_size=t.TYPE_SECONDARY,border_radius=t.R_SM,border_color=t.outline(),
            focused_border_color=t.primary(),color=t.on_surface(),
            label_style=ft.TextStyle(size=t.TYPE_LABEL,color=t.muted()),
            on_focus=(lambda e:on_typing(True)) if on_typing else None,
            on_blur=(lambda e:on_typing(False)) if on_typing else None)
        note.on_change=lambda e:(setattr(note,"value",e.control.value),on_note(index,e.control.value))[0]
        if refs is not None: refs["inspector_note"]=note
        occasional.append(note)
        occasional.append(ft.Text(s.NOTE_HINT,size=t.TYPE_CAPTION,color=t.muted()))
    body.append(rule())
    body.extend(occasional)
    # STRETCH, not the default START. A Column left to itself gives every child its
    # intrinsic width, so the editing box sat at whatever a TextField asks for — about
    # three hundred pixels — no matter how wide the panel around it grew. Widening the
    # panel could never have fixed it; this is the line that does.
    return ft.Column(body,spacing=t.S8,scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
