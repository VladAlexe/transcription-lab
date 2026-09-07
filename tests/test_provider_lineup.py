"""Tests for the provider lineup, the capability model and the generic endpoint.

Every HTTP request is simulated through `providers.http.urlopen`; no real API is ever called.
"""
from __future__ import annotations

import email.message
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from app_state import KEY_FIELDS, AppState
from providers import DEFAULT_PROVIDER, PROVIDERS, feature_state, provider_capabilities, provider_info
from providers.base import ProviderCapabilities, ProviderError, TranscriptionProvider
from providers.gladia import GladiaProvider, diarization_config, request_payload as gladia_payload
from providers.openai_compatible import OpenAICompatibleProvider, endpoint, parse_response as compatible_parse
from providers.soniox import SonioxProvider, parse_transcript

GLADIA_RESULT = {"status": "done", "result": {"transcription": {"utterances": [
    {"speaker": 0, "start": 0.5, "end": 3.2, "confidence": 0.94, "text": "Bună ziua tuturor.",
     "words": [{"word": "Bună", "start": 0.5, "end": 0.9, "confidence": 0.97},
               {"word": "ziua", "start": 0.9, "end": 3.2, "confidence": 0.95}]},
    {"speaker": 1, "start": 3.4, "end": 6.0, "confidence": 0.88, "text": "Mulțumim pentru invitație.", "words": []},
    {"speaker": 0, "start": 7200.0, "end": 7205.0, "confidence": 0.9, "text": "Închidem discuția.", "words": []}]}}}

SONIOX_TRANSCRIPT = {"tokens": [
    {"text": "Bună", "start_ms": 500, "end_ms": 900, "confidence": 0.97, "speaker": 0},
    {"text": "ziua.", "start_ms": 900, "end_ms": 1400, "confidence": 0.93, "speaker": 0},
    {"text": "Mulțumim.", "start_ms": 3400, "end_ms": 4100, "confidence": 0.89, "speaker": 1},
    {"text": "Închidem.", "start_ms": 7200000, "end_ms": 7201000, "confidence": 0.91, "speaker": 0}]}

VERBOSE_JSON = {"task": "transcribe", "language": "ro", "duration": 12.5, "text": "Bună ziua. Mulțumim.",
                "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": " Bună ziua."},
                             {"id": 1, "start": 4.0, "end": 8.5, "text": " Mulțumim."}]}

# What a server sends when it was asked for word granularity: the same shape, plus words.
WORD_JSON = {"task": "transcribe", "language": "ro", "duration": 5.0, "text": "Bună ziua.",
             "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": " Bună ziua.",
                           "words": [{"word": "Bună", "start": 0.0, "end": 0.6},
                                     {"word": "ziua", "start": 0.6, "end": 1.1}]}]}

TEXT_ONLY = {"text": "Primul paragraf al discuției.\n\nAl doilea paragraf, alt subiect.\n\nUltimul paragraf."}


class _FakeResponse:
    def __init__(self, payload) -> None:
        self._body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.status = 200

    def read(self) -> bytes: return self._body
    def __enter__(self) -> "_FakeResponse": return self
    def __exit__(self, *exc: object) -> bool: return False


def _drain(request: object) -> None:
    body = getattr(request, "data", None)
    if hasattr(body, "read"):
        while body.read(8192): pass


def _router(routes: list[tuple[str, object]], calls: list[dict]):
    """Answers in the order the routes were declared, matching on fragments of the URL."""
    def handler(request, timeout=None):
        _drain(request)
        calls.append({"url": request.full_url, "method": request.method,
                      "headers": {key.lower(): value for key, value in request.headers.items()}})
        for fragment, payload in routes:
            if fragment in request.full_url:
                if isinstance(payload, Exception): raise payload
                return _FakeResponse(payload)
        raise AssertionError(f"URL neasteptat: {request.full_url}")
    return handler


def _init_no_sleep(provider, api_key, cancelled=None, *args, **kwargs) -> None:
    """A Gladia provider that polls instantly, so the tests never wait."""
    provider.api_key = api_key; provider.cancelled = cancelled
    provider.poll_interval = 0; provider.poll_attempts = 5
    provider.retry_attempts = 2
    provider.sleeper = lambda _: None
    provider.clock = lambda: 0.0


def _http_error(code: int, message: str = "eroare") -> HTTPError:
    body = io.BytesIO(json.dumps({"message": message}).encode("utf-8"))
    return HTTPError("https://exemplu.ro", code, message, email.message.Message(), body)


class _AudioCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="lineup_test_")
        self.audio = Path(self._temp.name) / "interviu.m4a"
        self.audio.write_bytes(b"0" * 30_000)
        self.addCleanup(self._temp.cleanup)


class CapabilityTests(unittest.TestCase):
    def test_gladia_is_the_default_and_fully_capable(self) -> None:
        self.assertEqual(DEFAULT_PROVIDER, "gladia")
        caps = provider_capabilities("gladia")
        self.assertTrue(caps.supports_diarization and caps.supports_word_timestamps)
        self.assertTrue(caps.supports_confidence and caps.global_speakers)
        self.assertIn("Full", caps.summary())

    def test_every_provider_declares_a_capability_set(self) -> None:
        for key, provider in PROVIDERS.items():
            with self.subTest(provider=key):
                self.assertIsInstance(provider.info.capabilities, ProviderCapabilities)
                self.assertTrue(issubclass(provider, TranscriptionProvider))

    def test_flags_drive_feature_enablement(self) -> None:
        full = feature_state(provider_capabilities("gladia"))
        self.assertTrue(full["speaker_naming"] and full["word_timestamps"] and full["confidence_display"])
        self.assertFalse(full["speaker_reconciliation"] or full["manual_speaker_split"])

        fragmented = feature_state(provider_capabilities("openai"))
        self.assertTrue(fragmented["speaker_naming"] and fragmented["speaker_reconciliation"])
        self.assertFalse(fragmented["word_timestamps"] or fragmented["confidence_display"])
        self.assertFalse(fragmented["manual_speaker_split"])

        generic = feature_state(provider_capabilities("compatible"))
        self.assertFalse(generic["speaker_naming"] or generic["speaker_reconciliation"])
        self.assertFalse(generic["confidence_display"])
        self.assertTrue(generic["manual_speaker_split"])

    def test_summaries_are_honest_per_provider(self) -> None:
        self.assertIn("no speaker labels", provider_capabilities("compatible").summary())
        self.assertIn("per fragment", provider_capabilities("openai").summary())
        self.assertIn("global speakers", provider_capabilities("deepgram").summary())

    def test_state_capabilities_follow_the_selected_provider(self) -> None:
        state = AppState()
        self.assertTrue(state.effective_capabilities.global_speakers)
        state.settings.provider = "compatible"
        self.assertFalse(state.effective_capabilities.supports_diarization)
        # What a run actually delivered takes precedence over what was declared.
        state.run_capabilities = ProviderCapabilities(supports_diarization=False, supports_word_timestamps=False)
        self.assertFalse(state.effective_capabilities.supports_word_timestamps)

    def test_each_provider_has_its_own_key_field(self) -> None:
        state = AppState()
        self.assertEqual(sorted(KEY_FIELDS), sorted(PROVIDERS))
        for key in PROVIDERS:
            state.settings.provider = key
            state.set_active_api_key(f"cheie-{key}")
        for key in PROVIDERS:
            state.settings.provider = key
            self.assertEqual(state.active_api_key, f"cheie-{key}")


class GladiaTests(_AudioCase):
    def run_provider(self, expected_speakers: int = 5):
        calls: list[dict] = []
        # Routes match in order: the result route has to come before the initial request.
        routes = [("/upload", {"audio_url": "https://gladia/audio.m4a"}),
                  ("/result/abc", GLADIA_RESULT),
                  ("/pre-recorded", {"id": "abc", "result_url": "https://api.gladia.io/v2/result/abc"})]
        with mock.patch("providers.http.urlopen", _router(routes, calls)):
            provider = GladiaProvider("gl-key", poll_interval=0)
            segments = provider.transcribe(str(self.audio), "ro", expected_speakers)
        return segments, calls

    def test_speaker_count_is_bound_for_real(self) -> None:
        self.assertEqual(diarization_config(5),
                         {"number_of_speakers": 5, "min_speakers": 5, "max_speakers": 5})
        self.assertEqual(diarization_config(0), {})
        payload = gladia_payload("https://x/a.m4a", "ro", 5)
        self.assertTrue(payload["diarization"])
        self.assertEqual(payload["language"], "ro")
        self.assertEqual(payload["diarization_config"]["min_speakers"], 5)

    def test_global_speakers_words_and_confidence(self) -> None:
        segments, _ = self.run_provider()
        self.assertEqual(len(segments), 3)
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1", "Speaker 2"})
        self.assertEqual(segments[0].speaker_id, segments[-1].speaker_id)
        self.assertAlmostEqual(segments[0].confidence or 0, 0.94)
        self.assertEqual([word.text for word in segments[0].words], ["Bună", "ziua"])
        self.assertEqual(segments[-1].absolute_start, 7200.0)

    def test_upload_request_and_poll_are_authenticated(self) -> None:
        _, calls = self.run_provider()
        self.assertEqual(len(calls), 3)
        for call in calls: self.assertEqual(call["headers"].get("X-gladia-key".lower()), "gl-key")
        self.assertIn("/upload", calls[0]["url"])
        self.assertEqual(calls[1]["method"], "POST")

    def test_no_hint_when_count_is_unset(self) -> None:
        self.assertNotIn("diarization_config", gladia_payload("https://x/a.m4a", "ro", 0))

    def test_processing_error_is_reported(self) -> None:
        routes = [("/upload", {"audio_url": "u"}), ("/rezultat", {"status": "error", "error_code": 42}),
                  ("/pre-recorded", {"result_url": "https://g/rezultat"})]
        with mock.patch("providers.http.urlopen", _router(routes, [])):
            with self.assertRaises(ProviderError):
                GladiaProvider("k", poll_interval=0).transcribe(str(self.audio), "ro", 0)


class SonioxTests(_AudioCase):
    def test_tokens_are_grouped_into_global_speaker_turns(self) -> None:
        segments = parse_transcript(SONIOX_TRANSCRIPT)
        self.assertEqual([item.speaker_id for item in segments], ["Speaker 1", "Speaker 2", "Speaker 1"])
        self.assertEqual(segments[0].original_text, "Bună ziua.")
        self.assertAlmostEqual(segments[0].absolute_start, 0.5)
        self.assertAlmostEqual(segments[0].confidence or 0, 0.95)
        self.assertEqual(len(segments[0].words), 2)
        self.assertAlmostEqual(segments[-1].absolute_start, 7200.0)

    def test_full_flow_uploads_requests_polls_and_downloads(self) -> None:
        calls: list[dict] = []
        routes = [("/files", {"id": "file-1"}), ("/transcriptions/tr-1/transcript", SONIOX_TRANSCRIPT),
                  ("/transcriptions/tr-1", {"status": "completed"}), ("/transcriptions", {"id": "tr-1"})]
        with mock.patch("providers.http.urlopen", _router(routes, calls)):
            segments = SonioxProvider("sx-key", poll_interval=0).transcribe(str(self.audio), "ro", 5)
        self.assertEqual(len(segments), 3)
        self.assertEqual(len(calls), 4)
        for call in calls: self.assertEqual(call["headers"].get("authorization"), "Bearer sx-key")

    def test_empty_transcript_raises(self) -> None:
        with self.assertRaises(ProviderError): parse_transcript({"tokens": []})


class OpenAICompatibleTests(_AudioCase):
    def transcribe(self, payload, base_url: str = "https://local.ro/v1", model: str = "whisper-1"):
        calls: list[dict] = []
        with mock.patch("providers.http.urlopen", _router([("/audio/transcriptions", payload)], calls)):
            provider = OpenAICompatibleProvider("own-key", base_url, model)
            segments = provider.transcribe(str(self.audio), "ro", 5)
        return provider, segments, calls

    def test_verbose_json_segments_are_used(self) -> None:
        provider, segments, calls = self.transcribe(VERBOSE_JSON)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].original_text, "Bună ziua.")
        self.assertEqual(segments[1].absolute_start, 4.0)
        # No diarization: one default speaker for the whole transcript.
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1"})
        # `verbose_json` carries segment intervals but no words unless the server was asked
        # for word granularity. Claiming word timestamps anyway offered a "Play by word"
        # mode with nothing in it, so the capability now follows what actually arrived.
        self.assertFalse(provider.capabilities().supports_word_timestamps)
        self.assertFalse(provider.capabilities().supports_diarization)
        self.assertFalse(provider.capabilities().supports_confidence)
        self.assertIn("/audio/transcriptions", calls[0]["url"])
        self.assertEqual(calls[0]["headers"].get("authorization"), "Bearer own-key")

    def test_word_timestamps_are_claimed_when_words_actually_arrive(self) -> None:
        provider, segments, _ = self.transcribe(WORD_JSON)
        self.assertEqual([w.text for w in segments[0].words], ["Bună", "ziua"])
        self.assertTrue(provider.capabilities().supports_word_timestamps)

    def test_text_only_response_becomes_one_segment_per_paragraph(self) -> None:
        provider, segments, _ = self.transcribe(TEXT_ONLY)
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0].original_text, "Primul paragraf al discuției.")
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1"})
        self.assertEqual([item.absolute_start for item in segments], [0.0, 0.0, 0.0])
        # The capability narrows to reality: no timings came back.
        self.assertFalse(provider.capabilities().supports_word_timestamps)

    def test_plain_text_body_does_not_crash(self) -> None:
        _, segments, _ = self.transcribe(b"Doar text simplu, fara JSON.")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].original_text, "Doar text simplu, fara JSON.")

    def test_model_and_format_are_sent_as_form_fields(self) -> None:
        captured: dict[str, bytes] = {}

        def handler(request, timeout=None):
            body = request.data; chunks = []
            while True:
                block = body.read(8192)
                if not block: break
                chunks.append(block)
            captured["body"] = b"".join(chunks)
            return _FakeResponse(VERBOSE_JSON)

        with mock.patch("providers.http.urlopen", handler):
            OpenAICompatibleProvider("k", "https://local.ro/v1", "faster-whisper-large").transcribe(str(self.audio), "ro")
        body = captured["body"].decode("utf-8", "replace")
        self.assertIn("faster-whisper-large", body)
        self.assertIn("verbose_json", body)
        self.assertIn('name="language"', body)

    def test_endpoint_is_normalised_and_required(self) -> None:
        self.assertEqual(endpoint("https://x.ro/v1"), "https://x.ro/v1/audio/transcriptions")
        self.assertEqual(endpoint("https://x.ro/v1/"), "https://x.ro/v1/audio/transcriptions")
        self.assertEqual(endpoint("https://x.ro/v1/audio/transcriptions"), "https://x.ro/v1/audio/transcriptions")
        with self.assertRaises(ProviderError): endpoint("   ")

    def test_missing_endpoint_is_reported_before_upload(self) -> None:
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider("k", "", "whisper-1").transcribe(str(self.audio), "ro")

    def test_empty_response_raises(self) -> None:
        with self.assertRaises(ProviderError): compatible_parse({"text": "   "})

    def test_http_failure_is_translated(self) -> None:
        def handler(request, timeout=None):
            _drain(request); raise _http_error(404, "model necunoscut")

        with mock.patch("providers.http.urlopen", handler):
            with self.assertRaises(ProviderError) as caught:
                OpenAICompatibleProvider("k", "https://local.ro/v1", "x").transcribe(str(self.audio), "ro")
        self.assertIn("does not exist", str(caught.exception))


class ProvenanceTests(_AudioCase):
    def _run_gladia(self):
        from app_controller import AppController
        from models import AudioInfo
        routes = [("/upload", {"audio_url": "u"}), ("/rezultat", GLADIA_RESULT),
                  ("/pre-recorded", {"result_url": "https://g/rezultat"})]
        controller = AppController()
        self.addCleanup(controller.state.cleanup_temporary)
        controller.state.selected_file_metadata = AudioInfo(str(self.audio), self.audio.name,
                                                            self.audio.stat().st_size, 7837, "aac", 48000, 2, 148000)
        controller.state.gladia_api_key = "gl-key"
        # Poll instantly, so the test does not wait between attempts.
        with mock.patch("providers.http.urlopen", _router(routes, [])), \
             mock.patch.object(GladiaProvider, "__init__", _init_no_sleep):
            controller.start_transcription(lambda message, fraction: None)
        return controller

    def test_saved_project_records_the_real_provider_and_model(self) -> None:
        from document_export import project_payload
        controller = self._run_gladia()
        state = controller.state
        self.assertEqual(state.transcription_provider, "gladia")
        self.assertEqual(state.transcription_model, "gladia-v2")
        payload = project_payload(state.selected_file_metadata, state.generated_chunks, state.transcript_segments,
                                  state.speaker_mapping, state.generated_at, {}, False, 2,
                                  state.transcription_provider, state.transcription_model)
        self.assertEqual(payload["transcription_provider"], "gladia")
        self.assertEqual(payload["transcription_model"], "gladia-v2")
        self.assertNotIn("gl-key", json.dumps(payload, ensure_ascii=False))

    def test_loaded_project_describes_the_transcript_not_the_current_selection(self) -> None:
        from app_controller import AppController
        from document_export import project_payload
        legacy = project_payload(None, [], [], {}, "2026-07-19T15:11:45+03:00")  # no provider, as in the older files
        path = Path(self._temp.name) / "vechi.transcript.json"
        path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")

        controller = AppController()
        controller.state.settings.provider = "gladia"  # furnizor global selectat acum
        controller.load_project(str(path))
        # The transcript came from the fragmented OpenAI path, so the interface must not
        # promise global speakers.
        self.assertEqual(controller.state.transcription_provider, "openai")
        self.assertFalse(controller.state.effective_capabilities.global_speakers)
        self.assertTrue(feature_state(controller.state.effective_capabilities)["speaker_reconciliation"])

    def test_payload_defaults_stay_backwards_compatible(self) -> None:
        from document_export import MODEL, project_payload
        payload = project_payload(None, [], [], {}, "date")
        self.assertEqual(payload["transcription_model"], MODEL)
        self.assertEqual(payload["transcription_provider"], "openai")

    def test_generic_endpoint_credentials_never_reach_preferences_or_export(self) -> None:
        from document_export import project_payload
        state = AppState()
        state.settings.provider = "compatible"
        state.compatible_api_key = "secret-key"; state.compatible_base_url = "https://intern.ro/v1"
        state.compatible_model = "whisper-mare"
        payload = project_payload(None, [], [], {}, "date", {}, False, 0, "compatible", state.compatible_model)
        raw = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("secret-key", raw)
        self.assertNotIn("intern.ro", raw)
        self.assertNotIn("compatible_api_key", repr(state))


if __name__ == "__main__": unittest.main()


class DetectLanguageTests(unittest.TestCase):
    """Settings offers "Detect automatically". It is not a language code, and every one of
    these APIs rejects it as one, so each provider has to say detection in its own words."""

    def test_a_named_language_reaches_gladia_exactly_as_before(self) -> None:
        """The path already in use must not move because the auto path was fixed."""
        from providers.gladia import request_payload
        self.assertEqual(request_payload("url", "ro"),
                         {"audio_url": "url", "diarization": True, "language": "ro",
                          "detect_language": False})

    def test_gladia_asks_for_detection_instead_of_sending_the_word_auto(self) -> None:
        from providers.gladia import request_payload
        payload = request_payload("url", "auto")
        self.assertTrue(payload["detect_language"])
        self.assertNotIn("language", payload)

    def test_deepgram_uses_its_own_detection_flag(self) -> None:
        from providers.deepgram import request_params
        params = request_params("auto")
        self.assertEqual(params.get("detect_language"), "true")
        self.assertNotIn("language", params)

    def test_soniox_is_given_no_hint_at_all(self) -> None:
        from providers.soniox import request_payload
        self.assertNotIn("language_hints", request_payload("file-1", "auto"))
        self.assertEqual(request_payload("file-1", "ro")["language_hints"], ["ro"])

    def test_an_empty_language_still_falls_back_to_the_default(self) -> None:
        from providers.gladia import request_payload
        self.assertEqual(request_payload("url", "")["language"], "ro")
