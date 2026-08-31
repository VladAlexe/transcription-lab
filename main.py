from __future__ import annotations
import os,time
from pathlib import Path
from urllib.parse import parse_qs,urlparse
import flet as ft
import design_tokens as t
from app_controller import AppController
from app_state import ExportMetadata
from components.app_shell import app_shell
from components.dialogs import confirm_dialog,error_notification,message_dialog,missing_ffmpeg_dialog,modal_dialog
from components.navigation_rail import navigation_rail
from components.top_bar import top_bar
from media_tools import resolve_media_tools
from models import AudioInfo,MediaToolPaths,TranscriptSegment
from theme import application_theme
from utils import load_preferences,open_with_system,save_preferences
from views import export_view,recording_view,settings_view,speakers_view,transcription_view,welcome_view


class DesktopApp:
    def __init__(self,page:ft.Page):
        self.page=page;self.controller=AppController();self.show_settings=False;self.selected_segment:int|None=None;self.transcript_offset=0
        self.started_at:float|None=None;self.file_picker=ft.FilePicker();self.preferences=load_preferences()
        self.controller.state.first_run=not bool(self.preferences.get("welcome_seen",False))
        self.controller.state.settings.appearance=str(self.preferences.get("appearance","light"))
        self.controller.state.settings.user_media_tool_path=str(self.preferences.get("media_tool_path",""))
        self.controller.state.media_tools=resolve_media_tools([self.controller.state.settings.user_media_tool_path])
        query=parse_qs(urlparse(page.route).query);query_screen=query.get("screen",[""])[0]
        if query.get("dark",[""])[0]=="1":self.controller.state.settings.appearance="dark"
        self._configure_visual_demo(os.environ.get("TRANSCRIERE_DEMO_SCREEN","") or query_screen)
        self.configure_page();self.render()
        if not self.controller.state.media_tools.is_valid:self.show_missing_tools()

    def _configure_visual_demo(self,screen:str)->None:
        """Populate deterministic UI states used only by screenshot quality checks."""
        if not screen:return
        state=self.controller.state;state.first_run=screen=="welcome"
        if screen=="missing":state.media_tools=MediaToolPaths()
        if screen in {"file","transcription","speakers","export"}:
            state.selected_file_metadata=AudioInfo(r"C:\Cercetare\Interviu_grup_07.m4a","Interviu_grup_07.m4a",134217728,7242,"aac",48000,2,148000)
            state.selected_file_path=state.selected_file_metadata.path
        if screen=="transcription":
            state.current_workflow_step=1;state.processing=True;state.transcription_progress=.47;state.generated_chunks=[]
            state.activity_log=["Fișier analizat.","Au fost create 6 fragmente temporare.","Se transcrie fragmentul 3 din 6."]
        if screen in {"speakers","export"}:
            state.transcript_segments=[TranscriptSegment(1,0,"A","Fragment 01 · Speaker A",i*18,i*18+14,i*18,i*18+14,
                text) for i,text in enumerate(["Bună ziua și vă mulțumesc că participați la discuție.","Cred că problema apare mai ales atunci când informațiile ajung prea târziu.",
                "Pentru echipa noastră, comunicarea directă a făcut diferența.","Aș adăuga că experiența diferă mult de la un participant la altul."]*8)]
            state.speaker_mapping={"Fragment 01 · Speaker A":"Moderator"};state.current_workflow_step=2 if screen=="speakers" else 3;state.generated_at="2026-07-19T12:00:00+03:00"

    def configure_page(self)->None:
        p=self.page;p.title="Transcriere interviuri";p.padding=0;p.theme=application_theme(False);p.dark_theme=application_theme(True)
        p.theme_mode={"dark":ft.ThemeMode.DARK,"system":ft.ThemeMode.SYSTEM}.get(self.controller.state.settings.appearance,ft.ThemeMode.LIGHT)
        p.window.width=1240;p.window.height=820;p.window.min_width=980;p.window.min_height=680;p.window.resizable=True;p.window.prevent_close=True
        p.window.on_event=self.window_event;p.on_resize=lambda e:self.render();p.run_task(p.window.center)

    def window_event(self,e:ft.WindowEvent)->None:
        if e.type==ft.WindowEventType.CLOSE:
            if self.controller.state.processing:message_dialog(self.page,"Procesare activă","Anulează procesarea și așteaptă încheierea cererii curente.");return
            self.controller.state.cleanup_temporary();self.page.run_task(self._safe_destroy)
    async def _safe_destroy(self)->None:
        try:await self.page.window.destroy()
        except RuntimeError:pass

    def render(self)->None:
        state=self.controller.state
        t.set_dark(self.page.theme_mode==ft.ThemeMode.DARK or self.page.theme_mode==ft.ThemeMode.SYSTEM and self.page.platform_brightness==ft.Brightness.DARK)
        if state.first_run:
            self.page.controls.clear();self.page.add(welcome_view.build(self.finish_welcome,self.show_help));self.page.update();return
        collapsed=(self.page.width or 1240)<1080
        inspector=None
        if self.show_settings:workspace=settings_view.build(state,self.apply_settings,self.choose_media_folder,self.reset_welcome)
        elif state.current_workflow_step==0:workspace=recording_view.build(state,self.choose_file,self.remove_file,lambda:self.navigate(1),self.set_quality)
        elif state.current_workflow_step==1:
            elapsed="00:00" if not self.started_at else f"{int(time.monotonic()-self.started_at)//60:02d}:{int(time.monotonic()-self.started_at)%60:02d}"
            workspace=transcription_view.build(state,self.begin_transcription,self.controller.cancel,elapsed)
        elif state.current_workflow_step==2:
            workspace=speakers_view.build(state,self.map_speaker,self.select_segment,self.play_segment,lambda:self.navigate(3),self.selected_segment,self.transcript_offset,self.change_page)
            if self.selected_segment is not None and not collapsed:
                inspector=speakers_view.inspector(state,self.selected_segment,self.save_correction,self.revert_correction,self.play_segment)
        else:workspace=export_view.build(state,self.save_export,self.set_export_metadata)
        nav=navigation_rail(state,collapsed,self.navigate,self.new_project,self.save_project,self.open_project)
        top=top_bar(state,self.open_settings,self.toggle_theme,self.show_help)
        self.page.controls.clear();self.page.add(app_shell(nav,top,workspace,inspector));self.page.update()

    def finish_welcome(self)->None:
        self.controller.state.first_run=False;self.preferences["welcome_seen"]=True;save_preferences(self.preferences);self.render()
    def reset_welcome(self)->None:self.preferences["welcome_seen"]=False;save_preferences(self.preferences);self.controller.state.first_run=True;self.show_settings=False;self.render()
    def show_help(self)->None:
        modal_dialog(self.page,"Cum funcționează",ft.Column([ft.Text("1. Selectează înregistrarea locală.",size=13.5),ft.Text("2. Introdu cheia API și pornește transcrierea.",size=13.5),
            ft.Text("3. Verifică vorbitorii și corectează textul.",size=13.5),ft.Text("4. Exportă Word, text sau JSON.",size=13.5)],tight=True),
            [ft.Button("Am înțeles",on_click=lambda e:self.page.pop_dialog())])
    def show_missing_tools(self)->None:missing_ffmpeg_dialog(self.page,self.choose_media_folder,self.show_ffmpeg_instructions)
    def show_ffmpeg_instructions(self)->None:message_dialog(self.page,"Instrucțiuni FFmpeg","Instalează prin WinGet sau selectează un folder care conține împreună ffmpeg.exe și ffprobe.exe.\n\nwinget install --id Gyan.FFmpeg -e")

    def navigate(self,step:int)->None:
        if self.controller.can_enter(step):self.show_settings=False;self.controller.state.current_workflow_step=step;self.render()
    def open_settings(self)->None:self.show_settings=True;self.render()
    def toggle_theme(self)->None:
        self.page.theme_mode=ft.ThemeMode.DARK if self.page.theme_mode!=ft.ThemeMode.DARK else ft.ThemeMode.LIGHT
        self.render()

    async def _choose_file(self)->None:
        files=await self.file_picker.pick_files(dialog_title="Alege înregistrarea",allow_multiple=False,file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["m4a","wav","mp3","mp4","aac","flac","webm"])
        if files and files[0].path:
            def worker()->None:
                try:self.controller.select_recording(files[0].path);self.render()
                except Exception as exc:error_notification(self.page,str(exc))
            self.page.run_thread(worker)
    def choose_file(self)->None:self.page.run_task(self._choose_file)

    async def _choose_media_folder(self)->None:
        try:self.page.pop_dialog()
        except Exception:pass
        path=await self.file_picker.get_directory_path(dialog_title="Alege folderul FFmpeg")
        if path:
            resolved=resolve_media_tools([path])
            if resolved.is_valid:
                self.controller.state.media_tools=resolved;self.controller.state.settings.user_media_tool_path=path
                self.preferences["media_tool_path"]=path;save_preferences(self.preferences);self.render()
            else:message_dialog(self.page,"Folder invalid","Folderul trebuie să conțină ffmpeg.exe și ffprobe.exe funcționale.")
    def choose_media_folder(self)->None:self.page.run_task(self._choose_media_folder)

    def remove_file(self)->None:self.controller.remove_recording();self.controller.state.media_tools=resolve_media_tools([self.preferences.get("media_tool_path","")]);self.render()
    def set_quality(self,preserve:bool)->None:self.controller.state.settings.preserve_original=preserve;self.controller.state.dirty=True
    def begin_transcription(self,key:str)->None:
        self.controller.state.api_key=key;self.started_at=time.monotonic()
        def update(message:str,progress:float|None)->None:
            if progress is not None:self.controller.state.transcription_progress=progress
            self.controller.state.activity_log.append(message);self.render()
        def worker()->None:
            try:self.controller.start_transcription(update);self.render()
            except Exception as exc:error_notification(self.page,str(exc));self.render()
        self.page.run_thread(worker);self.render()
    def map_speaker(self,speaker:str,name:str)->None:self.controller.map_speaker(speaker,name);self.render()
    def select_segment(self,index:int)->None:self.selected_segment=index;self.render()
    def change_page(self,offset:int)->None:self.transcript_offset=offset;self.selected_segment=None;self.render()
    def save_correction(self,index:int,text:str)->None:self.controller.correct_segment(index,text);self.render()
    def revert_correction(self,index:int)->None:self.controller.correct_segment(index,None);self.render()
    def play_segment(self,index:int)->None:
        def worker()->None:
            try:open_with_system(self.controller.create_audio_preview(index))
            except Exception as exc:error_notification(self.page,str(exc))
        self.page.run_thread(worker)

    def set_export_metadata(self,title:str,project:str,date:str,notes:str,timestamps:bool,notice:bool,labels:bool)->None:
        self.controller.state.export_metadata=ExportMetadata(title,project,date,notes,timestamps,notice,labels);self.controller.state.dirty=True
    async def _save_export(self,kind:str)->None:
        ext={"docx":"docx","txt":"txt","json":"json"}[kind];info=self.controller.state.selected_file_metadata
        path=await self.file_picker.save_file(dialog_title="Salvează exportul",file_name=f"{Path(info.filename).stem}_transcriere.{ext}" if info else f"transcriere.{ext}",file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=[ext])
        if path:
            try:self.controller.save_export(kind,path);self.render()
            except Exception as exc:error_notification(self.page,str(exc))
    def save_export(self,kind:str)->None:self.page.run_task(self._save_export,kind)

    async def _save_project(self)->None:
        path=await self.file_picker.save_file(dialog_title="Salvează proiectul",file_name="proiect.transcript.json",file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["json"])
        if path:
            if not path.lower().endswith(".transcript.json"):path=str(Path(path).with_suffix(".transcript.json"))
            try:self.controller.save_project(path);self.render()
            except Exception as exc:error_notification(self.page,str(exc))
    def save_project(self)->None:self.page.run_task(self._save_project)
    async def _open_project(self)->None:
        files=await self.file_picker.pick_files(dialog_title="Deschide proiect",allow_multiple=False,file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["json"])
        if files and files[0].path:
            try:self.controller.load_project(files[0].path);self.controller.state.media_tools=resolve_media_tools([self.preferences.get("media_tool_path","")]);self.render()
            except Exception as exc:error_notification(self.page,str(exc))
    def open_project(self)->None:self.page.run_task(self._open_project)
    def new_project(self)->None:
        def reset()->None:self.controller.state.reset();self.controller.state.media_tools=resolve_media_tools([self.preferences.get("media_tool_path","")]);self.render()
        if self.controller.state.dirty:confirm_dialog(self.page,"Modificări nesalvate","Proiectul curent conține modificări nesalvate. Continui?",reset)
        else:reset()
    def apply_settings(self,appearance:str,size:float,bitrate:int,overlap:float,include:bool,diagnostic:bool)->None:
        s=self.controller.state.settings;s.appearance=appearance;s.safe_chunk_mb=max(5,min(size,23));s.fallback_bitrate_kbps=max(24,min(bitrate,128));s.overlap_seconds=max(0,min(overlap,60));s.include_source_path_json=include;s.diagnostic_logging=diagnostic
        self.preferences.update({"appearance":appearance,"media_tool_path":s.user_media_tool_path});save_preferences(self.preferences)
        self.page.theme_mode={"light":ft.ThemeMode.LIGHT,"dark":ft.ThemeMode.DARK,"system":ft.ThemeMode.SYSTEM}.get(appearance,ft.ThemeMode.LIGHT);self.show_settings=False;self.render()


def main(page:ft.Page)->None:DesktopApp(page)
if __name__=="__main__":ft.run(main,assets_dir="assets")
