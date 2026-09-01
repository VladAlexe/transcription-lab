"""Teste pentru stratul de furnizori și pentru compatibilitatea proiectelor salvate.

Niciun test nu contactează un API real: cererile HTTP sunt înlocuite cu răspunsuri simulate.
"""
from __future__ import annotations

import email.message
import inspect
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from models import AudioChunk, TranscriptSegment, Word
from providers import DEFAULT_PROVIDER, PROVIDERS, provider_info
from providers.base import ProviderError, TranscriptionProvider
from providers.deepgram import DeepgramProvider, parse_response
from providers.openai_diarize import OpenAIDiarizeProvider

# Doi vorbitori, fiecare revenind la finalul înregistrării: dovada că numerotarea este globală.
DEEPGRAM_PAYLOAD = {
    "metadata": {"duration": 7837.5},
    "results": {"utterances": [
        {"start": 0.5, "end": 3.2, "speaker": 0, "confidence": 0.94, "transcript": "Bună ziua tuturor.",
         "words": [{"word": "buna", "punctuated_word": "Bună", "start": 0.5, "end": 0.9, "confidence": 0.97, "speaker": 0},
                   {"word": "ziua", "punctuated_word": "ziua", "start": 0.9, "end": 1.4, "confidence": 0.95, "speaker": 0},
                   {"word": "tuturor", "punctuated_word": "tuturor.", "start": 1.4, "end": 3.2, "confidence": 0.90, "speaker": 0}]},
        {"start": 3.4, "end": 6.0, "speaker": 1, "confidence": 0.88, "transcript": "Mulțumim pentru invitație.",
         "words": [{"word": "multumim", "punctuated_word": "Mulțumim", "start": 3.4, "end": 4.1, "confidence": 0.89, "speaker": 1},
                   {"word": "pentru", "punctuated_word": "pentru", "start": 4.1, "end": 4.6, "confidence": 0.92, "speaker": 1},
                   {"word": "invitatie", "punctuated_word": "invitație.", "start": 4.6, "end": 6.0, "confidence": 0.85, "speaker": 1}]},
        {"start": 7200.0, "end": 7205.5, "speaker": 0, "confidence": 0.91, "transcript": "Închidem aici discuția.",
         "words": [{"word": "inchidem", "punctuated_word": "Închidem", "start": 7200.0, "end": 7201.0, "confidence": 0.93, "speaker": 0}]},
    ]},
}


class _FakeResponse:
    def __init__(self, payload: dict) -> None: self._body = json.dumps(payload).encode("utf-8"); self.status = 200
    def read(self) -> bytes: return self._body
    def __enter__(self) -> "_FakeResponse": return self
    def __exit__(self, *exc: object) -> bool: return False


def _drain(request: object) -> None:
    """Consumă corpul cererii exact cum ar face http.client, ca progresul încărcării să fie raportat."""
    body = getattr(request, "data", None)
    if hasattr(body, "read"):
        while body.read(8192): pass


def _fake_urlopen(payload: dict, calls: list[str]):
    def handler(request, timeout=None):
        calls.append(request.full_url); _drain(request); return _FakeResponse(payload)
    return handler


def _http_error(code: int, message: str = "unsupported parameter") -> HTTPError:
    body = io.BytesIO(json.dumps({"err_msg": message}).encode("utf-8"))
    return HTTPError("https://api.deepgram.com/v1/listen", code, message, email.message.Message(), body)


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


class DeepgramProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="deepgram_test_")
        self.audio = Path(self._temp.name) / "interviu.m4a"
        self.audio.write_bytes(b"0" * 40_000)
        self.addCleanup(self._temp.cleanup)

    def transcribe(self, payload: dict = DEEPGRAM_PAYLOAD, expected_speakers: int = 5, progress=None):
        calls: list[str] = []
        with mock.patch("providers.deepgram.urlopen", _fake_urlopen(payload, calls)):
            segments = DeepgramProvider("test-key").transcribe(str(self.audio), "ro", expected_speakers, progress)
        return segments, calls

    def test_speaker_ids_are_global_across_the_whole_file(self) -> None:
        segments, _ = self.transcribe()
        self.assertEqual(len(segments), 3)
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1", "Speaker 2"})
        # Prima și ultima intervenție aparțin aceleiași persoane, la peste două ore distanță.
        self.assertEqual(segments[0].speaker_id, segments[-1].speaker_id)
        self.assertNotIn("Fragment", segments[0].speaker_id)

    def test_absolute_times_need_no_chunk_offset(self) -> None:
        segments, _ = self.transcribe()
        last = segments[-1]
        self.assertEqual(last.absolute_start, 7200.0)
        self.assertEqual(last.local_start, last.absolute_start)
        self.assertEqual(last.chunk_index, 0)
        self.assertEqual(last.chunk_start_offset, 0.0)
        self.assertFalse(last.in_overlap)

    def test_words_and_confidence_are_captured(self) -> None:
        segments, _ = self.transcribe()
        first = segments[0]
        self.assertAlmostEqual(first.confidence or 0, 0.94)
        self.assertEqual([word.text for word in first.words], ["Bună", "ziua", "tuturor."])
        self.assertAlmostEqual(first.words[0].confidence or 0, 0.97)
        self.assertAlmostEqual(first.words[-1].end, 3.2)

    def test_request_enables_diarization_and_carries_language_and_hint(self) -> None:
        _, calls = self.transcribe(expected_speakers=5)
        query = _query(calls[0])
        self.assertEqual(query["diarize"], ["true"])
        self.assertEqual(query["utterances"], ["true"])
        self.assertEqual(query["language"], ["ro"])
        self.assertEqual(query["speakers_expected"], ["5"])

    def test_speaker_hint_is_advisory_and_never_fails(self) -> None:
        calls: list[str] = []

        def handler(request, timeout=None):
            calls.append(request.full_url); _drain(request)
            if "speakers_expected" in request.full_url: raise _http_error(400)
            return _FakeResponse(DEEPGRAM_PAYLOAD)

        with mock.patch("providers.deepgram.urlopen", handler):
            segments = DeepgramProvider("test-key").transcribe(str(self.audio), "ro", 5)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("speakers_expected", _query(calls[1]))
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1", "Speaker 2"})

    def test_hint_is_omitted_when_no_count_is_configured(self) -> None:
        _, calls = self.transcribe(expected_speakers=0)
        self.assertNotIn("speakers_expected", _query(calls[0]))

    def test_progress_covers_upload_and_ends_complete(self) -> None:
        events: list[tuple[str, float | None]] = []
        self.transcribe(progress=lambda message, fraction: events.append((message, fraction)))
        fractions = [fraction for _, fraction in events if fraction is not None]
        self.assertTrue(any("Uploading" in message for message, _ in events))
        self.assertTrue(any("processing" in message for message, _ in events))
        self.assertEqual(fractions, sorted(fractions))
        self.assertLessEqual(max(fractions), 1.0)

    def test_missing_key_and_missing_file_are_reported(self) -> None:
        with self.assertRaises(ProviderError): DeepgramProvider("").transcribe(str(self.audio))
        with self.assertRaises(ProviderError): DeepgramProvider("k").transcribe(str(self.audio.with_name("lipsa.m4a")))

    def test_authentication_failure_is_translated(self) -> None:
        def handler(request, timeout=None):
            _drain(request); raise _http_error(401, "invalid credentials")

        with mock.patch("providers.deepgram.urlopen", handler):
            with self.assertRaises(ProviderError) as caught:
                DeepgramProvider("bad").transcribe(str(self.audio), "ro", 0)
        self.assertIn("Deepgram", str(caught.exception))

    def test_word_level_fallback_when_utterances_are_absent(self) -> None:
        payload = {"results": {"channels": [{"alternatives": [{"words": [
            {"punctuated_word": "Prima", "start": 0.0, "end": 0.5, "confidence": 0.9, "speaker": 0},
            {"punctuated_word": "replică.", "start": 0.5, "end": 1.0, "confidence": 0.8, "speaker": 0},
            {"punctuated_word": "A", "start": 1.2, "end": 1.4, "confidence": 0.7, "speaker": 1},
            {"punctuated_word": "doua.", "start": 1.4, "end": 1.9, "confidence": 0.9, "speaker": 1}]}]}]}}
        segments = parse_response(payload)
        self.assertEqual([item.speaker_id for item in segments], ["Speaker 1", "Speaker 2"])
        self.assertEqual(segments[0].original_text, "Prima replică.")
        self.assertAlmostEqual(segments[0].confidence or 0, 0.85)

    def test_empty_response_raises(self) -> None:
        with self.assertRaises(ProviderError): parse_response({"results": {"utterances": []}})


class ProviderInterfaceTests(unittest.TestCase):
    def test_whole_file_providers_declare_global_speakers(self) -> None:
        self.assertTrue(provider_info("deepgram").capabilities.global_speakers)
        self.assertFalse(provider_info("openai").capabilities.global_speakers)

    def test_unknown_key_falls_back_to_default(self) -> None:
        self.assertEqual(provider_info("inexistent").key, DEFAULT_PROVIDER)

    def test_every_provider_implements_the_interface(self) -> None:
        for key, provider in PROVIDERS.items():
            with self.subTest(provider=key):
                self.assertTrue(issubclass(provider, TranscriptionProvider))
                self.assertEqual(provider.info.key, key)
                parameters = list(inspect.signature(provider.transcribe).parameters)
                self.assertEqual(parameters, ["self", "audio_path", "language", "expected_speakers", "progress_cb"])

    def test_openai_provider_refuses_an_empty_key_before_any_work(self) -> None:
        provider = OpenAIDiarizeProvider("", tempfile.gettempdir())
        with self.assertRaises(ProviderError): provider.transcribe("oricare.m4a", "ro", 0)
        self.assertEqual(provider.chunks, [])


# Setul EXACT de chei scris de versiunile anterioare, înainte de `words` / `confidence`.
OLD_SEGMENT = {"chunk_index": 2, "chunk_start_offset": 100.0, "original_speaker": "A",
               "speaker_id": "Fragment 02 · Speaker A", "local_start": 3.5, "local_end": 8.0,
               "absolute_start": 103.5, "absolute_end": 108.0, "original_text": "Text vechi",
               "corrected_text": None, "in_overlap": True, "final_speaker": "Moderator"}

NEW_SEGMENT = {**{key: value for key, value in OLD_SEGMENT.items()},
               "chunk_index": 0, "chunk_start_offset": 0.0, "original_speaker": "0", "speaker_id": "Speaker 1",
               "local_start": 0.5, "local_end": 3.2, "absolute_start": 0.5, "absolute_end": 3.2,
               "original_text": "Text nou", "in_overlap": False, "final_speaker": "Maria",
               "confidence": 0.94,
               "words": [{"start": 0.5, "end": 0.9, "text": "Bună", "confidence": 0.97},
                         {"start": 0.9, "end": 3.2, "text": "ziua.", "confidence": 0.95}]}


class ProjectCompatibilityTests(unittest.TestCase):
    def test_old_segment_without_words_still_loads(self) -> None:
        item = TranscriptSegment.from_dict(OLD_SEGMENT)
        self.assertEqual(item.original_text, "Text vechi")
        self.assertEqual(item.speaker_id, "Fragment 02 · Speaker A")
        self.assertEqual(item.absolute_start, 103.5)
        self.assertTrue(item.in_overlap)
        self.assertEqual(item.words, [])
        self.assertIsNone(item.confidence)

    def test_new_segment_with_words_loads_and_rebuilds_word_objects(self) -> None:
        item = TranscriptSegment.from_dict(NEW_SEGMENT)
        self.assertEqual(item.speaker_id, "Speaker 1")
        self.assertAlmostEqual(item.confidence or 0, 0.94)
        self.assertEqual(len(item.words), 2)
        self.assertIsInstance(item.words[0], Word)
        self.assertEqual(item.words[0].text, "Bună")

    def test_round_trip_preserves_words(self) -> None:
        restored = TranscriptSegment.from_dict(TranscriptSegment.from_dict(NEW_SEGMENT).to_dict("Maria"))
        self.assertEqual([word.text for word in restored.words], ["Bună", "ziua."])
        self.assertAlmostEqual(restored.confidence or 0, 0.94)

    def test_unknown_keys_are_ignored_and_missing_ones_defaulted(self) -> None:
        item = TranscriptSegment.from_dict({"original_text": "Doar textul", "camp_din_viitor": {"a": 1},
                                            "sentiment": "neutru"})
        self.assertEqual(item.original_text, "Doar textul")
        self.assertEqual(item.speaker_id, "")
        self.assertEqual(item.absolute_start, 0.0)

    def test_audio_chunk_tolerates_unknown_and_missing_keys(self) -> None:
        chunk = AudioChunk.from_dict({"index": 3, "start": 12.5, "duration": 60.0, "size_bytes": 10,
                                      "method": "copiere flux", "codec_viitor": "opus"})
        self.assertEqual(chunk.index, 3)
        self.assertEqual(chunk.path, "")
        self.assertEqual(chunk.overlap_seconds, 0.0)

    def test_word_tolerates_unknown_and_missing_keys(self) -> None:
        word = Word.from_dict({"text": "cuvânt", "speaker": 2, "language": "ro"})
        self.assertEqual(word.text, "cuvânt")
        self.assertEqual(word.start, 0.0)
        self.assertIsNone(word.confidence)


if __name__ == "__main__": unittest.main()
