from __future__ import annotations
import json, tempfile, threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
from app_state import AppState, ExportMetadata, PreparationSettings
from audio_processing import create_chunks, probe_audio
from document_export import make_docx, make_json, project_payload, readable_transcript
from models import AudioChunk, AudioInfo, TranscriptSegment
from speaker_reconciliation import initialize_mapping
from transcription import MODEL, transcribe_chunks
from utils import load_json, write_bytes, write_text
import subprocess

Update = Callable[[str,float|None],None]


class AppController:
    def __init__(self,state:AppState|None=None): self.state=state or AppState(); self._lock=threading.Lock()

    def select_recording(self,path:str) -> AudioInfo:
        info=probe_audio(path,self.state.media_tools); self.state.selected_file_path=info.path; self.state.selected_file_metadata=info
        self.state.current_workflow_step=0; self.state.dirty=True; self.state.activity_log.append("Fișier analizat."); return info

    def remove_recording(self) -> None: self.state.reset()

    def can_enter(self,step:int)->bool:
        if step==0:return True
        if step==1:return self.state.selected_file_metadata is not None
        if step==2:return bool(self.state.transcript_segments)
        if step==3:return bool(self.state.transcript_segments)
        return True

    def start_transcription(self,update:Update) -> None:
        with self._lock:
            if self.state.processing: raise RuntimeError("Există deja o transcriere în curs.")
            if not self.state.api_key.strip(): raise RuntimeError("Introduceți cheia API OpenAI.")
            if not self.state.selected_file_metadata: raise RuntimeError("Selectați o înregistrare validă.")
            self.state.processing=True; self.state.cancellation_flag=False; self.state.error_state=None
        try:
            self.state.cleanup_temporary(); self.state.temporary_directory=tempfile.TemporaryDirectory(prefix="transcriere_")
            info=self.state.selected_file_metadata; settings=self.state.settings
            def prep(cur:int,total:int,msg:str)->None: update(msg,.35*cur/max(total,1))
            chunks=create_chunks(info,self.state.temporary_directory.name,settings.overlap_seconds,prep,settings.safe_chunk_mb,
                settings.fallback_bitrate_kbps,not settings.preserve_original,lambda:self.state.cancellation_flag,self.state.media_tools)
            self.state.generated_chunks=chunks; self.state.chunk_metadata=[x.to_dict() for x in chunks]
            self.state.activity_log.append(f"Au fost create {len(chunks)} fragmente temporare."); update("Pregătirea audio s-a încheiat.",.35)
            def api(cur:int,total:int,msg:str)->None: update(msg,.35+.65*(cur-1)/max(total,1))
            segments=transcribe_chunks(self.state.api_key,chunks,api,lambda:self.state.cancellation_flag)
            self.state.transcript_segments=segments; self.state.speaker_mapping=initialize_mapping(segments)
            self.state.generated_at=datetime.now().astimezone().isoformat(timespec="seconds")
            self.state.current_workflow_step=2; self.state.transcription_progress=1; self.state.dirty=True
            self.state.activity_log.append("Transcrierea a fost combinată cronologic."); update("Transcriere finalizată.",1.0)
        except Exception as exc: self.state.error_state=str(exc); raise
        finally: self.state.processing=False

    def cancel(self)->None: self.state.cancellation_flag=True

    def map_speaker(self,speaker_id:str,name:str)->None:
        self.state.speaker_mapping[speaker_id]=name.strip() or speaker_id; self.state.dirty=True

    def correct_segment(self,index:int,text:str|None)->None:
        self.state.transcript_segments[index].corrected_text=text if text and text!=self.state.transcript_segments[index].original_text else None
        self.state.dirty=True

    def create_audio_preview(self,index:int)->str:
        info=self.state.selected_file_metadata
        if not info or not Path(info.path).is_file(): raise RuntimeError("Fișierul audio original nu mai este disponibil.")
        item=self.state.transcript_segments[index]
        if not self.state.temporary_directory: self.state.temporary_directory=tempfile.TemporaryDirectory(prefix="transcriere_review_")
        start=max(0,item.absolute_start-1); duration=max(.5,item.absolute_end-item.absolute_start+2)
        target=Path(self.state.temporary_directory.name)/f"preview_{index:05d}.m4a"
        if not target.exists():
            if not self.state.media_tools.is_valid: raise RuntimeError("FFmpeg nu este disponibil.")
            result=subprocess.run([self.state.media_tools.ffmpeg_path,"-hide_banner","-loglevel","error","-y","-ss",f"{start:.3f}","-i",info.path,
                "-t",f"{duration:.3f}","-vn","-c:a","aac","-ac","1","-ar","16000","-b:a","48k",str(target)],
                capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),check=False)
            if result.returncode: raise RuntimeError(f"Previzualizarea audio nu a putut fi creată: {result.stderr.strip()}")
        self.state.preview_cache=[x for x in self.state.preview_cache if Path(x).exists()]
        self.state.preview_cache.append(str(target))
        while len(self.state.preview_cache)>8:
            old=Path(self.state.preview_cache.pop(0)); old.unlink(missing_ok=True)
        return str(target)

    def save_export(self,kind:str,path:str)->None:
        info=self.state.selected_file_metadata
        if not info: raise RuntimeError("Metadatele înregistrării lipsesc.")
        meta=self.state.export_metadata; md={"Identificator proiect":meta.project_id,"Data interviului":meta.interview_date,"Observații":meta.notes}
        if kind=="docx": write_bytes(path,make_docx(info,self.state.transcript_segments,self.state.speaker_mapping,self.state.generated_at,
            meta.title,md,meta.include_timestamps,meta.include_notice))
        elif kind=="txt": write_text(path,readable_transcript(self.state.transcript_segments,self.state.speaker_mapping,meta.include_timestamps))
        elif kind=="json":
            payload=project_payload(info,self.state.generated_chunks,self.state.transcript_segments,self.state.speaker_mapping,
                self.state.generated_at,md,self.state.settings.include_source_path_json,self.state.current_workflow_step)
            if not meta.include_original_labels:
                for item in payload["segments"]: item.pop("original_speaker",None);item.pop("speaker_id",None)
            write_bytes(path,json.dumps(payload,ensure_ascii=False,indent=2).encode("utf-8"))
        else: raise ValueError(kind)
        self.state.export_paths[kind]=path

    def save_project(self,path:str)->None:
        payload=project_payload(self.state.selected_file_metadata,self.state.generated_chunks,self.state.transcript_segments,
            self.state.speaker_mapping,self.state.generated_at,self.state.export_metadata.__dict__,True,self.state.current_workflow_step)
        write_text(path,json.dumps(payload,ensure_ascii=False,indent=2)); self.state.project_path=path; self.state.dirty=False

    def load_project(self,path:str)->None:
        data=load_json(path)
        if data.get("project_format")!="transcript-project-v1": raise RuntimeError("Fișierul nu este un proiect de transcriere compatibil.")
        audio=data.get("audio_metadata"); info=AudioInfo.from_dict(audio) if audio else None
        chunks=[AudioChunk.from_dict({**x,"path":""}) for x in data.get("chunks",[])]
        segments=[TranscriptSegment.from_dict(x) for x in data.get("segments",[])]
        self.state.cleanup_temporary(); self.state.selected_file_metadata=info; self.state.selected_file_path=info.path if info else None
        self.state.generated_chunks=chunks; self.state.chunk_metadata=data.get("chunks",[]); self.state.transcript_segments=segments
        self.state.speaker_mapping=data.get("speaker_mapping",{}); self.state.generated_at=data.get("generation_date","")
        self.state.export_metadata=ExportMetadata(**{k:v for k,v in data.get("interview_metadata",{}).items() if k in ExportMetadata.__dataclass_fields__})
        self.state.current_workflow_step=max(2,int(data.get("workflow_step",2))) if segments else 0
        self.state.project_path=path; self.state.dirty=False
