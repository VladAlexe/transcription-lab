"""The transcript: one raised surface, rows separated by air, no page numbers.

A turn shows its whole first two lines. It used to show one line clipped to about thirty
characters, which on a three-column window meant every row ended in an ellipsis — the
transcript was the one thing in the application you could not read.

Three things can be true of a row at once and each has its own channel, so they never
collide: the turn being **heard** is tinted with the accent, the turn **open** in the panel
sits on a lighter fill, and a turn already **reviewed** carries an accent bar on its edge.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from document_export import format_timestamp
from models import TranscriptSegment
from speaker_reconciliation import apply_speaker_mapping


def carries_marks(item:TranscriptSegment)->bool:
    """Whether this turn holds anything a researcher put there beyond the wording itself."""
    return bool(getattr(item,"annotations",None) or (getattr(item,"note","") or "").strip())


def checked_border(checked:bool)->ft.Border:
    """The reviewed marker. Always drawn, only ever recoloured, so checking a turn cannot
    shift its text sideways — and it is an edge, which nothing else on a row uses."""
    return ft.Border(left=ft.BorderSide(t.CHECK_RULE,
        t.primary() if checked else ft.Colors.TRANSPARENT))


def row_state(parts:dict,selected:bool|None=None,playing:bool|None=None,
              checked:bool|None=None)->None:
    """Repaint one row from its three flags. One function, so two states can never fight
    over the same property."""
    for key,value in (("selected",selected),("playing",playing),("checked",checked)):
        if value is not None: parts[key]=value
    container=parts["container"]
    container.bgcolor=(t.primary_soft() if parts.get("playing")
                       else t.surface_variant() if parts.get("selected") else None)
    container.border=checked_border(bool(parts.get("checked")))


def transcript_item(index:int,item:TranscriptSegment,mapping:dict[str,str],color:str,selected:bool,
                    measure:float,on_select:Callable[[int],None],refs:dict|None=None)->ft.Control:
    stamp=ft.Text(format_timestamp(item.absolute_start),size=t.TYPE_META,color=t.muted(),
        font_family=t.MONO,no_wrap=True)
    dot=ft.Container(width=7,height=7,bgcolor=color,border_radius=t.R_PILL)
    speaker=ft.Text(apply_speaker_mapping(item,mapping),size=t.TYPE_META,
        weight=ft.FontWeight.W_500,color=t.on_surface_variant(),
        max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)
    # A turn that carries a mark or a note says so on its own line. Without this the only
    # way to find a phrase you highlighted an hour ago was to open every turn in turn.
    marked=ft.Icon(ft.Icons.BOOKMARK,size=12,color=t.accent_warm(),
        tooltip=s.TURN_MARKED,visible=carries_marks(item))
    meta=ft.Row([stamp,dot,speaker,marked],spacing=t.S8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)
    body=ft.Text(item.text,size=t.TYPE_BODY,color=t.on_surface(),
        max_lines=t.TURN_LINES,overflow=ft.TextOverflow.ELLIPSIS)
    body.style=ft.TextStyle(height=t.LINE_HEIGHT)
    reading=ft.Container(ft.Column([meta,body],spacing=t.S4),width=measure)
    container=ft.Container(ft.Row([reading,ft.Container(expand=True)],spacing=0),
        padding=ft.Padding(t.S12,t.TURN_PADDING,t.S12,t.TURN_PADDING),
        margin=ft.Margin(0,0,0,t.TURN_GAP),border_radius=t.RADIUS,
        ink=True,ink_color=t.primary_soft(),
        on_click=lambda e:on_select(index))
    parts={"speaker":speaker,"body":body,"container":container,"marker":dot,"color":color,
           "marked":marked,
           "segment":item,"selected":selected,"playing":False,"checked":item.checked}
    row_state(parts)
    if refs is not None: refs[index]=parts
    return container


def paint_turn(parts:dict,item:TranscriptSegment,word:int|None,active:bool)->None:
    """Show where playback is: the active word when it was timed, the whole turn otherwise."""
    body=parts["body"]
    row_state(parts,playing=active)
    words=getattr(item,"words",None) or []
    if not (active and word is not None and words):
        body.spans=None
        body.value=item.text
        return
    # `corrected_text` no longer matches the timed words, so only the original is word-synced.
    body.value=None
    body.spans=[ft.TextSpan(f"{entry.text} ",
        style=ft.TextStyle(color=t.on_surface(),height=t.LINE_HEIGHT,
            bgcolor=t.primary_soft() if position==word else None,
            weight=ft.FontWeight.W_600 if position==word else ft.FontWeight.W_400))
        for position,entry in enumerate(words)]


def transcript_list(segments:list[TranscriptSegment],order:list[int],mapping:dict[str,str],
                    speaker_index:dict[str,int],selected_index:int|None,
                    on_select:Callable[[int],None],refs:dict|None=None,
                    measure:float=t.TRANSCRIPT_MEASURE)->ft.Control:
    """`order` is every transcript index the list shows, already filtered.

    All of them, in one scrolling surface. There are no pages: the list is virtualised and
    every row is the same height, so three hundred turns cost the same as thirty and the
    researcher never has to ask which quarter of the interview they are looking at.

    `refs` is the screen's registry, and this owns two separate places in it. `refs["rows"]`
    is keyed by transcript index and holds NOTHING ELSE — callers walk those keys comparing
    them to a segment count, so a string key in there is a crash.
    """
    row_refs=refs.setdefault("rows",{}) if refs is not None else None
    colors={key:t.speaker_color(value) for key,value in speaker_index.items()}
    rows=[transcript_item(index,segments[index],mapping,
        colors.get(segments[index].speaker_id,t.speaker_color(0)),
        selected_index==index,measure,on_select,row_refs) for index in order]

    if not order:
        empty=ft.Container(ft.Text(s.ALL_CHECKED,size=t.TYPE_BODY,color=t.muted()),
            padding=t.S32,alignment=ft.Alignment.CENTER,expand=True)
        return ft.Container(empty,expand=True,bgcolor=t.surface(),border_radius=t.RADIUS)

    listing=ft.ListView(rows,spacing=0,expand=True,item_extent=t.TRANSCRIPT_ROW_HEIGHT,
        build_controls_on_demand=True)
    if refs is not None:
        refs["listing"]=listing; refs["page_order"]=order; refs["page_offset"]=0
    # The raised surface the whole transcript sits on: one card, not a card per row.
    return ft.Container(listing,expand=True,bgcolor=t.surface(),border_radius=t.RADIUS,
        padding=ft.Padding(t.S8,t.S12,t.S8,t.S4),clip_behavior=ft.ClipBehavior.HARD_EDGE)
