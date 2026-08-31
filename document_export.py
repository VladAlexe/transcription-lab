from __future__ import annotations
import json
from io import BytesIO
from typing import Any
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from models import AudioChunk, AudioInfo, TranscriptSegment
from speaker_reconciliation import apply_speaker_mapping
from transcription import MODEL

APP_VERSION = "1.0.0"


def format_timestamp(seconds: float) -> str:
    total=max(0,int(seconds)); hours, rem=divmod(total,3600); minutes, secs=divmod(rem,60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def readable_transcript(segments: list[TranscriptSegment], mapping: dict[str,str], timestamps: bool=True) -> str:
    blocks=[]
    for item in sorted(segments,key=lambda s:(s.absolute_start,s.absolute_end,s.chunk_index)):
        stamp=f" [{format_timestamp(item.absolute_start)}–{format_timestamp(item.absolute_end)}]" if timestamps else ""
        blocks.append(f"{apply_speaker_mapping(item,mapping)}{stamp}\n{item.text}")
    return "\n\n".join(blocks)


def project_payload(info: AudioInfo | None, chunks: list[AudioChunk], segments: list[TranscriptSegment], mapping: dict[str,str],
                    generated_at: str, metadata: dict[str,Any] | None=None, include_source_path: bool=False,
                    workflow_step: int=0) -> dict[str,Any]:
    audio = info.to_dict() if info else None
    if audio and not include_source_path: audio["path"] = ""
    return {"application_version":APP_VERSION,"project_format":"transcript-project-v1","source_filename":info.filename if info else "",
            "source_path":info.path if info and include_source_path else None,"source_duration":info.duration if info else 0,
            "audio_metadata":audio,"transcription_model":MODEL,"generation_date":generated_at,
            "chunks":[c.to_dict() for c in chunks],"speaker_mapping":mapping,
            "segments":[s.to_dict(apply_speaker_mapping(s,mapping)) for s in segments],
            "interview_metadata":metadata or {},"workflow_step":workflow_step}


def make_json(*args: Any, **kwargs: Any) -> bytes:
    return json.dumps(project_payload(*args,**kwargs),ensure_ascii=False,indent=2).encode("utf-8")


def _page_number(paragraph: Any) -> None:
    paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER; run=paragraph.add_run()
    begin=OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"),"begin")
    instruction=OxmlElement("w:instrText"); instruction.set(qn("xml:space"),"preserve"); instruction.text=" PAGE "
    end=OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"),"end"); run._r.extend([begin,instruction,end])


def make_docx(info: AudioInfo, segments: list[TranscriptSegment], mapping: dict[str,str], generated_at: str,
              title: str="Transcriere interviu de grup", metadata: dict[str,str] | None=None,
              include_timestamps: bool=True, include_notice: bool=True) -> bytes:
    try:
        document=Document(); section=document.sections[0]
        section.top_margin=section.bottom_margin=Cm(2.5); section.left_margin=section.right_margin=Cm(2.5)
        normal=document.styles["Normal"]; normal.font.name="Aptos"; normal.font.size=Pt(11)
        heading=document.add_heading(title or "Transcriere interviu de grup",0); heading.alignment=WD_ALIGN_PARAGRAPH.CENTER
        values={"Fișier original":info.filename,"Data generării":generated_at,"Durata înregistrării":format_timestamp(info.duration),
                "Model utilizat":MODEL}
        for key,value in (metadata or {}).items():
            if value: values[key]=value
        for label,value in values.items():
            p=document.add_paragraph(); p.add_run(f"{label}: ").bold=True; p.add_run(str(value))
        if include_notice:
            note=document.add_paragraph("Notă: transcrierea și identificarea vorbitorilor sunt automate și necesită verificare manuală."); note.runs[0].italic=True
        for item in sorted(segments,key=lambda s:(s.absolute_start,s.absolute_end,s.chunk_index)):
            line=document.add_paragraph(); line.paragraph_format.space_before=Pt(7); line.paragraph_format.space_after=Pt(2)
            line.add_run(apply_speaker_mapping(item,mapping)).bold=True
            if include_timestamps:
                stamp=line.add_run(f"  {format_timestamp(item.absolute_start)}–{format_timestamp(item.absolute_end)}"); stamp.font.color.rgb=RGBColor(100,105,110)
            body=document.add_paragraph(item.text); body.paragraph_format.space_after=Pt(5)
        _page_number(section.footer.paragraphs[0]); output=BytesIO(); document.save(output); return output.getvalue()
    except Exception as exc: raise RuntimeError(f"Documentul Word nu a putut fi generat: {exc}") from exc
