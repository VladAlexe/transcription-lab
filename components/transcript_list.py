"""The transcript: a dense list you scan, not a document you read in.

One turn is a meta line and a single line of speech. The whole turn is one click away in the
inspector beside it, so paying four lines of screen for every turn buys nothing and costs the
researcher a page-down every few seconds.

Three things can be true of a row at once, so each gets its own channel and they never
collide: the turn being **heard** is filled in sage, the turn **open** in the inspector is
filled in neutral grey, and a turn already **reviewed** carries a sage bar on its left edge.
"""
from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import secondary_button
from document_export import format_timestamp
from models import TranscriptSegment
from speaker_reconciliation import apply_speaker_mapping


def checked_border(checked:bool)->ft.Border:
    """The reviewed marker. Always drawn, only ever recoloured, so checking a turn cannot
    shift its text sideways — and it is an edge, which nothing else on a row uses."""
    return ft.Border(left=ft.BorderSide(t.CHECK_RULE,
        t.primary() if checked else ft.Colors.TRANSPARENT))


def row_state(parts:dict,selected:bool|None=None,playing:bool|None=None,
              checked:bool|None=None)->None:
    """Repaint one row from its three flags. One function, so two states can never fight
    over the same property — which is exactly what happened when selection and playback
    both wrote the background."""
    for key,value in (("selected",selected),("playing",playing),("checked",checked)):
        if value is not None: parts[key]=value
    container=parts["container"]
    container.bgcolor=(t.primary_soft() if parts.get("playing")
                       else t.surface_variant() if parts.get("selected") else None)
    container.border=checked_border(bool(parts.get("checked")))


def transcript_item(index:int,item:TranscriptSegment,mapping:dict[str,str],color:str,selected:bool,
                    measure:float,on_select:Callable[[int],None],refs:dict|None=None)->ft.Control:
    speaker=ft.Text(apply_speaker_mapping(item,mapping),size=t.TYPE_CAPTION,weight=ft.FontWeight.W_600,
        color=t.on_surface_variant(),max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)
    body=ft.Text(item.text,size=t.TYPE_BODY,color=t.on_surface(),
        max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)
    body.style=ft.TextStyle(height=t.LINE_HEIGHT)
    stamp=ft.Text(format_timestamp(item.absolute_start),size=t.TYPE_MONO,color=t.muted(),
        font_family="Consolas",no_wrap=True)
    dot=ft.Container(width=7,height=7,bgcolor=color,border_radius=t.R_PILL)
    # The measure caps the text, not the row: long turns stay readable instead of running wide.
    reading=ft.Container(ft.Column([
        ft.Row([dot,speaker],spacing=t.S8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        body],spacing=2),width=measure)
    container=ft.Container(ft.Row([
        ft.Container(stamp,width=t.TIMESTAMP_GUTTER,padding=ft.Padding(0,2,0,0)),
        reading,ft.Container(expand=True)],
        vertical_alignment=ft.CrossAxisAlignment.START,spacing=t.S12),
        padding=ft.Padding(t.S12,t.TURN_PADDING,t.S8,t.TURN_PADDING),
        margin=ft.Margin(0,0,0,t.TURN_GAP),border_radius=t.R_SM,
        # A row answers the pointer before it is clicked; the ripple is the click itself.
        ink=True,ink_color=t.primary_soft(),
        on_click=lambda e:on_select(index))
    parts={"speaker":speaker,"body":body,"container":container,"marker":dot,"color":color,
           "segment":item,"selected":selected,"playing":False,"checked":item.checked}
    row_state(parts)
    if refs is not None: refs[index]=parts
    return container


def paint_turn(parts:dict,item:TranscriptSegment,word:int|None,active:bool)->None:
    """Show where playback is: the active word when it was timed, the whole turn otherwise.

    Called on every position tick, so it mutates the existing controls rather than rebuilding.
    """
    body=parts["body"]
    row_state(parts,playing=active)
    words=getattr(item,"words",None) or []
    if not (active and word is not None and words):
        # No word timings — or not the active turn: plain text, turn-level highlight only.
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
                    speaker_index:dict[str,int],selected_index:int|None,offset:int,page_size:int,
                    on_select:Callable[[int],None],on_page:Callable[[int],None],
                    refs:dict|None=None,measure:float=t.TRANSCRIPT_MEASURE)->ft.Control:
    """`order` is the list of transcript indices to show, already filtered.

    Indices rather than segments: with "show only unchecked" on, a row still selects, seeks
    and saves against its real position in the interview rather than a position in a view.
    """
    page=order[offset:offset+page_size]
    colors={key:t.speaker_color(value) for key,value in speaker_index.items()}
    rows=[transcript_item(index,segments[index],mapping,
        colors.get(segments[index].speaker_id,t.speaker_color(0)),
        selected_index==index,measure,on_select,refs) for index in page]

    # Sticky speaker header. Rows share one fixed extent, so the top row is exact arithmetic
    # rather than a guess, and the current speaker stays visible through long turns.
    first=segments[page[0]] if page else None
    sticky_dot=ft.Container(width=7,height=7,border_radius=t.R_PILL,
        bgcolor=colors.get(first.speaker_id,t.speaker_color(0)) if first else t.muted())
    sticky_name=ft.Text(apply_speaker_mapping(first,mapping) if first else "",size=t.TYPE_LABEL,
        weight=ft.FontWeight.W_500,color=t.on_surface_variant())
    sticky=ft.Container(ft.Row([ft.Text(s.NOW_SPEAKING,size=t.TYPE_CAPTION,color=t.muted()),sticky_dot,sticky_name,
        ft.Container(expand=True)],spacing=t.S8),padding=ft.Padding(t.S12,t.S4,t.S12,t.S4),
        border=ft.Border(bottom=ft.BorderSide(t.HAIRLINE,t.outline())),visible=bool(page))

    def follow(event:ft.Event)->None:
        pixels=getattr(event,"pixels",None)
        if pixels is None or not page: return
        position=min(len(page)-1,max(0,int(pixels/t.TRANSCRIPT_ROW_HEIGHT)))
        item=segments[page[position]]; label=apply_speaker_mapping(item,mapping)
        if sticky_name.value==label: return
        sticky_name.value=label; sticky_dot.bgcolor=colors.get(item.speaker_id,t.speaker_color(0))
        try: sticky.update()
        except Exception: pass

    listing=ft.ListView(rows,spacing=0,expand=True,item_extent=t.TRANSCRIPT_ROW_HEIGHT,
        build_controls_on_demand=True,on_scroll=follow,scroll_interval=120)
    if refs is not None: refs["listing"]=listing; refs["page_offset"]=offset; refs["page_order"]=page
    total_pages=max(1,(len(order)+page_size-1)//page_size); current=offset//page_size+1
    pager=ft.Row([secondary_button(s.PAGE_PREVIOUS,lambda e:on_page(max(0,offset-page_size)),disabled=offset==0),
        ft.Text(s.PAGE_POSITION.format(current=current,total=total_pages),size=t.TYPE_LABEL,color=t.muted()),
        secondary_button(s.PAGE_NEXT,lambda e:on_page(offset+page_size),disabled=offset+page_size>=len(order))],
        alignment=ft.MainAxisAlignment.CENTER,spacing=t.S16)
    if not order:
        empty=ft.Container(ft.Text(s.ALL_CHECKED,size=t.TYPE_SECONDARY,color=t.muted()),
            padding=t.S24,alignment=ft.Alignment.CENTER,expand=True)
        return ft.Column([sticky,empty],spacing=0,expand=True)
    # No frame around the list: whitespace separates it from the page, a hairline marks the header.
    return ft.Column([sticky,ft.Container(listing,expand=True,padding=ft.Padding(0,t.S12,0,t.S8)),pager],
        spacing=0,expand=True)
