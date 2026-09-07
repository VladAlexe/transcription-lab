from __future__ import annotations
import os,time
from pathlib import Path
from urllib.parse import parse_qs,urlparse
import flet as ft
import flet_audio as fa
import design_tokens as t
import annotations as an
from audio_player import AudioPlayer
import strings as s
from app_controller import AppController
from app_state import ExportMetadata
import layout_audit
from components.app_shell import Layout,app_shell,measure
from components.buttons import primary_button,tertiary_button
from components.audio_transport import audio_transport
from components.transcript_list import carries_marks,paint_turn,row_state
import find_replace
import playback_sync
import review_progress
from components.find_replace_bar import find_replace_bar,match_summary as find_replace_summary
from components import overlay
from components.dialogs import confirm_dialog,error_notification,message_dialog,missing_ffmpeg_dialog,modal_dialog,notification
from components.navigation_rail import navigation_rail
from components.status_bar import status_bar
from components.review_strip import label_for,review_strip
from components.top_bar import save_status,top_bar,window_chrome
from media_tools import resolve_media_tools
from models import AudioInfo,MediaToolPaths,TranscriptSegment
from providers import DEFAULT_PROVIDER
from document_export import format_timestamp
from speaker_reconciliation import apply_speaker_mapping,speaker_statistics
from theme import application_theme
from time_range import TimeRangeError,resolve
import window_icon
from flet.controls.core.text import TextSelection
from utils import human_size,load_preferences,save_preferences
from views import export_view,recording_view,settings_view,speakers_view,transcription_view,welcome_view


class DesktopApp:
    def __init__(self,page:ft.Page):
        self.page=page;self.controller=AppController();self.show_settings=False;self.show_home=False;self.selected_segment:int|None=None;self.transcript_offset=0
        self.started_at:float|None=None;self.file_picker=ft.FilePicker();self.preferences=load_preferences()
        # References to live controls, refreshed on every full render and used for targeted updates.
        self.refs:dict={};self.nav_minimised=True;self._restore_fitted=False;self.panel_collapsed=False;self.typing=False;self.active=playback_sync.Position()
        self.find_open=False;self.find_term="";self.find_replacement=""
        self.placement=speakers_view.pane_placement(t.MAX_CONTENT,True)
        # Inspector view modes: the one text slot shows the editor or the clickable words,
        # and the untouched original only when asked for.
        self.words_mode=False;self.show_original=False;self.note_open=False
        # The open turn tracks the audio unless the researcher turns it off.
        self.follow_playback=True
        # Marking a turn writes the project back, throttled so holding Ctrl+Enter down
        # cannot turn a 3 MB write into a stutter on every turn.
        self._last_autosave=0.0;self._autosave_pending=False
        self.find_options=find_replace.Options()
        # One Audio service for the whole session. In Flet 0.86 audio ships in `flet-audio` and
        # Audio is a Service, so it is attached to page.services rather than page.controls.
        # No placeholder service. Bisection result: an Audio(src=None) attached at build time
        # stops any later Audio from ever loading — no on_loaded, no duration, transport calls
        # time out. The service is created only when there is a real recording to play.
        self.audio=None
        self.player=AudioPlayer(self.audio,self.page.run_task,lambda message:print(message,flush=True),
            factory=self.new_audio_service,attach=self.attach_audio_service,detach=self.detach_audio_service)
        self.player.on_change=self.refresh_transport
        self.player.on_position=self.sync_highlight
        self.controller.state.first_run=not bool(self.preferences.get("welcome_seen",False))
        self.controller.state.settings.appearance=str(self.preferences.get("appearance","light"))
        self.controller.state.settings.user_media_tool_path=str(self.preferences.get("media_tool_path",""))
        self.controller.state.settings.provider=str(self.preferences.get("provider",DEFAULT_PROVIDER))
        self.controller.state.settings.language=str(self.preferences.get("language","ro"))
        # Preferences never hold API keys; only configuration choices.
        try:self.controller.state.settings.expected_speakers=int(self.preferences.get("expected_speakers") or 0)
        except (TypeError,ValueError):self.controller.state.settings.expected_speakers=0
        settings=self.controller.state.settings
        try:settings.type_scale=float(self.preferences.get("type_scale",1.0))
        except (TypeError,ValueError):settings.type_scale=1.0
        t.set_type_scale(settings.type_scale)
        settings.auto_rewind_enabled=bool(self.preferences.get("auto_rewind_enabled",True))
        try:settings.auto_rewind_seconds=max(0.0,min(float(self.preferences.get("auto_rewind_seconds",1.5)),5.0))
        except (TypeError,ValueError):settings.auto_rewind_seconds=1.5
        stored=self.preferences.get("highlight_labels")
        if isinstance(stored,list):
            settings.highlight_labels=[str(name)[:40] for name in (stored+["","",""])[:3]]
        settings.reviewer=str(self.preferences.get("reviewer","") or "")[:80]
        self.apply_rewind()
        self.controller.state.media_tools=resolve_media_tools([self.controller.state.settings.user_media_tool_path])
        query=parse_qs(urlparse(page.route).query);query_screen=query.get("screen",[""])[0]
        if query.get("dark",[""])[0]=="1":self.controller.state.settings.appearance="dark"
        self._configure_visual_demo(os.environ.get("TRANSCRIBER_DEMO_SCREEN","") or os.environ.get("TRANSCRIERE_DEMO_SCREEN","") or query_screen)
        self.configure_page();self.render();self.fit_restore_size()
        # Cosmetic and guarded: `flet run` uses a prebuilt client, so the taskbar shows that
        # executable's icon until ours is attached to the live window handle.
        window_icon.apply_in_background(s.APP_NAME,Path(__file__).resolve().parent/"assets"/"icon.ico",
            lambda message:print(message,flush=True))
        if not self.controller.state.media_tools.is_valid:self.show_missing_tools()

    def _configure_visual_demo(self,screen:str)->None:
        """Populate deterministic UI states used only by screenshot quality checks."""
        if not screen:return
        state=self.controller.state;state.first_run=screen=="welcome"
        if screen=="missing":state.media_tools=MediaToolPaths()
        if screen=="home":self.show_home=True
        if screen=="settings":self.show_settings=True
        if screen in {"file","transcription","speakers","export"}:
            state.selected_file_metadata=AudioInfo(r"C:\Research\Group_interview_07.m4a","Group_interview_07.m4a",134217728,7242,"aac",48000,2,148000)
            state.selected_file_path=state.selected_file_metadata.path
        if screen=="transcription":
            state.current_workflow_step=1;state.processing=True;state.transcription_progress=.47;state.generated_chunks=[]
            state.activity_log=["File analysed.","Uploading the recording: 64%.","The provider is processing the recording."]
        if screen in {"speakers","export"}:
            # Screenshot fixture. English because the screenshots are published; a real
            # transcript is in whatever language the interview was, which is a data setting.
            names=["Good afternoon, and thank you all for taking part in this discussion.",
                "I think the problem shows up mainly when the information arrives too late.",
                "For our team, talking to each other directly is what made the difference.",
                "I would add that the experience differs a great deal from one participant to another."]
            state.transcript_segments=[TranscriptSegment(0,0,str(i%3),f"Speaker {i%3+1}",i*18,i*18+14,i*18,i*18+14,text)
                for i,text in enumerate(names*8)]
            state.speaker_mapping={"Speaker 1":"Moderator","Speaker 2":"Speaker 2","Speaker 3":"Speaker 3"}
            state.current_workflow_step=2 if screen=="speakers" else 3;state.generated_at="2026-07-19T12:00:00+03:00"

    def configure_page(self)->None:
        p=self.page;p.title=s.APP_NAME;p.padding=0;p.theme=application_theme(False);p.dark_theme=application_theme(True)
        p.theme_mode={"dark":ft.ThemeMode.DARK,"system":ft.ThemeMode.SYSTEM}.get(self.controller.state.settings.appearance,ft.ThemeMode.LIGHT)
        p.window.width=1320;p.window.height=860;p.window.min_width=760;p.window.min_height=560;p.window.resizable=True;p.window.prevent_close=True
        # Start maximised. On a high-DPI display the logical desktop can be smaller than any
        # fixed default — a 3060x2100 screen at 300% scaling is only 1020x700 logical — so a
        # hard-coded size puts the window's edges off-screen. Filling the work area always fits.
        p.window.maximized=True
        # The native title bar is replaced by the application's own bar, which carries the
        # window buttons on the right and doubles as the drag handle.
        p.window.title_bar_hidden=True;p.window.title_bar_buttons_hidden=True
        p.window.on_event=self.window_event;p.on_resize=self.on_resize;p.on_keyboard_event=self.on_key

    # ── Window buttons ───────────────────────────────────────────────────────
    def minimize_window(self)->None:
        self.page.window.minimized=True;self.page.update()

    def toggle_maximize(self)->None:
        maximized=not bool(self.page.window.maximized)
        self.page.window.maximized=maximized;self.page.update()
        button=self.refs.get("maximize_button")
        if button is None:return
        button.icon=ft.Icons.FILTER_NONE if maximized else ft.Icons.CROP_SQUARE
        button.tooltip=s.WINDOW_RESTORE if maximized else s.WINDOW_MAXIMIZE
        self._safe_update(button)

    def close_window(self)->None:
        """Same guarantees as the OS close button: refuse while busy, clean up, then exit."""
        if self.controller.state.processing:
            message_dialog(self.page,s.BUSY_TITLE,s.BUSY_BODY);return
        self.controller.state.cleanup_temporary();self.page.run_task(self._safe_destroy)

    def fit_restore_size(self)->None:
        """Keep the un-maximised size inside the desktop.

        Measured once, from the first real width the page reports while maximised: that value is
        the work area in logical pixels, which is the only reliable way to learn how big this
        display actually is. Without it, restoring the window would hand back the oversized
        default that made the app larger than the screen in the first place.
        """
        if self._restore_fitted:return
        width,height=self.page.width,self.page.height
        if not width or not height:return
        self._restore_fitted=True
        window=self.page.window
        fitted_width=min(float(window.width or width),float(width))
        fitted_height=min(float(window.height or height),float(height)+t.TOP_BAR_HEIGHT)
        if fitted_width!=window.width or fitted_height!=window.height:
            window.width=fitted_width;window.height=fitted_height
            print(f"[window] restore size fitted to the desktop: {fitted_width:.0f}x{fitted_height:.0f}",flush=True)

    def on_resize(self,event:ft.Event)->None:
        self.fit_restore_size()
        # Docking the inspector changes the pane count and needs a rebuild; a plain width change
        # only resizes two containers.
        wide=self.controller.state.current_workflow_step==2 and not (self.show_settings or self.show_home)
        layout=measure(self.page.width,self.wants_side_pane(),False,self.nav_minimised,wide=wide)
        previous:Layout|None=self.refs.get("layout")
        if previous is None or layout.docked_inspector!=previous.docked_inspector or layout.sheet_open!=previous.sheet_open:
            self.render();return
        if abs(layout.workspace-previous.workspace)<.5 and abs(layout.content-previous.content)<.5:return
        self.refs["layout"]=layout;self.log_layout(layout,"resize")
        host=self.refs.get("content_host");pane=self.refs.get("workspace_pane")
        if host is not None:host.width=layout.content
        if pane is not None:pane.width=layout.workspace
        if not self._safe_update(host,pane):self.render()

    # ── Audio ────────────────────────────────────────────────────────────────
    def new_audio_service(self,path:str|None):
        """A fresh Audio service with its source fixed at construction.

        The backend only loads a source supplied this way; assigning `src` to an already
        attached service is silently ignored, which is what made play() hang.
        """
        return fa.Audio(src=path,autoplay=False,volume=1.0,
            playback_rate=getattr(self.player,"speed",1.0) if hasattr(self,"player") else 1.0,
            release_mode=fa.ReleaseMode.STOP)

    def attach_audio_service(self,audio)->None:
        """Publish the recording's service as the page's only Audio service.

        Replacing the list keeps exactly one Audio attached. More than one — in particular a
        placeholder with no source — prevents the client from ever loading any of them.
        """
        self.page.services=[audio]
        try:self.page.update()
        except Exception:pass
        self.page.run_task(self._watch_audio_load,audio)

    async def _watch_audio_load(self,audio)->None:
        """Say plainly whether the backend ever opened the source, instead of failing silently."""
        import asyncio
        await asyncio.sleep(8)
        if self.player.audio is not audio: return
        if self.player.loaded:
            print(f"[audio] source open after 8s (duration {self.player.duration_ms} ms)",flush=True)
            return
        print("[audio] STILL NOT OPEN after 8s — the client never registered this service; "
              "no on_loaded, no duration. The path is valid and was verified readable.",flush=True)

    def detach_audio_service(self,audio)->None:
        # Nothing to do: attach_audio_service replaces the list, which drops the previous one.
        return

    def apply_rewind(self)->None:
        settings=self.controller.state.settings
        self.player.auto_rewind=settings.auto_rewind_seconds if settings.auto_rewind_enabled else 0.0

    def sync_highlight(self,position_ms:int)->None:
        """Follow playback through the transcript: word when timed, whole turn otherwise."""
        state=self.controller.state
        if state.current_workflow_step!=2 or self.show_settings or self.show_home: return
        found=playback_sync.locate(state.transcript_segments,position_ms/1000.0)
        if found==self.active: return
        previous,self.active=self.active,found
        rows=self.refs.get("rows") or {}
        touched=[]
        for index in {previous.turn,found.turn}:
            parts=rows.get(index) if index is not None else None
            if parts is None: continue
            paint_turn(parts,parts["segment"],found.word if index==found.turn else None,
                index==found.turn)
            touched.append(parts["container"])
        if touched and not self._safe_update(*touched): return
        if previous.turn==found.turn: return
        # Nothing moves while a field has focus. The panel was already protected; the list
        # was not, so the text under the caret kept sliding away mid-sentence.
        if self.typing: return
        self.scroll_to_turn(found.turn)
        if self.follow_playback and found.turn is not None:
            self.follow_to(found.turn)

    def follow_to(self,index:int)->None:
        """Open the turn playback has reached, without touching playback itself.

        Deliberately not `select_segment`: that seeks the player to the start of the turn,
        which during playback would drag the audio backwards on every turn boundary.
        """
        if index==self.selected_segment: return
        previous,self.selected_segment=self.selected_segment,index
        touched:list[ft.Control]=[]
        rows=self.refs.get("rows") or {}
        for position in (previous,index):
            parts=rows.get(position) if position is not None else None
            if parts is None: continue
            row_state(parts,selected=position==index)
            touched.append(parts["container"])
        host=self.refs.get("inspector_host")
        if host is not None:
            host.content=self.build_inspector(index)
            touched.append(host)
        if not self._safe_update(*touched): self.render()

    def toggle_follow(self)->None:
        self.follow_playback=not self.follow_playback
        button=self.refs.get("player_follow")
        if button is None: self.render();return
        button.icon=ft.Icons.MY_LOCATION if self.follow_playback else ft.Icons.LOCATION_SEARCHING
        button.tooltip=s.FOLLOW_ON if self.follow_playback else s.FOLLOW_OFF
        button.icon_color=t.primary() if self.follow_playback else t.on_surface_variant()
        if not self._safe_update(button): self.render()

    def current_order(self)->list[int]:
        """The transcript indices the list is showing, in the order it shows them."""
        order=self.refs.get("visible_order")
        if order is not None: return order
        state=self.controller.state
        return review_progress.visible_order(state.transcript_segments,state.show_only_unchecked)

    def reveal_turn(self,index:int|None,allow_page_change:bool=True)->bool:
        """Bring a turn into view in the list: right page, scrolled to it. True if shown.

        A row's place in the list is its position in the visible order, NOT its transcript
        index. Those are the same number only while nothing is filtered; with "only
        unchecked" on, turn 100 can be the sixty-sixth row. Subtracting the page offset from
        the index — which is what this did — then scrolled to the wrong row, or, past the
        page size, gave up silently. That is why Resume appeared to do nothing.
        """
        if index is None: return False
        order=self.current_order()
        try: position=order.index(index)
        except ValueError:
            return False                       # filtered out of the list entirely
        self.scroll_to_row(position)
        return True

    def scroll_to_row(self,position:int)->None:
        """Scroll the list to a row, one row of context above it.

        `ListView.scroll_to` is a coroutine. Called without awaiting it, it builds a
        coroutine object, never runs, and raises nothing — so "Show this turn" did nothing,
        following playback never scrolled, and Resume looked broken. It goes through the
        page's task runner now, and a failure is printed instead of swallowed: a bare
        `except: pass` around this is exactly why it stayed hidden.
        """
        listing=self.refs.get("listing")
        if listing is None or position<0: return
        target=max(0.0,(position-1)*float(t.TRANSCRIPT_ROW_HEIGHT))

        async def run()->None:
            # The list this was scheduled for may have been replaced by a rebuild between
            # the key press and the task running. Scrolling a control that is no longer on
            # the page asks the client to animate something it cannot find, so a scroll
            # that has been overtaken is dropped rather than sent.
            if self.refs.get("listing") is not listing: return
            try: await listing.scroll_to(offset=target,duration=250)
            except Exception as exc: print(f"[scroll] {type(exc).__name__}: {exc}",flush=True)

        try: self.page.run_task(run)
        except Exception as exc: print(f"[scroll] cannot schedule: {exc}",flush=True)

    def scroll_to_turn(self,index:int|None)->None:
        """Follow playback into view, including across a page boundary."""
        self.reveal_turn(index)

    # ── Find and replace ─────────────────────────────────────────────────────
    def open_find(self)->None:
        self.find_open=True;self.render()

    def close_find(self)->None:
        self.find_open=False;self.render()

    def update_find(self,term:str,replacement:str,case_sensitive:bool,whole_word:bool)->None:
        """Recount as the researcher types, without rebuilding the screen under the cursor."""
        self.find_term=term;self.find_replacement=replacement
        self.find_options=find_replace.Options(case_sensitive,whole_word)
        count=self.refs.get("find_count");apply=self.refs.get("find_apply")
        if count is None: return
        segments=self.controller.state.transcript_segments
        matches=self.controller.count_matches(term,self.find_options)
        turns=len(find_replace.matching_turns(segments,term,self.find_options))
        count.value,count.color=find_replace_summary(term,matches,turns)
        # The count and the button must always tell the same story; updating one without the
        # other left Replace all permanently dead after the panel opened on an empty term.
        if apply is not None: apply.disabled=not matches
        self._safe_update(count,apply)

    def replace_all(self)->None:
        record=self.controller.replace_all(self.find_term,self.find_replacement,self.find_options)
        self.render()
        if record.applied:
            notification(self.page,s.FIND_DONE.format(count=record.matches,turns=record.turns))

    def undo_replace(self)->None:
        if self.controller.undo_replace():
            self.render();notification(self.page,s.FIND_UNDONE)

    def overlays(self,layout:Layout)->list[ft.Control]:
        """Every transient tool that is currently open, as floating panels.

        They are handed to the shell, never to a view: a tool must not be able to insert
        itself into a column and push the transcript down. With none open this list is
        empty and the shell builds exactly the tree it built before find and replace existed.
        """
        if not self.find_open: return []
        segments=self.controller.state.transcript_segments
        matches=self.controller.count_matches(self.find_term,self.find_options)
        turns=len(find_replace.matching_turns(segments,self.find_term,self.find_options))
        panel=find_replace_bar(self.find_term,self.find_replacement,
            self.find_options.case_sensitive,self.find_options.whole_word,matches,turns,
            self.controller.state.last_replacement is not None,
            self.update_find,self.replace_all,self.undo_replace,self.close_find,
            self.refs,self.set_typing,layout.body)
        print(f"[overlay:find] width={self.refs.get('find_panel_width'):.0f} "
              f"docked=top-right floats=yes reflow=none",flush=True)
        return [panel]

    # ── The open turn ────────────────────────────────────────────────────────
    def build_inspector(self,index:int|None=None)->ft.Control:
        """One place that builds the panel, so its growing set of view modes cannot drift
        between the four points that rebuild it."""
        return speakers_view.inspector(self.controller.state,
            self.selected_segment if index is None else index,
            self.save_correction,self.revert_correction,self.play_segment,self.refs,None,
            self.seek_to,self.set_typing,self.insert_timestamp,self.reassign_turn,
            self.set_checked,self.words_mode,self.toggle_words_mode,
            self.show_original,self.toggle_show_original,self.locate_open_turn,
            self.set_note,self.note_open,self.toggle_note,
            self.mark_selection,self.comment_on_selection,self.clear_marks,self.drop_mark,
            self.controller.state.settings.highlight_labels)

    # ── Marking a phrase ─────────────────────────────────────────────────────
    # Bold, one of three highlighters, and a comment on the selected words. All three reach
    # the Word file as the thing a reader expects, so the marking is not a private notation.
    def mark_selection(self,index:int,start:int,end:int,kind:str,slot:str="1")->None:
        """Mark the selected characters. Any unsaved edit is written first.

        A mark is stored against the turn's text, so marking with an unsaved sentence in the
        box would place it on characters that are not there yet. Saving first makes the two
        agree, and it is what the researcher wanted anyway.
        """
        self.commit_correction(index)
        if self.controller.mark_selection(index,start,end,kind,slot):
            self.refresh_inspector();self._refresh_row_marks(index);self.autosave()

    def comment_on_selection(self,index:int,start:int,end:int)->None:
        """Ask for the comment, then anchor it to those words alone.

        A dialog rather than another box in the panel: the question is asked once and the
        panel goes back to being the turn, per the rule that a transient tool floats.
        """
        segments=self.controller.state.transcript_segments
        if not (0<=index<len(segments)): return
        self.commit_correction(index)
        text=segments[index].text
        low,high=an.normalise(start,end,text)
        if high<=low: return
        quote=text[low:high]
        box=ft.TextField(multiline=True,min_lines=2,max_lines=4,autofocus=True,
            text_size=t.TYPE_BODY,border_radius=t.R_SM,border_color=t.outline(),
            focused_border_color=t.primary(),color=t.on_surface())
        box.on_change=lambda e:setattr(box,"value",e.control.value)
        def keep(event:ft.Event)->None:
            self.page.pop_dialog()
            note=(box.value or "").strip()
            if note and self.controller.mark_selection(index,low,high,an.COMMENT,"",note):
                self.refresh_inspector();self._refresh_row_marks(index);self.autosave()
        modal_dialog(self.page,s.MARK_COMMENT_PROMPT.format(quote=quote[:60]),box,
            [tertiary_button(s.DISCARD,lambda e:self.page.pop_dialog()),
             primary_button(s.SAVE_CORRECTION,keep)],ft.Icons.ADD_COMMENT_OUTLINED)

    def clear_marks(self,index:int,start:int,end:int)->None:
        """Take the marks off the selected words, or off the whole turn when nothing is
        selected — applying a mark rebuilds the panel and the selection is gone by then."""
        self.commit_correction(index)
        segments=self.controller.state.transcript_segments
        if not (0<=index<len(segments)): return
        if end<=start: start,end=0,len(segments[index].text)
        if self.controller.clear_marks(index,start,end):
            self.refresh_inspector();self._refresh_row_marks(index);self.autosave()

    def drop_mark(self,index:int,mark:object)->None:
        """Remove the one mark the researcher pointed at in the list."""
        if self.controller.drop_mark(index,mark):
            self.refresh_inspector();self._refresh_row_marks(index);self.autosave()

    def set_note(self,index:int,note:str)->None:
        """A comment on a turn, saved as you type. It never touches the transcript text."""
        if self.controller.annotate_segment(index,note):
            self._refresh_row_marks(index);self._refresh_status()

    def toggle_note(self)->None:
        self.note_open=not self.note_open;self.refresh_inspector()

    def locate_open_turn(self)->None:
        """Bring the list to the turn the panel is showing, wherever it has scrolled to."""
        index=self.selected_segment
        if index is None: return
        state=self.controller.state
        if state.show_only_unchecked and index not in self.current_order():
            state.show_only_unchecked=False
            self.refs.pop("visible_order",None)
            notification(self.page,s.FILTER_CLEARED)
            self.render()
        if not self.reveal_turn(index): self.render()

    def set_api_key(self,key:str)->None:
        """Hold the provider's key for this session only. It is never written anywhere."""
        self.controller.state.set_active_api_key(key.strip())

    def toggle_words_mode(self)->None:
        self.words_mode=not self.words_mode;self.refresh_inspector()

    def toggle_show_original(self)->None:
        self.show_original=not self.show_original;self.refresh_inspector()

    def refresh_inspector(self)->None:
        host=self.refs.get("inspector_host")
        if host is None: self.render();return
        host.content=self.build_inspector()
        if not self._safe_update(host): self.render()

    # ── Review progress ──────────────────────────────────────────────────────
    def commit_correction(self,index:int|None=None)->bool:
        """Write whatever is in the correction box into the turn. True if anything changed.

        Checked and corrected are one act now: whichever the researcher reaches for, the
        edit in front of them is kept. Before this, ticking Checked with an unsaved sentence
        in the box quietly threw the sentence away.
        """
        index=self.selected_segment if index is None else index
        field=self.refs.get("inspector_field")
        segments=self.controller.state.transcript_segments
        if field is None or index is None or index>=len(segments): return False
        text=field.value or ""
        if text==segments[index].text: return False
        before=len(segments[index].annotations)
        self.controller.correct_segment(index,text)
        # A mark whose phrase the edit removed cannot follow it anywhere. Saying so is the
        # difference between a mark that went away and a mark the researcher thinks is still
        # there and will not find in the exported document.
        lost=before-len(segments[index].annotations)
        if lost>0: notification(self.page,s.MARK_DETACHED.format(count=lost))
        self._refresh_row_text(index)
        return True

    def set_checked(self,index:int,value:bool)->None:
        """Mark one turn reviewed, keeping any edit in the box, and write the project back."""
        segments=self.controller.state.transcript_segments
        self.commit_correction(index)
        if not review_progress.set_checked(segments,index,value):
            self.autosave();return
        self.controller.state.last_reviewed_index=index
        self.controller.state.dirty=True
        parts=(self.refs.get("rows") or {}).get(index)
        if parts is not None: row_state(parts,checked=value)
        if not self.refresh_progress(parts):self.render();return
        self.autosave()
        # A filtered list must lose the turn that no longer belongs in it.
        if self.controller.state.show_only_unchecked: self.render()

    AUTOSAVE_INTERVAL = 3.0

    def autosave(self,force:bool=False)->bool:
        """Write the project back once it has a file, without ever opening a dialog.

        Throttled: a 3 MB transcript takes about 70 ms to write, which is nothing once but
        a stutter if it happened on every turn of a fast pass. Anything skipped is written
        by the next call, and `force` flushes on the way out.
        """
        state=self.controller.state
        if not state.dirty or not self.save_target():
            return False
        now=time.monotonic()
        if not force and now-self._last_autosave<self.AUTOSAVE_INTERVAL:
            self._autosave_pending=True;return False
        try:
            self.controller.save_project(self.save_target())
        except Exception as exc:
            error_notification(self.page,str(exc));return False
        self._last_autosave=now;self._autosave_pending=False
        self._refresh_status()
        return True

    def refresh_progress(self,*touched:ft.Control|None)->bool:
        state=self.controller.state
        progress=review_progress.progress(state.transcript_segments)
        track=self.refs.get("progress_track");label=self.refs.get("progress_label")
        if track is not None: track.value=progress.fraction
        if label is not None: label.value=label_for(progress)
        rows=[parts["container"] if isinstance(parts,dict) else parts for parts in touched]
        if not self._safe_update(track,label,*rows): return False
        self._refresh_status();return True

    def mark_and_advance(self)->None:
        """Ctrl+Enter: this one is done, take me to the next one that is not."""
        state=self.controller.state;index=self.selected_segment
        if index is None:
            first=review_progress.next_unchecked(state.transcript_segments,None)
            if first is not None: self.select_segment(first)
            return
        # set_checked commits the box, so the sentence being typed is never lost here.
        self.set_checked(index,True)
        following=review_progress.next_unchecked(state.transcript_segments,index)
        if following is None:
            notification(self.page,s.REVIEW_DONE);return
        self.select_segment(following)
        self.reveal_turn(following)

    def toggle_unchecked_filter(self)->None:
        state=self.controller.state
        state.show_only_unchecked=not state.show_only_unchecked
        self.transcript_offset=0;self.render()

    def resume_target(self)->int|None:
        state=self.controller.state
        return review_progress.resume_index(state.transcript_segments,state.last_reviewed_index)

    def resume_stamp(self)->str:
        index=self.resume_target();segments=self.controller.state.transcript_segments
        if index is None or index>=len(segments): return ""
        return format_timestamp(segments[index].absolute_start)

    def resume_review(self)->None:
        """Go back to where the work stopped, in the transcript and in the audio.

        Resume promises to take you there, so a filter that would hide the destination is
        cleared rather than leaving the button looking broken. Anything already reviewed is
        hidden by "only unchecked", and where you stopped is very often exactly that.
        """
        index=self.resume_target()
        if index is None: return
        state=self.controller.state
        if state.show_only_unchecked and index not in self.current_order():
            state.show_only_unchecked=False
            self.refs.pop("visible_order",None)
            notification(self.page,s.FILTER_CLEARED)
            self.render()
        self.select_segment(index)
        if not self.reveal_turn(index): self.render()

    def insert_timestamp(self)->None:
        """Put the current playback time into the turn's text, at the cursor."""
        index=self.selected_segment
        field=self.refs.get("inspector_field")
        if field is None or index is None: return
        cursor=getattr(getattr(field,"selection",None),"base_offset",None)
        text,position=playback_sync.insert_timestamp(field.value or "",cursor,
            self.player.position_ms/1000.0)
        field.value=text
        try: field.selection=TextSelection(base_offset=position,extent_offset=position)
        except Exception: pass
        self.controller.correct_segment(index,text)
        self._safe_update(field)
        self._refresh_row_text(index)

    def set_typing(self,active:bool)->None:
        """A text field took or lost focus. Space belongs to the text while it is typing."""
        self.typing=active

    # Key names as Flet reports them, with the spellings other builds have used, so a
    # shortcut cannot quietly stop working because a label changed.
    LEFT_KEYS = ("Arrow Left", "ArrowLeft", "Left")
    RIGHT_KEYS = ("Arrow Right", "ArrowRight", "Right")
    UP_KEYS = ("Arrow Up", "ArrowUp", "Up")
    DOWN_KEYS = ("Arrow Down", "ArrowDown", "Down")
    ENTER_KEYS = ("Enter", "Numpad Enter", "NumpadEnter")
    # The dedicated play/pause key: Ctrl+W. Flet's keyboard hook is a listener, not a
    # consumer, so a key it reports still reaches whatever has focus — Space with the
    # transcript focused scrolls the list as well as toggling the audio, and Ctrl+Space put
    # a space in the sentence. A letter has neither meaning, so it can only pause. F4 is
    # kept beside it because transcription foot pedals are commonly mapped to a function key.
    # Ctrl+1/2/3 pick a highlighter, Ctrl+0 takes the marks off. Flet reports the digit
    # row by name, so both spellings are accepted rather than guessed at.
    SLOT_KEYS={"1":"1","2":"2","3":"3","Digit 1":"1","Digit 2":"2","Digit 3":"3",
               "Numpad 1":"1","Numpad 2":"2","Numpad 3":"3"}
    CLEAR_KEYS=("0","Digit 0","Numpad 0")
    PLAY_LETTERS = ("w",)
    PLAY_KEYS = ("F4",)

    def on_key(self,event:ft.KeyboardEvent)->None:
        """Route one key press, and never let a failure escape into the event loop.

        A shortcut that raises inside a handler takes the exception somewhere the researcher
        cannot see it — at best a line on a console a built application does not have, at
        worst the window going away with no explanation. Held down, a key that fails fails
        repeatedly. Caught here, a broken shortcut is a message that names itself and the
        rest of the application carries on.
        """
        try: self._route_key(event)
        except Exception as exc:
            print(f"[shortcut] {type(exc).__name__}: {exc}",flush=True)
            try: error_notification(self.page,s.SHORTCUT_FAILED.format(detail=exc))
            except Exception: pass

    def _route_key(self,event:ft.KeyboardEvent)->None:
        """Every shortcut on the review screen, in one place.

        Two rules decide what is allowed when. Anything with Ctrl works while typing,
        because that is exactly when a researcher wants it — mark this turn and move on
        without leaving the keyboard. Anything without Ctrl (Space, the arrows) is a plain
        character to a text field, so it only acts when no field has focus.
        """
        key=str(event.key);ctrl=bool(getattr(event,"ctrl",False))
        state=self.controller.state
        reviewing=state.current_workflow_step==2 and not (self.show_settings or self.show_home)

        # Before anything else, and outside every guard: one key, one effect, no context.
        if key in self.PLAY_KEYS or (ctrl and key.lower() in self.PLAY_LETTERS):
            self.player.toggle();return

        if key in ("Escape","Esc"):
            if self.find_open: self.close_find()
            return

        if ctrl:
            # Ctrl owns the audio, and works with the caret anywhere: space, then the two
            # directions. Stopping and stepping the recording are the things a researcher
            # needs mid-sentence, which is exactly when the plain keys cannot be spared.
            if key in self.LEFT_KEYS:
                self.skip_audio(-float(t.SKIP_SECONDS));return
            if key in self.RIGHT_KEYS:
                self.skip_audio(float(t.SKIP_SECONDS));return
            if key in self.UP_KEYS or key in self.DOWN_KEYS:
                if reviewing: self.step_turn(1 if key in self.DOWN_KEYS else -1)
                return
            if key in self.ENTER_KEYS:
                if reviewing: self.mark_and_advance()
                return
            letter=key.lower()
            if letter=="s":
                if not state.transcript_segments: return
                if bool(getattr(event,"shift",False)): self.save_project_as()
                # The correction in the box first, then the file. Ctrl+S used to write the
                # project around an unsaved sentence and report "Saved", which is the one
                # thing a save key must never do.
                else: self.commit_correction();self.save_project()
                return
            if letter=="o":
                self.open_project();return
            if not reviewing: return
            # Marking the selected phrase, without reaching for the mouse. All under Ctrl,
            # because the caret is inside the text when the selection exists.
            if key in self.SLOT_KEYS:
                self.mark_from_keyboard(annotations_kind=an.HIGHLIGHT,slot=self.SLOT_KEYS[key]);return
            if key in self.CLEAR_KEYS:
                self.clear_from_keyboard();return
            if letter=="b": self.mark_from_keyboard(annotations_kind=an.BOLD)
            elif letter=="d": self.comment_from_keyboard()
            elif letter=="f": self.open_find()
            elif letter=="t": self.insert_timestamp()
            elif letter=="k": self.toggle_words_mode()
            elif letter=="m": self.toggle_note()
            elif letter=="j": self.locate_open_turn()
            elif letter=="p": self.play_segment(self.selected_segment) if self.selected_segment is not None else None
            elif letter=="e": self.toggle_unchecked_filter()
            elif letter=="r": self.resume_review() if self.resume_target() is not None else None
            return

        # Everything below is a character a text field would want, so it yields to typing.
        # Space is deliberately NOT offered with Ctrl: Flet cannot consume a key, so the
        # field receives it too and a space lands in the sentence. Ctrl+W is the pause key.
        if self.typing or not reviewing: return
        if key in (" ","Space"): self.player.toggle()
        elif key in self.LEFT_KEYS: self.skip_audio(-float(t.SKIP_SECONDS))
        elif key in self.RIGHT_KEYS: self.skip_audio(float(t.SKIP_SECONDS))
        elif key in self.UP_KEYS: self.step_turn(-1)
        elif key in self.DOWN_KEYS: self.step_turn(1)

    # ── Marking from the keyboard ────────────────────────────────────────────
    # The selection lives in the marking bar and is published into `refs`, so these read
    # what is selected in the box right now rather than what was selected when it was built.
    def live_selection(self)->tuple[int,int]:
        span=self.refs.get("selection") or {}
        return int(span.get("start",0) or 0),int(span.get("end",0) or 0)

    def mark_from_keyboard(self,annotations_kind:str,slot:str="1")->None:
        index=self.selected_segment
        start,end=self.live_selection()
        if index is None: return
        if end<=start: notification(self.page,s.MARK_NEEDS_SELECTION);return
        self.mark_selection(index,start,end,annotations_kind,slot)

    def comment_from_keyboard(self)->None:
        index=self.selected_segment
        start,end=self.live_selection()
        if index is None: return
        if end<=start: notification(self.page,s.MARK_NEEDS_SELECTION);return
        self.comment_on_selection(index,start,end)

    def clear_from_keyboard(self)->None:
        """With a selection, that range; without one, the whole turn — as the button does."""
        index=self.selected_segment
        if index is None: return
        start,end=self.live_selection()
        self.clear_marks(index,start,end)

    def skip_audio(self,delta_seconds:float)->None:
        """Ten seconds back is the single most used control when checking a word."""
        self.player.skip(delta_seconds)

    def step_turn(self,delta:int)->None:
        """Move to the turn before or after this one, staying inside the transcript."""
        segments=self.controller.state.transcript_segments
        if not segments: return
        current=self.selected_segment
        target=0 if current is None else max(0,min(len(segments)-1,current+delta))
        if target==current: return
        self.select_segment(target)
        self.reveal_turn(target)

    def seek_to(self,seconds:float)->None:
        self.player.seek(seconds)

    def refresh_transport(self)->None:
        """Update only the transport controls; rebuilding the screen would lose scroll position."""
        button=self.refs.get("player_button")
        if button is None: return
        from audio_player import format_position
        button.icon=ft.Icons.PAUSE if self.player.playing else ft.Icons.PLAY_ARROW
        button.tooltip=s.PLAYER_PAUSE if self.player.playing else s.PLAYER_PLAY
        elapsed=self.refs.get("player_elapsed");duration=self.refs.get("player_duration")
        scrubber=self.refs.get("player_scrubber")
        if elapsed is not None: elapsed.value=format_position(self.player.position_ms)
        if duration is not None and self.player.duration_ms:
            duration.value=format_position(self.player.duration_ms)
        if scrubber is not None and self.player.duration_ms:
            # Writing `value` makes Flet fire on_change_end, which would seek again and again.
            self.refs["scrubber_programmatic"]=True
            scrubber.max=float(self.player.duration_ms)
            scrubber.value=float(min(self.player.position_ms,self.player.duration_ms))
            scrubber.disabled=False
            self.refs["scrubber_programmatic"]=False
        self._safe_update(button,elapsed,duration,scrubber)

    def dismiss_audio_banner(self)->None:
        self.controller.state.audio_banner_dismissed=True;self.render()

    async def _locate_audio(self)->None:
        files=await self.file_picker.pick_files(dialog_title=s.AUDIO_DIALOG_TITLE,allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["m4a","wav","mp3","mp4","aac","flac","webm"])
        if not (files and files[0].path): return
        chosen=files[0].path
        if self.controller.audio_matches(chosen): self._attach_audio(chosen);return
        state=self.controller.state
        detail=s.AUDIO_MISMATCH_BODY.format(expected=state.audio_filename or "—",
            size=human_size(state.audio_bytes) if state.audio_bytes else "—",
            chosen=Path(chosen).name,chosen_size=human_size(Path(chosen).stat().st_size))
        confirm_dialog(self.page,s.AUDIO_MISMATCH_TITLE,detail,lambda:self._attach_audio(chosen))

    def _attach_audio(self,path:str)->None:
        if not self.controller.bind_audio(path) or not self.player.bind(path):
            message_dialog(self.page,s.AUDIO_MISSING_TITLE,s.AUDIO_UNREADABLE);return
        self.controller.state.audio_banner_dismissed=False
        self.render()

    def locate_audio(self)->None:self.page.run_task(self._locate_audio)

    def wants_side_pane(self)->bool:
        """The Speakers screen's right-hand pane holds the open turn.

        The speaker list is back in the left column of the workspace, where it started; the
        turn under edit is the pane. It is always present rather than appearing on
        selection, so nothing on the screen moves when a turn is picked.
        """
        state=self.controller.state
        return (not (self.show_settings or self.show_home) and state.current_workflow_step==2
                and bool(state.transcript_segments))

    def log_layout(self,layout:Layout,reason:str)->None:
        """Printed on every layout decision so the pane arithmetic can be checked from outside."""
        print(f"[layout:{reason}] {layout.describe()}",flush=True)

    def window_event(self,e:ft.WindowEvent)->None:
        if e.type==ft.WindowEventType.CLOSE:
            if self.controller.state.processing:message_dialog(self.page,s.BUSY_TITLE,s.BUSY_BODY);return
            self.autosave(force=True)
            self.controller.state.cleanup_temporary();self.page.run_task(self._safe_destroy)
    async def _safe_destroy(self)->None:
        try:await self.page.window.destroy()
        except RuntimeError:pass

    # ── Rendering ────────────────────────────────────────────────────────────
    def render(self)->None:
        """Full rebuild. Reserved for screen and step changes; edits update in place."""
        state=self.controller.state
        t.set_dark(self.page.theme_mode==ft.ThemeMode.DARK or self.page.theme_mode==ft.ThemeMode.SYSTEM and self.page.platform_brightness==ft.Brightness.DARK)
        if state.first_run:
            self.refs={}
            # The welcome screen has no application chrome, so it gets a bare title bar of its own.
            chrome=window_chrome(self.minimize_window,self.toggle_maximize,self.close_window,
                bool(self.page.window.maximized))
            self.page.controls.clear()
            self.page.add(ft.Column([chrome,welcome_view.build(self.finish_welcome,self.show_help)],spacing=0,expand=True))
            self.page.update();return
        # The Speakers screen manages its own vertical space (a virtualised list); every other
        # screen is a stack of cards and scrolls as one column inside the shell. It is also the
        # only workbench: three panes that should use the whole desk rather than sit inside a
        # reading column, since the text within them is already capped to its own measure.
        fills=state.current_workflow_step==2 and not (self.show_settings or self.show_home)
        layout=measure(self.page.width,self.wants_side_pane(),False,self.nav_minimised,wide=fills)
        self.refs={"layout":layout,"rows":{},"speakers":{}}
        self.log_layout(layout,"render")
        inspector=None
        if self.show_home:workspace=welcome_view.home(self.leave_home,self.open_project)
        elif self.show_settings:workspace=settings_view.build(state,self.apply_settings,self.choose_media_folder,
            self.reset_welcome,self.set_api_key)
        elif state.current_workflow_step==0:
            workspace=recording_view.build(state,self.choose_file,self.remove_file,lambda:self.navigate(1),
                self.set_quality,self.set_range,layout.content,self.open_project,self.open_settings)
        elif state.current_workflow_step==1:
            workspace=transcription_view.build(state,self.begin_transcription,self.controller.cancel,self.elapsed())
        elif state.current_workflow_step==2:
            # The open turn is the right-hand pane, kept in a host container so an edit can
            # rebuild it alone without touching the transcript or its scroll position.
            host=ft.Container(self.build_inspector(),expand=True)
            self.refs["inspector_host"]=host
            order=review_progress.visible_order(state.transcript_segments,state.show_only_unchecked)
            self.refs["visible_order"]=order
            self.transcript_offset=0
            strip=review_strip(review_progress.progress(state.transcript_segments),
                state.show_only_unchecked,self.toggle_unchecked_filter,
                self.resume_review if self.resume_target() is not None else None,
                self.resume_stamp(),self.refs)
            # One decision for the whole screen, so no two surfaces can end up on top of
            # each other and nothing has to be squeezed to make room.
            self.placement=speakers_view.pane_placement(layout.content,layout.docked_inspector,
                self.panel_collapsed,self.find_open)
            identities=(speakers_view.identities_pane(state,self.map_speaker,self.refs,
                self.set_typing,self.merge_speakers,self.toggle_panel)
                if self.placement.identities=="column" else None)
            workspace=speakers_view.build(state,self.select_segment,self.play_segment,
                lambda:self.navigate(3),self.selected_segment,self.change_page,
                self.refs,layout.content,self.locate_audio,
                self.dismiss_audio_banner,self.open_find,
                self.toggle_panel,self.panel_collapsed,identities,order,strip)
            if self.placement.detail=="pane": inspector=host
        else:workspace=export_view.build(state,self.save_export,self.set_export_metadata)
        nav=navigation_rail(state,self.navigate,self.new_project,self.save_project,self.open_project,
            self.nav_minimised,self.toggle_nav,self.go_home)
        top=top_bar(state,self.open_settings,self.toggle_theme,self.show_help,self.refs,
            self.minimize_window,self.toggle_maximize,self.close_window,
            bool(self.page.window.maximized),self.save_project,
            Path(self.save_target()).name if self.save_target() else "",self.save_project_as,
            layout.nav)
        # Proof, printed rather than eyeballed: no declared child width exceeds the column.
        print(layout_audit.report(self.screen_name(),layout.content,workspace),flush=True)
        # The transport belongs to the review screen only, and sits below it as a footer.
        footer=audio_transport(self.player,self.refs,self.set_speed,self.skip_audio,
            self.toggle_follow,self.follow_playback) if fills else None
        floating=self.overlays(layout) if fills else []
        # Whatever cannot take a column floats, on its own solid surface with its own way
        # out — and `pane_placement` has already guaranteed that at most one of them does,
        # so nothing is ever half-drawn under something else.
        placement=getattr(self,"placement",None)
        if fills and placement is not None and placement.identities=="float":
            panel,_=overlay.floating_panel(s.IDENTITIES,
                [speakers_view.identities_pane(state,self.map_speaker,self.refs,self.set_typing,
                    self.merge_speakers,None,heading=False)],
                self.toggle_panel,ft.Icons.PEOPLE_OUTLINE,layout.body,
                close_tooltip=s.COLLAPSE_IDENTITIES,height=t.FLOATING_LIST_HEIGHT)
            floating.append(panel)
        if fills and placement is not None and placement.detail=="float":
            panel,_=overlay.floating_panel(s.INSPECTOR_TITLE,[self.build_inspector()],
                self.close_inspector,ft.Icons.EDIT_NOTE,layout.body,
                close_tooltip=s.CLOSE_INSPECTOR,height=t.FLOATING_PANEL_HEIGHT)
            floating.append(panel)
        band=status_bar(state,self.screen_name(),
            review_progress.progress(state.transcript_segments).checked,
            self.open_settings,self.go_home)
        shell=app_shell(nav,top,workspace,inspector,layout,self.refs,not fills,footer,
            floating or None,band)
        self.page.controls.clear();self.page.add(shell);self.page.update()

    def screen_name(self)->str:
        if self.show_home:return "home"
        if self.show_settings:return "settings"
        return {0:"recording",1:"transcription",2:"speakers"}.get(self.controller.state.current_workflow_step,"export")

    def toggle_nav(self)->None:
        self.nav_minimised=not self.nav_minimised;self.render()

    def toggle_panel(self)->None:
        self.panel_collapsed=not self.panel_collapsed;self.render()

    def set_speed(self,rate:float)->None:
        """Playback speed. The service is rebuilt because a source-bearing Audio is the only
        form the client loads; the position and playing state are carried across."""
        self.player.set_speed(rate)

    def elapsed(self)->str:
        if not self.started_at:return "00:00"
        seconds=int(time.monotonic()-self.started_at);return f"{seconds//60:02d}:{seconds%60:02d}"

    def _safe_update(self,*controls:ft.Control|None)->bool:
        """Update the given controls in place; report failure so the caller can fall back."""
        try:
            for control in controls:
                if control is not None:control.update()
            return True
        except Exception:
            return False

    def _refresh_status(self)->None:
        status=self.refs.get("status")
        if status is None:return
        dirty=self.controller.state.dirty
        target=self.save_target()
        status.value=save_status(dirty,Path(target).name if target else "")
        status.color=t.warning() if dirty else t.on_surface_variant()
        self._safe_update(status)

    def visible_rows(self)->list[tuple[int,dict]]:
        """The turn rows currently on screen, as (transcript index, controls).

        Only integer keys. The row registry is index-keyed by contract, and a caller that
        compares those keys to a segment count crashes on anything else — which is exactly
        what happened when the list wrote its own handles into the same dictionary.
        """
        rows=self.refs.get("rows") or {}
        return [(key,parts) for key,parts in rows.items() if isinstance(key,int)]

    def _refresh_speaker(self,speaker_id:str)->None:
        """Only the rows belonging to this speaker change when a name is applied."""
        state=self.controller.state
        touched:list[ft.Control]=[]
        for index,parts in self.visible_rows():
            if index>=len(state.transcript_segments):continue
            item=state.transcript_segments[index]
            if item.speaker_id!=speaker_id:continue
            parts["speaker"].value=apply_speaker_mapping(item,state.speaker_mapping);touched.append(parts["speaker"])
        field=(self.refs.get("speakers") or {}).get(speaker_id)
        if field is not None:
            field.value=state.speaker_mapping.get(speaker_id,speaker_id);touched.append(field)
        if not self._safe_update(*touched):self.render();return
        self._refresh_inspector_if_showing(speaker_id)
        self._refresh_status()

    def _refresh_inspector_if_showing(self,speaker_id:str)->None:
        state=self.controller.state;index=self.selected_segment
        host=self.refs.get("inspector_host")
        if host is None or index is None or index>=len(state.transcript_segments):return
        if state.transcript_segments[index].speaker_id!=speaker_id:return
        host.content=self.build_inspector(index)
        self._safe_update(host)

    def _refresh_row_text(self,index:int)->None:
        state=self.controller.state;parts=(self.refs.get("rows") or {}).get(index)
        if parts is None:
            self.render();return
        item=state.transcript_segments[index]
        parts["body"].value=item.text
        if not self._safe_update(parts["body"]):self.render();return
        self._refresh_row_marks(index)
        self._refresh_status()

    def _refresh_row_marks(self,index:int)->None:
        """Show or hide the row's mark badge in place, so highlighting a phrase is visible
        in the transcript straight away rather than at the next full render."""
        parts=(self.refs.get("rows") or {}).get(index)
        badge=(parts or {}).get("marked")
        if badge is None: return
        badge.visible=carries_marks(self.controller.state.transcript_segments[index])
        self._safe_update(badge)

    # ── Navigation and chrome ────────────────────────────────────────────────
    def finish_welcome(self)->None:
        self.controller.state.first_run=False;self.preferences["welcome_seen"]=True;save_preferences(self.preferences);self.render()
    def reset_welcome(self)->None:
        self.preferences["welcome_seen"]=False;save_preferences(self.preferences)
        self.controller.state.first_run=True;self.show_settings=False;self.render()
    def show_help(self)->None:
        def section(heading:str,lines:tuple[str,...])->list[ft.Control]:
            return [ft.Text(heading,size=t.TYPE_LABEL,weight=ft.FontWeight.W_600,color=t.primary()),
                *[ft.Text(line,size=t.TYPE_SECONDARY,color=t.on_surface()) for line in lines],
                ft.Container(height=t.S8)]
        body=ft.Column([*section(s.HELP_NEW_HEADING,s.HELP_STEPS),
            *section(s.HELP_OPEN_HEADING,s.HELP_OPEN_STEPS),
            *section(s.HELP_SHORTCUTS_HEADING,s.shortcuts(t.SKIP_SECONDS))],tight=True,spacing=t.S4,
            scroll=ft.ScrollMode.AUTO)
        modal_dialog(self.page,s.HELP_TITLE,body,[ft.Button(s.HELP_UNDERSTOOD,on_click=lambda e:self.page.pop_dialog())])
    def show_missing_tools(self)->None:missing_ffmpeg_dialog(self.page,self.choose_media_folder,self.show_ffmpeg_instructions)
    def show_ffmpeg_instructions(self)->None:message_dialog(self.page,s.FFMPEG_INSTRUCTIONS_TITLE,s.FFMPEG_INSTRUCTIONS_BODY)

    def navigate(self,step:int)->None:
        if self.controller.can_enter(step):
            self.show_settings=self.show_home=False
            self.controller.state.current_workflow_step=step;self.render()
    def open_settings(self)->None:self.show_settings=True;self.show_home=False;self.render()

    def go_home(self)->None:
        """The wordmark leads here: what the application is for, and how to work through it.

        It is a screen rather than a dialog because it is reference material — the shortcut
        list and the export table are things to read beside the work, not to dismiss.
        """
        self.show_home=True;self.show_settings=False;self.render()

    def leave_home(self)->None:
        """Back to whichever step the project is actually at."""
        self.show_home=False;self.render()
    def toggle_theme(self)->None:
        self.page.theme_mode=ft.ThemeMode.DARK if self.page.theme_mode!=ft.ThemeMode.DARK else ft.ThemeMode.LIGHT
        self.render()

    # ── Recording ────────────────────────────────────────────────────────────
    async def _choose_file(self)->None:
        files=await self.file_picker.pick_files(dialog_title=s.DIALOG_CHOOSE_RECORDING,allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["m4a","wav","mp3","mp4","aac","flac","webm"])
        if files and files[0].path:
            def worker()->None:
                try:
                    self.controller.select_recording(files[0].path);self.controller.set_range(None,None)
                    self.player.bind(self.controller.state.audio_path);self.render()
                except Exception as exc:error_notification(self.page,str(exc))
            self.page.run_thread(worker)
    def choose_file(self)->None:self.page.run_task(self._choose_file)

    def set_range(self,start_text:str,end_text:str)->str|None:
        """Validate the typed range and store it. Returns a message for the view, or None."""
        info=self.controller.state.selected_file_metadata
        try:
            selection=resolve(start_text,end_text,info.duration if info else 0)
        except TimeRangeError as exc:
            return str(exc)
        self.controller.set_range(selection.start if selection else None,selection.end if selection else None)
        self._refresh_status()
        return None

    async def _choose_media_folder(self)->None:
        try:self.page.pop_dialog()
        except Exception:pass
        path=await self.file_picker.get_directory_path(dialog_title=s.DIALOG_CHOOSE_FFMPEG)
        if path:
            resolved=resolve_media_tools([path])
            if resolved.is_valid:
                self.controller.state.media_tools=resolved;self.controller.state.settings.user_media_tool_path=path
                self.preferences["media_tool_path"]=path;save_preferences(self.preferences);self.render()
            else:message_dialog(self.page,s.FFMPEG_INVALID_FOLDER_TITLE,s.FFMPEG_INVALID_FOLDER_BODY)
    def choose_media_folder(self)->None:self.page.run_task(self._choose_media_folder)

    def remove_file(self)->None:
        self.controller.remove_recording()
        self.controller.state.media_tools=resolve_media_tools([self.preferences.get("media_tool_path","")]);self.render()
    def set_quality(self,preserve:bool)->None:
        self.controller.state.settings.preserve_original=preserve;self.controller.state.dirty=True;self._refresh_status()

    # ── Transcription ────────────────────────────────────────────────────────
    def begin_transcription(self,key:str)->None:
        self.controller.state.set_active_api_key(key);self.started_at=time.monotonic()
        def update(message:str,progress:float|None)->None:
            if progress is not None:self.controller.state.transcription_progress=progress
            self.controller.state.activity_log.append(message);self.render()
        def worker()->None:
            try:self.controller.start_transcription(update);self.render()
            except Exception as exc:error_notification(self.page,str(exc));self.render()
        self.page.run_thread(worker);self.render()

    # ── Speakers ─────────────────────────────────────────────────────────────
    def map_speaker(self,speaker:str,name:str)->None:
        self.controller.map_speaker(speaker,name);self._refresh_speaker(speaker)
    def reassign_turn(self,index:int,speaker_id:str)->None:
        """Move one turn to another speaker, straight from the inspector row."""
        if not self.controller.reassign_turn(index,speaker_id): return
        state=self.controller.state
        name=state.speaker_mapping.get(speaker_id,speaker_id)
        self.render()
        notification(self.page,s.REASSIGN_DONE.format(speaker=name))

    def merge_speakers(self,source:str,target:str)->None:
        """Fold one label into another, behind a confirmation that says what will happen."""
        state=self.controller.state
        stats=speaker_statistics(state.transcript_segments)
        count,duration=stats.get(source,(0,0.0))
        detail=s.MERGE_BODY.format(source=state.speaker_mapping.get(source,source),
            target=state.speaker_mapping.get(target,target),count=count,
            duration=format_timestamp(duration))
        confirm_dialog(self.page,s.MERGE_TITLE,detail,
            lambda:self._apply_merge(source,target),s.MERGE_CONFIRM)

    def _apply_merge(self,source:str,target:str)->None:
        moved=self.controller.merge_speakers(source,target)
        if not moved: return
        # The open turn may have belonged to the label that just disappeared.
        self.selected_segment=None
        name=self.controller.state.speaker_mapping.get(target,target)
        self.render()
        notification(self.page,s.MERGE_DONE.format(count=moved,target=name))
    def close_inspector(self)->None:
        self.selected_segment=None;self.render()


    def select_segment(self,index:int)->None:
        previous=self.selected_segment;self.selected_segment=index
        segments=self.controller.state.transcript_segments
        # Clicking a turn positions the player on its exact start.
        if self.player.ready and index<len(segments): self.player.seek(segments[index].absolute_start)
        # Opening the sheet takes width away from the body, so that transition rebuilds.
        layout=self.refs.get("layout")
        if layout is not None and not layout.docked_inspector and previous is None:
            self.render();return
        rows=self.refs.get("rows") or {};host=self.refs.get("inspector_host")
        touched:list[ft.Control]=[]
        for position in (previous,index):
            parts=rows.get(position) if position is not None else None
            if parts is None:continue
            # One painter for all three row states, so selection, playback and the reviewed
            # marker cannot overwrite one another.
            row_state(parts,selected=position==index)
            touched.append(parts["container"])
        if host is not None:
            host.content=self.build_inspector(index)
            touched.append(host)
        if not touched or not self._safe_update(*touched):self.render()
    def change_page(self,offset:int)->None:
        self.transcript_offset=offset;self.selected_segment=None;self.render()
    def save_correction(self,index:int,text:str)->None:
        """The button under the box. Saving a correction is also saying you checked it.

        The box is brought into line with the text being saved first, so the commit that
        `set_checked` performs sees the same value and cannot write an older one back over
        it. One source of truth, rather than two that happen to agree.
        """
        field=self.refs.get("inspector_field")
        if field is not None: field.value=text
        self.controller.correct_segment(index,text);self._refresh_row_text(index)
        self.set_checked(index,True)
    def revert_correction(self,index:int)->None:
        self.controller.correct_segment(index,None);self._refresh_row_text(index)
        host=self.refs.get("inspector_host")
        if host is not None:
            host.content=self.build_inspector(index)
            self._safe_update(host)
    def play_segment(self,index:int)->None:
        """Seek the persistent player to this turn's exact start; no clip is cut."""
        segments=self.controller.state.transcript_segments
        if index>=len(segments): return
        if not self.player.ready:
            error_notification(self.page,s.AUDIO_MISSING_TITLE);return
        self.player.seek(segments[index].absolute_start)

    # ── Export and projects ──────────────────────────────────────────────────
    def set_export_metadata(self,title:str,project:str,date:str,notes:str,timestamps:bool,notice:bool,labels:bool)->None:
        self.controller.state.export_metadata=ExportMetadata(title,project,date,notes,timestamps,notice,labels)
        self.controller.state.dirty=True;self._refresh_status()
    async def _save_export(self,kind:str)->None:
        info=self.controller.state.selected_file_metadata
        name=s.EXPORT_FILENAME.format(stem=Path(info.filename).stem if info else "transcript",ext=kind)
        path=await self.file_picker.save_file(dialog_title=s.DIALOG_SAVE_EXPORT,file_name=name,
            file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=[kind])
        if path:
            try:self.controller.save_export(kind,path);self.render()
            except Exception as exc:error_notification(self.page,str(exc))
    def save_export(self,kind:str)->None:self.page.run_task(self._save_export,kind)

    def save_target(self)->str:
        """Where Save writes without asking: the file this project already came from.

        Empty until the project has been saved or opened once, which is the only moment a
        dialog is genuinely needed. After that, asking again on every save is a question
        with one possible answer.
        """
        path=self.controller.state.project_path or ""
        return path if path and Path(path).parent.is_dir() else ""

    def save_project(self)->None:
        """Ctrl+S and the Save button. Straight to the known file, or ask once."""
        target=self.save_target()
        if not target:
            self.page.run_task(self._save_project);return
        try:
            self.controller.save_project(target)
        except Exception as exc:
            error_notification(self.page,str(exc));return
        # No dialog means no feedback unless we give some; the top bar flips to Saved too.
        notification(self.page,s.SAVED_TO.format(name=Path(target).name))
        self._refresh_status()
        self._refresh_save_button()

    def save_project_as(self)->None:
        """Ctrl+Shift+S: the way to a different file once one is remembered."""
        self.page.run_task(self._save_project)

    async def _save_project(self)->None:
        current=self.save_target()
        path=await self.file_picker.save_file(dialog_title=s.DIALOG_SAVE_PROJECT,
            file_name=Path(current).name if current else s.DEFAULT_PROJECT_FILENAME,
            file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["json"])
        if path:
            if not path.lower().endswith(".transcript.json"):path=str(Path(path).with_suffix(".transcript.json"))
            try:self.controller.save_project(path);self.render()
            except Exception as exc:error_notification(self.page,str(exc))

    def _refresh_save_button(self)->None:
        button=self.refs.get("save_button")
        if button is None: return
        target=self.save_target()
        button.tooltip=(s.SAVE_PROJECT_TO.format(name=Path(target).name) if target
                        else s.SAVE_PROJECT_TOOLTIP)
        self._safe_update(button)
    async def _open_project(self)->None:
        files=await self.file_picker.pick_files(dialog_title=s.DIALOG_OPEN_PROJECT,allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["json"])
        if files and files[0].path:
            try:
                self.controller.load_project(files[0].path)
                self.controller.state.media_tools=resolve_media_tools([self.preferences.get("media_tool_path","")])
                # Rebind silently when the recording is still where the project says it is.
                state=self.controller.state
                self.player.unbind()
                if state.audio_path: self.player.bind(state.audio_path)
                self.selected_segment=None;self.transcript_offset=0;self.render()
            except Exception as exc:error_notification(self.page,str(exc))
    def open_project(self)->None:self.page.run_task(self._open_project)
    def new_project(self)->None:
        def reset()->None:
            self.controller.state.reset();self.selected_segment=None;self.transcript_offset=0
            self.controller.state.media_tools=resolve_media_tools([self.preferences.get("media_tool_path","")]);self.render()
        if self.controller.state.dirty:confirm_dialog(self.page,s.UNSAVED_TITLE,s.UNSAVED_BODY,reset)
        else:reset()

    def apply_settings(self,appearance:str,size:float,bitrate:int,overlap:float,include:bool,
                       _unused:bool=False,
                       provider:str|None=None,language:str|None=None,speakers:str|int|None=None,
                       base_url:str|None=None,model:str|None=None,
                       auto_rewind:bool|None=None,rewind_seconds:str|float|None=None,
                       type_scale:str|float|None=None,
                       highlight_labels:list[str]|None=None,
                       reviewer:str|None=None)->None:
        state=self.controller.state;settings=state.settings
        settings.appearance=appearance;settings.safe_chunk_mb=max(5,min(size,23))
        settings.fallback_bitrate_kbps=max(24,min(bitrate,128));settings.overlap_seconds=max(0,min(overlap,60))
        settings.include_source_path_json=include
        settings.provider=provider or settings.provider;settings.language=language or settings.language
        try:settings.expected_speakers=max(0,min(int(str(speakers).strip() or 0),20))
        except (TypeError,ValueError):pass
        # The generic endpoint's address and model stay in memory; they never reach preferences.
        if base_url is not None:state.compatible_base_url=base_url.strip()
        if model is not None:state.compatible_model=model.strip()
        if auto_rewind is not None:settings.auto_rewind_enabled=bool(auto_rewind)
        if rewind_seconds is not None:
            try:settings.auto_rewind_seconds=max(0.0,min(float(str(rewind_seconds).strip() or 1.5),5.0))
            except (TypeError,ValueError):pass
        if type_scale is not None:
            try:settings.type_scale=max(0.8,min(float(str(type_scale).strip() or 1.0),1.4))
            except (TypeError,ValueError):pass
            t.set_type_scale(settings.type_scale)
        if highlight_labels is not None:
            # Three names, kept in slot order; a blank one falls back to "Colour N" wherever
            # the name is shown, so clearing a name is allowed rather than punished.
            settings.highlight_labels=[str(name)[:40] for name in (list(highlight_labels)+["","",""])[:3]]
        if reviewer is not None: settings.reviewer=str(reviewer).strip()[:80]
        self.apply_rewind()
        self.preferences.update({"appearance":appearance,"media_tool_path":settings.user_media_tool_path,
            "provider":settings.provider,"language":settings.language,"expected_speakers":settings.expected_speakers,
            "auto_rewind_enabled":settings.auto_rewind_enabled,"auto_rewind_seconds":settings.auto_rewind_seconds,
            "type_scale":settings.type_scale,"highlight_labels":settings.highlight_labels,"reviewer":settings.reviewer})
        save_preferences(self.preferences)
        self.page.theme_mode={"light":ft.ThemeMode.LIGHT,"dark":ft.ThemeMode.DARK,"system":ft.ThemeMode.SYSTEM}.get(appearance,ft.ThemeMode.LIGHT)
        self.show_settings=False;self.render()


def main(page:ft.Page)->None:DesktopApp(page)
if __name__=="__main__":ft.run(main,assets_dir="assets")
