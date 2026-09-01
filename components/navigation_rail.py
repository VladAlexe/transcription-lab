from __future__ import annotations
from typing import Callable
import flet as ft
import design_tokens as t
import strings as s
from components.buttons import icon_button
from app_state import AppState
from components.brand import wordmark

# The waveform belongs to the wordmark alone; navigation uses plain functional icons.
DESTINATIONS=((s.NAV_RECORDING,ft.Icons.AUDIO_FILE_OUTLINED),(s.NAV_TRANSCRIPTION,ft.Icons.AUTO_AWESOME_OUTLINED),
              (s.NAV_SPEAKERS,ft.Icons.PEOPLE_OUTLINE),(s.NAV_EXPORT,ft.Icons.IOS_SHARE_OUTLINED))


def navigation_rail(state:AppState,on_navigate:Callable[[int],None],on_new:Callable[[],None],
                    on_save:Callable[[],None],on_open:Callable[[],None],
                    minimised:bool=False,on_minimise:Callable[[],None]|None=None)->ft.Control:
    items:list[ft.Control]=[]
    for index,(label,icon) in enumerate(DESTINATIONS):
        available=index==0 or index==1 and state.selected_file_metadata is not None or index>=2 and bool(state.transcript_segments)
        complete=((index==0 and state.selected_file_metadata is not None) or (index==1 and bool(state.transcript_segments))
                  or (index==2 and state.current_workflow_step>2))
        selected=state.current_workflow_step==index
        row:list[ft.Control]=[ft.Icon(icon,size=20,color=t.primary() if selected else t.muted())]
        if not minimised:
            row.append(ft.Text(label,size=t.TYPE_SECONDARY,color=t.on_surface() if selected else t.on_surface_variant(),
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                max_lines=1,no_wrap=True,expand=True))
            row.append(ft.Icon(ft.Icons.CHECK_CIRCLE,size=13,color=t.success()) if complete else ft.Container(width=13))
        # A soft filled pill marks the current step; everything else stays neutral.
        items.append(ft.Container(ft.Row(row,spacing=t.S12,
            alignment=ft.MainAxisAlignment.CENTER if minimised else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),height=t.NAV_ITEM_HEIGHT,
            padding=ft.Padding(t.NAV_ITEM_PADDING,0,t.NAV_ITEM_PADDING,0),
            margin=ft.Margin(0,0,0,t.NAV_ITEM_GAP),
            bgcolor=t.primary_soft() if selected else None,border_radius=t.NAV_PILL_RADIUS,
            opacity=1 if available else .4,
            tooltip=label if available else s.NAV_LOCKED.format(step=label),
            on_click=(lambda e,i=index:on_navigate(i)) if available else None))

    def rail_action(icon:ft.IconData,tooltip:str,handler:Callable[[],None],disabled:bool=False)->ft.Control:
        return icon_button(icon,tooltip,lambda e:handler(),size=20,color=t.muted(),disabled=disabled)

    buttons=[rail_action(ft.Icons.FOLDER_OPEN,s.OPEN_PROJECT,on_open),
        rail_action(ft.Icons.SAVE_OUTLINED,s.SAVE_PROJECT,on_save,not bool(state.transcript_segments)),
        rail_action(ft.Icons.ADD,s.NEW_PROJECT,on_new)]
    if on_minimise is not None:
        buttons.append(rail_action(ft.Icons.CHEVRON_RIGHT if minimised else ft.Icons.CHEVRON_LEFT,
            s.EXPAND_SIDEBAR if minimised else s.COLLAPSE_SIDEBAR,on_minimise))
    actions=(ft.Column(buttons,spacing=0,horizontal_alignment=ft.CrossAxisAlignment.CENTER) if minimised
             else ft.Row(buttons,spacing=t.S4))
    # The pill is inset from both rail edges, so it never runs into the border.
    body=ft.Column([ft.Container(ft.Column(items,spacing=0),
            padding=ft.Padding(t.NAV_PILL_INSET,t.S16,t.NAV_PILL_INSET,0)),
        ft.Container(expand=True),
        ft.Container(actions,padding=ft.Padding(t.NAV_PILL_INSET,0,t.NAV_PILL_INSET,t.S12))],
        spacing=0,expand=True)
    return ft.Container(ft.Column([wordmark(minimised),body],spacing=0,expand=True),
        bgcolor=t.surface(),border=ft.Border(right=ft.BorderSide(1,t.outline())))
