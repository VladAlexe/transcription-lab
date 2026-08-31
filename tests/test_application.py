from __future__ import annotations
import json, unittest
from pathlib import Path
from app_controller import AppController
from audio_processing import estimate_chunk_duration, estimated_chunk_count
from document_export import make_docx, project_payload
from models import AudioChunk, AudioInfo, TranscriptSegment
from speaker_reconciliation import apply_speaker_mapping, initialize_mapping
from transcription import parse_response, transcribe_chunks
from media_tools import resolve_media_tools


def segment(start:float=10,text:str="Text original") -> TranscriptSegment:
    return TranscriptSegment(1,0,"A","Fragment 01 · Speaker A",start,start+2,start,start+2,text)


class ApplicationTests(unittest.TestCase):
    def setUp(self)->None:
        self.info=AudioInfo(r"C:\audio\test.m4a","test.m4a",128*1024*1024,7200,"aac",44100,2,149000)
        self.chunk=AudioChunk(2,"chunk.m4a",100,120,1000,"copiere flux",20)

    def test_timestamp_offset_and_diarized_parsing(self)->None:
        parsed=parse_response({"segments":[{"speaker":"1","start":3.5,"end":8,"text":"Salut"}]},self.chunk)[0]
        self.assertEqual(parsed.local_start,3.5);self.assertEqual(parsed.absolute_start,103.5)
        self.assertEqual(parsed.speaker_id,"Fragment 02 · Speaker 1");self.assertTrue(parsed.in_overlap)

    def test_speaker_mapping(self)->None:
        item=segment();mapping=initialize_mapping([item]);mapping[item.speaker_id]="Moderator"
        self.assertEqual(apply_speaker_mapping(item,mapping),"Moderator")

    def test_transcript_sorting(self)->None:
        import transcription
        original=transcription.transcribe_chunk
        try:
            transcription.transcribe_chunk=lambda key,chunk:[segment(20 if chunk.index==1 else 5)]
            chunks=[AudioChunk(1,"",0,1,1,""),AudioChunk(2,"",0,1,1,"")]
            result=transcribe_chunks("secret",chunks)
            self.assertEqual([x.absolute_start for x in result],[5,20])
        finally:transcription.transcribe_chunk=original

    def test_chunk_estimation(self)->None:
        duration=estimate_chunk_duration(self.info,23);self.assertGreaterEqual(duration,18*60);self.assertLessEqual(duration,22*60)
        self.assertGreaterEqual(estimated_chunk_count(self.info,0,23),6)

    def test_project_json_round_trip_without_key(self)->None:
        item=segment();data=project_payload(self.info,[self.chunk],[item],{item.speaker_id:"Participant"},"date",{},False,2)
        raw=json.dumps(data,ensure_ascii=False);self.assertNotIn("api_key",raw);self.assertNotIn("secret",raw)
        path=Path("tests")/"project_roundtrip.tmp"
        try:
            path.write_text(raw,encoding="utf-8")
            controller=AppController();controller.load_project(str(path))
            self.assertEqual(controller.state.transcript_segments[0].original_text,"Text original")
            self.assertEqual(controller.state.speaker_mapping[item.speaker_id],"Participant")
        finally:
            path.unlink(missing_ok=True)

    def test_docx_generation(self)->None:
        item=segment();result=make_docx(self.info,[item],{item.speaker_id:"Moderator"},"date")
        self.assertTrue(result.startswith(b"PK"));self.assertGreater(len(result),10000)

    def test_bundled_media_tools_are_valid_and_paired(self)->None:
        tools=resolve_media_tools()
        self.assertTrue(tools.is_valid);self.assertEqual(tools.source_type,"bundled")
        self.assertEqual(Path(tools.ffmpeg_path).parent,Path(tools.ffprobe_path).parent)
        self.assertTrue(Path(tools.ffmpeg_path).is_absolute());self.assertIn("ffmpeg version",tools.version.lower())


if __name__=="__main__":unittest.main()
