from __future__ import annotations
import json, tempfile, threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
from app_state import AppState, ExportMetadata, PreparationSettings
import strings as s
from audio_processing import compress_for_upload, extract_range, probe_audio, should_compress
from time_range import TimeRange, format_timecode, shift_segments
from document_export import make_docx, make_json, project_payload, readable_transcript
import find_replace
from models import AudioChunk, AudioInfo, TranscriptSegment
from providers import (PROVIDERS, DeepgramProvider, GladiaProvider, OpenAICompatibleProvider, OpenAIDiarizeProvider,
                       SonioxProvider, TranscriptionProvider, provider_capabilities, provider_info)
from speaker_reconciliation import initialize_mapping
from utils import human_size, load_json, write_bytes, write_text
import subprocess

Update = Callable[[str,float|None],None]


class AppController:
    def __init__(self,state:AppState|None=None): self.state=state or AppState(); self._lock=threading.Lock()

    def select_recording(self,path:str) -> AudioInfo:
        info=probe_audio(path,self.state.media_tools); self.state.selected_file_path=info.path; self.state.selected_file_metadata=info
        self.state.audio_filename=info.filename; self.state.audio_bytes=info.size_bytes; self.bind_audio(info.path)
        self.state.current_workflow_step=0; self.state.dirty=True; self.state.activity_log.append(s.LOG_FILE_ANALYSED); return info

    def remove_recording(self) -> None: self.state.reset()

    def can_enter(self,step:int)->bool:
        if step==0:return True
        if step==1:return self.state.selected_file_metadata is not None
        if step==2:return bool(self.state.transcript_segments)
        if step==3:return bool(self.state.transcript_segments)
        return True

    def build_provider(self,output_dir:str) -> TranscriptionProvider:
        state=self.state; settings=state.settings; cancelled=lambda:state.cancellation_flag
        if settings.provider==OpenAIDiarizeProvider.info.key:
            return OpenAIDiarizeProvider(state.api_key,output_dir,state.media_tools,settings.safe_chunk_mb,
                settings.fallback_bitrate_kbps,settings.overlap_seconds,not settings.preserve_original,cancelled)
        if settings.provider==DeepgramProvider.info.key: return DeepgramProvider(state.deepgram_api_key,cancelled)
        if settings.provider==SonioxProvider.info.key: return SonioxProvider(state.soniox_api_key,cancelled)
        if settings.provider==OpenAICompatibleProvider.info.key:
            return OpenAICompatibleProvider(state.compatible_api_key,state.compatible_base_url,state.compatible_model,cancelled)
        return GladiaProvider(state.gladia_api_key,cancelled)

    def selected_range(self) -> TimeRange | None:
        start,end=self.state.range_start,self.state.range_end
        if start is None and end is None: return None
        info=self.state.selected_file_metadata
        return TimeRange(start or 0.0,end if end is not None else (info.duration if info else 0.0))

    def prepare_source(self,info:AudioInfo,output_dir:str,update:Update,uploads_whole_file:bool=True) -> tuple[str,float]:
        """Return the path actually sent to the provider and the offset of its first sample.

        Two optional steps, in order: cut the chosen range, then — for providers that upload the
        whole file — re-encode a compact copy when the result is large. A multi-hundred-megabyte
        request is what stalls on an ordinary connection; tens of megabytes goes through.
        """
        settings=self.state.settings; selection=self.selected_range()
        source,offset=info,0.0
        if selection is not None:
            source=extract_range(info,output_dir,selection.start,selection.end,self.state.media_tools,
                not settings.preserve_original,settings.fallback_bitrate_kbps)
            offset=selection.start
            update(s.RANGE_CLIP_CREATED.format(duration=format_timecode(source.duration),
                start=format_timecode(selection.start)),None)
        if uploads_whole_file and should_compress(source.size_bytes,settings.upload_compress_above_mb):
            before=source.size_bytes
            update(s.COMPRESS_STARTED.format(size=human_size(before)),None)
            source=compress_for_upload(source,output_dir,self.state.media_tools,
                settings.upload_bitrate_kbps,lambda:self.state.cancellation_flag)
            update(s.COMPRESS_DONE.format(before=human_size(before),after=human_size(source.size_bytes)),None)
        return source.path,offset

    def set_range(self,start:float|None,end:float|None) -> None:
        self.state.range_start=start; self.state.range_end=end; self.state.dirty=True

    def start_transcription(self,update:Update) -> None:
        with self._lock:
            if self.state.processing: raise RuntimeError(s.ERROR_ALREADY_RUNNING)
            if not self.state.active_api_key.strip(): raise RuntimeError(provider_info(self.state.settings.provider).missing_key)
            if not self.state.selected_file_metadata: raise RuntimeError(s.ERROR_NO_RECORDING)
            self.state.processing=True; self.state.cancellation_flag=False; self.state.error_state=None
        try:
            self.state.cleanup_temporary(); self.state.temporary_directory=tempfile.TemporaryDirectory(prefix="transcriere_")
            info=self.state.selected_file_metadata; settings=self.state.settings
            provider=self.build_provider(self.state.temporary_directory.name)
            # Only the chosen portion is sent to the provider; the original is untouched.
            source_path,offset=self.prepare_source(info,self.state.temporary_directory.name,update,
                provider.info.uploads_whole_file)
            segments=provider.transcribe(source_path,settings.language,settings.expected_speakers,update)
            # The times that come back are relative to the clip, so they are re-anchored
            # onto the original recording.
            shift_segments(segments,offset)
            # Providers that fragment locally report their fragments; those that send the
            # whole file have none.
            self.state.generated_chunks=list(getattr(provider,"chunks",[]))
            self.state.chunk_metadata=[x.to_dict() for x in self.state.generated_chunks]
            self.state.transcript_segments=segments; self.state.speaker_mapping=initialize_mapping(segments)
            self.state.run_capabilities=provider.capabilities()
            self.state.transcription_provider=provider.info.key
            self.state.transcription_model=getattr(provider,"model",None) or provider.info.model
            self.state.generated_at=datetime.now().astimezone().isoformat(timespec="seconds")
            self.state.current_workflow_step=2; self.state.transcription_progress=1; self.state.dirty=True
            self.state.activity_log.append(s.LOG_MERGED_CHRONOLOGICALLY if self.state.generated_chunks else s.LOG_GLOBAL_SPEAKERS)
            update(s.LOG_FINISHED,1.0)
        except Exception as exc: self.state.error_state=str(exc); raise
        finally: self.state.processing=False

    def cancel(self)->None: self.state.cancellation_flag=True

    def map_speaker(self,speaker_id:str,name:str)->None:
        self.state.speaker_mapping[speaker_id]=name.strip() or speaker_id; self.state.dirty=True

    def correct_segment(self,index:int,text:str|None)->None:
        self.state.transcript_segments[index].corrected_text=text if text and text!=self.state.transcript_segments[index].original_text else None
        self.state.dirty=True

    # ── Who said this ────────────────────────────────────────────────────
    # Diarization labels a voice, not a person. These two corrections are the ones
    # researchers reach for: this turn belongs to someone else, and these two labels are
    # in fact the same person. Both touch `speaker_id` only — timings, wording and word
    # timestamps are never rewritten.
    def reassign_turn(self,index:int,speaker_id:str)->bool:
        """Move one turn to another speaker. False when it already belonged there."""
        if not (0<=index<len(self.state.transcript_segments)): return False
        segment=self.state.transcript_segments[index]
        if not speaker_id or segment.speaker_id==speaker_id: return False
        segment.speaker_id=speaker_id; self.state.dirty=True
        return True

    def merge_speakers(self,source:str,target:str)->int:
        """Fold every turn of `source` into `target`. Returns how many turns moved.

        The source label stops existing: its name mapping goes with it, so the panel and
        the exports agree that there is now one person where there were two.
        """
        if not source or not target or source==target: return 0
        moved=0
        for segment in self.state.transcript_segments:
            if segment.speaker_id==source:
                segment.speaker_id=target; moved+=1
        self.state.speaker_mapping.pop(source,None)
        if moved: self.state.dirty=True
        return moved

    # ── Find and replace ─────────────────────────────────────────────────
    def count_matches(self,term:str,options:"find_replace.Options")->int:
        return find_replace.count_matches(self.state.transcript_segments,term,options)

    def replace_all(self,term:str,replacement:str,options:"find_replace.Options"):
        """Rewrite every occurrence across the transcript, as one undoable step."""
        record=find_replace.replace_all(self.state.transcript_segments,term,replacement,options)
        if record.applied:
            self.state.last_replacement=record; self.state.dirty=True
        return record

    def undo_replace(self)->int:
        """Restore the text exactly as it was before the last replace-all."""
        record=self.state.last_replacement
        if record is None: return 0
        restored=find_replace.undo(self.state.transcript_segments,record)
        self.state.last_replacement=None
        if restored: self.state.dirty=True
        return restored

    # ── Audio reference ──────────────────────────────────────────────────
    # Per-turn FFmpeg clips are gone: one persistent player seeks the original recording, so
    # playback starts on the exact timestamp instead of a second early.
    def audio_candidates(self,data:dict[str,Any])->list[str]:
        """Paths a saved project may carry, newest field first.

        Projects written before this step have no `audio_path`, but many still record the
        recording's location under `source_path` or inside `audio_metadata`. Trying all three
        lets an older project rebind silently instead of always asking.
        """
        audio=data.get("audio_metadata") or {}
        candidates=[data.get("audio_path"),data.get("source_path"),audio.get("path")]
        return [str(item) for item in candidates if item]

    def bind_audio(self,path:str)->bool:
        """Record which recording the project plays from. False when the file is not there."""
        if not path or not Path(path).is_file(): return False
        resolved=Path(path).resolve()
        self.state.audio_path=str(resolved)
        if not self.state.audio_filename: self.state.audio_filename=resolved.name
        if not self.state.audio_bytes: self.state.audio_bytes=resolved.stat().st_size
        self.state.audio_missing=False
        return True

    def audio_matches(self,path:str)->bool:
        """A relocated recording is accepted when either its name or its size still matches."""
        candidate=Path(path)
        if not candidate.is_file(): return False
        if self.state.audio_filename and candidate.name==self.state.audio_filename: return True
        if self.state.audio_bytes and candidate.stat().st_size==self.state.audio_bytes: return True
        return False

    def save_export(self,kind:str,path:str)->None:
        info=self.state.selected_file_metadata
        if not info: raise RuntimeError(s.ERROR_METADATA_MISSING)
        meta=self.state.export_metadata; md={s.DOC_PROJECT_ID:meta.project_id,s.DOC_INTERVIEW_DATE:meta.interview_date,s.DOC_NOTES:meta.notes}
        if kind=="docx": write_bytes(path,make_docx(info,self.state.transcript_segments,self.state.speaker_mapping,self.state.generated_at,
            meta.title,md,meta.include_timestamps,meta.include_notice,self.state.transcription_model))
        elif kind=="txt": write_text(path,readable_transcript(self.state.transcript_segments,self.state.speaker_mapping,meta.include_timestamps))
        elif kind=="json":
            payload=project_payload(info,self.state.generated_chunks,self.state.transcript_segments,self.state.speaker_mapping,
                self.state.generated_at,md,self.state.settings.include_source_path_json,self.state.current_workflow_step,
                self.state.transcription_provider,self.state.transcription_model,self.state.range_start,self.state.range_end,
                self.state.last_reviewed_index)
            if not meta.include_original_labels:
                for item in payload["segments"]: item.pop("original_speaker",None);item.pop("speaker_id",None)
            write_bytes(path,json.dumps(payload,ensure_ascii=False,indent=2).encode("utf-8"))
        else: raise ValueError(kind)
        self.state.export_paths[kind]=path

    def save_project(self,path:str)->None:
        payload=project_payload(self.state.selected_file_metadata,self.state.generated_chunks,self.state.transcript_segments,
            self.state.speaker_mapping,self.state.generated_at,self.state.export_metadata.__dict__,True,self.state.current_workflow_step,
            self.state.transcription_provider,self.state.transcription_model,self.state.range_start,self.state.range_end,
            self.state.last_reviewed_index)
        # The player needs somewhere to come back to; the audio itself is never embedded.
        if not payload.get("audio_path") and self.state.audio_path: payload["audio_path"]=self.state.audio_path
        write_text(path,json.dumps(payload,ensure_ascii=False,indent=2)); self.state.project_path=path; self.state.dirty=False

    def load_project(self,path:str)->None:
        data=load_json(path)
        if data.get("project_format")!="transcript-project-v1": raise RuntimeError(s.ERROR_INCOMPATIBLE_PROJECT)
        audio=data.get("audio_metadata"); info=AudioInfo.from_dict(audio) if audio else None
        chunks=[AudioChunk.from_dict({**x,"path":""}) for x in data.get("chunks",[])]
        segments=[TranscriptSegment.from_dict(x) for x in data.get("segments",[])]
        self.state.cleanup_temporary(); self.state.selected_file_metadata=info; self.state.selected_file_path=info.path if info else None
        self.state.generated_chunks=chunks; self.state.chunk_metadata=data.get("chunks",[]); self.state.transcript_segments=segments
        self.state.speaker_mapping=data.get("speaker_mapping",{}); self.state.generated_at=data.get("generation_date","")
        # Older projects carry no provider; the saved model is the only clue left.
        def optional_number(value:Any)->float|None:
            try: return None if value is None else float(value)
            except (TypeError,ValueError): return None
        self.state.range_start=optional_number(data.get("transcription_range_start"))
        self.state.range_end=optional_number(data.get("transcription_range_end"))
        recorded=str(data.get("transcription_provider","") or "")
        self.state.transcription_model=str(data.get("transcription_model","") or "")
        if not recorded and self.state.transcription_model==OpenAIDiarizeProvider.info.model:
            recorded=OpenAIDiarizeProvider.info.key
        self.state.transcription_provider=recorded
        # The capabilities must describe the transcript that was LOADED, not whichever
        # provider happens to be selected right now.
        self.state.run_capabilities=provider_capabilities(recorded) if recorded in PROVIDERS else None
        # Reconnect the recording, or flag that it needs locating. Opening a project never
        # rewrites or migrates the file on disk.
        self.state.audio_filename=str(data.get("audio_filename") or data.get("source_filename") or "")
        try: self.state.audio_bytes=int(data.get("audio_bytes") or (info.size_bytes if info else 0))
        except (TypeError,ValueError): self.state.audio_bytes=0
        self.state.audio_path=""; self.state.audio_banner_dismissed=False; self.state.audio_missing=False
        bound=False
        for candidate in self.audio_candidates(data):
            if self.bind_audio(candidate): bound=True; break
        self.state.audio_missing=not bound
        self.state.export_metadata=ExportMetadata(**{k:v for k,v in data.get("interview_metadata",{}).items() if k in ExportMetadata.__dataclass_fields__})
        review=data.get("review") or {}
        try: stored=review.get("last_reviewed_turn_index")
        except AttributeError: stored=None
        self.state.last_reviewed_index=stored if isinstance(stored,int) and 0<=stored<len(segments) else None
        self.state.show_only_unchecked=False
        self.state.current_workflow_step=max(2,int(data.get("workflow_step",2))) if segments else 0
        self.state.project_path=path; self.state.dirty=False
