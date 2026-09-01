"""The application shell: one row, three panes, arithmetic that cannot overflow.

The root is a single Row bounded to the page width with no horizontal scrolling anywhere,
so a pane can only be too narrow, never pushed past the right edge.

The inner content column is the parent of every screen body. It carries a fixed width and
deliberately does NOT expand: a Flet container given both `width` and `expand=True` inside a
Row grows to the row instead of honouring the width, which is what let screen bodies spill
past the workspace.
"""
from __future__ import annotations
from dataclasses import dataclass
import flet as ft
import design_tokens as t
from components import overlay


@dataclass(frozen=True)
class Layout:
    page_width: float
    nav: float
    workspace: float
    inspector: float
    content: float
    docked_inspector: bool
    sheet_open: bool
    gutter: float = t.CONTENT_GUTTER
    wide: bool = False

    @property
    def total(self) -> float: return self.nav + self.workspace + self.inspector

    @property
    def fits(self) -> bool: return self.total <= self.page_width + .5

    @property
    def body(self) -> float:
        """Width available to the screen body once an open sheet has taken its share."""
        return self.workspace - (t.INSPECTOR_WIDTH if self.sheet_open else 0.0)

    def describe(self) -> str:
        mode = "docked" if self.docked_inspector else ("sheet" if self.sheet_open else "hidden")
        return (f"page={self.page_width:.0f} nav={self.nav:.0f} workspace={self.workspace:.0f} "
                f"inspector={self.inspector:.0f} sum={self.total:.0f} "
                f"({'fits' if self.fits else 'OVERFLOW'}) body={self.body:.0f} "
                f"content={self.content:.0f} gutter={self.gutter:.0f} "
                f"mode={'workbench' if self.wide else 'document'} inspector={mode}")


def measure(page_width:float|None,wants_inspector:bool,inspector_open:bool=False,
            nav_minimised:bool=False,wide:bool=False)->Layout:
    """Split the page width into panes. The workspace absorbs whatever is left.

    `wide` switches the content column from document to workbench: a document is capped at a
    readable measure and centred, a workbench takes the desk it is given. The review screen
    is the only workbench, and the text inside it is capped separately by TRANSCRIPT_MEASURE.
    """
    width=float(page_width or t.INSPECTOR_BREAKPOINT)
    rail=t.NAV_MINIMISED if nav_minimised else t.NAV_WIDTH
    docked=wants_inspector and width>=rail+t.WORKSPACE_MIN+t.INSPECTOR_WIDTH
    sheet=wants_inspector and inspector_open and not docked
    inspector=t.INSPECTOR_WIDTH if docked else 0.0
    nav=min(rail,max(0.0,width))
    workspace=max(0.0,width-nav-inspector)
    # An open sheet takes its width out of the body, so nothing is ever painted underneath it.
    body=max(0.0,workspace-(t.INSPECTOR_WIDTH if sheet else 0.0))
    gutter=float(t.WORKBENCH_GUTTER if wide else t.CONTENT_GUTTER)
    room=body-2*gutter
    content=max(1.0,room if wide else min(t.MAX_CONTENT,room))
    return Layout(width,nav,workspace,inspector,content,docked,sheet,gutter,wide)


def _inspector_pane(inspector:ft.Control,width:float)->ft.Container:
    """A solid right-hand sheet: opaque surface, own border, never see-through."""
    return ft.Container(inspector,width=width,padding=t.CARD_PADDING,bgcolor=t.surface(),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border=ft.Border(left=ft.BorderSide(1,t.outline_strong())))


def app_shell(nav:ft.Control,top:ft.Control,workspace:ft.Control,inspector:ft.Control|None,
              layout:Layout,refs:dict|None=None,scrollable:bool=True,
              footer:ft.Control|None=None,overlays:list[ft.Control]|None=None)->ft.Control:
    column=ft.Column([workspace],spacing=0,expand=True,
        scroll=ft.ScrollMode.AUTO if scrollable else None)
    # Fixed width, centred, NOT expanding — see the module docstring.
    host=ft.Container(column,width=layout.content)
    if refs is not None: refs["content_host"]=host
    body=ft.Row([host],alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,expand=True)
    # A workbench starts nearer the top: its first row is a toolbar, not a page heading.
    top_pad=t.S16 if layout.wide else t.S32
    field=ft.Container(body,padding=ft.Padding(layout.gutter,top_pad,layout.gutter,t.S16),
        expand=True,clip_behavior=ft.ClipBehavior.HARD_EDGE)

    # Transient tools live here and nowhere else: stacked over the content area, positioned,
    # never in the flow. With none open this is the same `field` object as above, so the
    # content cannot have shifted. The stack stops short of the inspector, which is a real
    # pane rather than something to be floated over.
    if overlays:
        field=overlay.stack(field,overlays)
        if refs is not None: refs["overlay_stack"]=field

    if inspector is not None and layout.sheet_open:
        # Side by side, not stacked: the body is already narrower by exactly the sheet's width.
        field=ft.Row([ft.Container(field,width=layout.body,expand=False,clip_behavior=ft.ClipBehavior.HARD_EDGE),
            _inspector_pane(inspector,t.INSPECTOR_WIDTH)],spacing=0,expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        if refs is not None: refs["inspector_sheet"]=field.controls[1]

    # The footer is pinned under the workspace: a slim bar, outside the scrolling content.
    stack:list[ft.Control]=[top,field]
    if footer is not None: stack.append(footer)
    center=ft.Container(ft.Column(stack,spacing=0,expand=True),
        width=layout.workspace,clip_behavior=ft.ClipBehavior.HARD_EDGE)
    if refs is not None: refs["workspace_pane"]=center
    panes:list[ft.Control]=[ft.Container(nav,width=layout.nav,clip_behavior=ft.ClipBehavior.HARD_EDGE),center]
    if inspector is not None and layout.docked_inspector:
        docked=_inspector_pane(inspector,layout.inspector)
        if refs is not None: refs["inspector_sheet"]=docked
        panes.append(docked)
    return ft.Container(ft.Row(panes,spacing=0,expand=True,vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        bgcolor=t.background(),expand=True,clip_behavior=ft.ClipBehavior.HARD_EDGE)
