"""A two-hour recording must survive a long wait and a dropped packet.

The failure this guards against: one blocking request held open for the whole upload and
processing, and any network blip during the wait killing the job outright.
"""
from __future__ import annotations

import email.message
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from providers.base import ProviderError, format_elapsed
from providers.gladia import GladiaProvider
from providers.http import TRANSIENT_STATUS, with_retry
from providers.soniox import SonioxProvider

GLADIA_DONE = {"status": "done", "result": {"transcription": {"utterances": [
    {"speaker": 0, "start": 0.5, "end": 3.2, "confidence": .94, "text": "Bună ziua tuturor.",
     "words": [{"word": "Bună", "start": 0.5, "end": 0.9, "confidence": .97},
               {"word": "ziua", "start": 0.9, "end": 3.2, "confidence": .95}]},
    {"speaker": 1, "start": 8.0, "end": 11.0, "confidence": .88, "text": "Mulțumim.", "words": []},
    {"speaker": 0, "start": 7200.0, "end": 7205.0, "confidence": .9, "text": "Închidem.", "words": []}]}}}

SONIOX_DONE = {"tokens": [
    {"text": "Bună", "start_ms": 500, "end_ms": 900, "confidence": .97, "speaker": 0},
    {"text": "ziua.", "start_ms": 900, "end_ms": 1400, "confidence": .93, "speaker": 0},
    {"text": "Mulțumim.", "start_ms": 8000, "end_ms": 9000, "confidence": .89, "speaker": 1}]}


class _Response:
    def __init__(self, payload) -> None:
        self._body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.status = 200

    def read(self) -> bytes: return self._body
    def __enter__(self) -> "_Response": return self
    def __exit__(self, *exc: object) -> bool: return False


def _drain(request) -> None:
    body = getattr(request, "data", None)
    if hasattr(body, "read"):
        while body.read(8192): pass


def _http_error(code: int) -> HTTPError:
    return HTTPError("https://api.gladia.io", code, "busy", email.message.Message(),
                     io.BytesIO(b'{"message":"busy"}'))


class _Clock:
    """A clock the test drives, so a three-hour job takes no real time."""

    def __init__(self) -> None: self.now = 0.0
    def __call__(self) -> float: return self.now
    def sleep(self, seconds: float) -> None: self.now += seconds


class LongGladiaJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="long_job_")
        self.audio = Path(self._temp.name) / "interview_2h.m4a"
        self.audio.write_bytes(b"0" * 200_000)
        self.addCleanup(self._temp.cleanup)
        self.clock = _Clock()

    def provider(self) -> GladiaProvider:
        return GladiaProvider("gl-key", poll_interval=5.0, poll_attempts=100, retry_attempts=4,
                              sleeper=self.clock.sleep, clock=self.clock)

    def run_job(self, script: list, expected_speakers: int = 5):
        """`script` is consumed one entry per request: a payload, or an exception to raise."""
        calls: list[str] = []
        events: list[tuple[str, float | None]] = []
        remaining = list(script)

        def handler(request, timeout=None):
            _drain(request)
            calls.append(request.full_url)
            step = remaining.pop(0)
            if isinstance(step, Exception): raise step
            return _Response(step)

        with mock.patch("providers.http.urlopen", handler):
            segments = self.provider().transcribe(str(self.audio), "ro", expected_speakers,
                                                  lambda message, fraction: events.append((message, fraction)))
        return segments, calls, events

    def test_a_long_job_survives_many_polls_and_a_dropped_connection(self) -> None:
        script = [
            {"audio_url": "https://gladia/audio.m4a"},          # upload
            {"result_url": "https://api.gladia.io/v2/result/job-1"},  # job created
            {"status": "queued"},                                # poll 1
            {"status": "processing"},                            # poll 2
            URLError("connection reset by peer"),                # poll 3 drops
            {"status": "processing"},                            # poll 3 retried, same job
            {"status": "processing"},                            # poll 4
            GLADIA_DONE,                                         # poll 5 finishes
        ]
        segments, calls, events = self.run_job(script)

        # The job completed despite the drop.
        self.assertEqual(len(segments), 3)
        self.assertEqual(len(calls), len(script))
        # Every poll after the drop went to the SAME job, never restarting the work.
        polls = [url for url in calls if "/result/job-1" in url]
        self.assertEqual(len(polls), 6)
        self.assertEqual(len(set(polls)), 1)
        # No upload was repeated: exactly one call to /upload.
        self.assertEqual(len([url for url in calls if "/upload" in url]), 1)

    def test_the_transcript_keeps_speakers_words_and_confidence(self) -> None:
        script = [{"audio_url": "u"}, {"result_url": "https://api.gladia.io/v2/result/job-1"},
                  URLError("timed out"), {"status": "processing"}, GLADIA_DONE]
        segments, _, _ = self.run_job(script)
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1", "Speaker 2"})
        self.assertEqual(segments[0].speaker_id, segments[-1].speaker_id)   # global, two hours apart
        self.assertEqual([word.text for word in segments[0].words], ["Bună", "ziua"])
        self.assertAlmostEqual(segments[0].confidence or 0, .94)
        self.assertEqual(segments[-1].absolute_start, 7200.0)

    def test_the_wait_reports_elapsed_time_so_it_never_looks_frozen(self) -> None:
        script = [{"audio_url": "u"}, {"result_url": "https://api.gladia.io/v2/result/job-1"},
                  {"status": "processing"}, {"status": "processing"}, {"status": "processing"}, GLADIA_DONE]
        _, _, events = self.run_job(script)
        messages = [message for message, _ in events]
        self.assertTrue(any("Uploading the recording to Gladia" in m for m in messages))
        elapsed = [m for m in messages if m.startswith("Processing on Gladia — elapsed")]
        self.assertGreaterEqual(len(elapsed), 3)
        # The clock advances between polls, so the reported time actually moves.
        self.assertNotEqual(elapsed[0], elapsed[-1])
        # The first tick lands before any wait, so it honestly reads zero; the next is 5s later.
        self.assertIn("00:00", elapsed[0])
        self.assertIn("00:05", elapsed[1])
        fractions = [f for _, f in events if f is not None]
        self.assertEqual(fractions, sorted(fractions))

    def test_a_retry_tells_the_user_what_happened(self) -> None:
        script = [{"audio_url": "u"}, {"result_url": "https://api.gladia.io/v2/result/job-1"},
                  URLError("connection reset by peer"), GLADIA_DONE]
        _, _, events = self.run_job(script)
        notices = [m for m, _ in events if m.startswith("Connection problem")]
        self.assertEqual(len(notices), 1)
        self.assertIn("Retrying in", notices[0])

    def test_a_gateway_error_is_retried_but_a_bad_key_is_not(self) -> None:
        script = [{"audio_url": "u"}, {"result_url": "https://api.gladia.io/v2/result/job-1"},
                  _http_error(503), GLADIA_DONE]
        segments, _, _ = self.run_job(script)
        self.assertEqual(len(segments), 3)

        with mock.patch("providers.http.urlopen", side_effect=_http_error(401)):
            with self.assertRaises(ProviderError) as caught:
                self.provider().transcribe(str(self.audio), "ro", 0)
        self.assertIn("invalid", str(caught.exception).lower())

    def test_giving_up_only_after_the_retry_budget_is_spent(self) -> None:
        script = [{"audio_url": "u"}, {"result_url": "https://api.gladia.io/v2/result/job-1"}]
        script += [URLError("down")] * 4          # retry_attempts=4, so the fourth is fatal
        with self.assertRaises(ProviderError) as caught:
            self.run_job(script)
        self.assertIn("Could not connect", str(caught.exception))


class LongSonioxJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="long_soniox_")
        self.audio = Path(self._temp.name) / "interview_2h.m4a"
        self.audio.write_bytes(b"0" * 120_000)
        self.addCleanup(self._temp.cleanup)
        self.clock = _Clock()

    def test_a_long_soniox_job_survives_a_dropped_poll(self) -> None:
        script = [{"id": "file-1"}, {"id": "tr-1"}, {"status": "processing"},
                  URLError("connection reset"), {"status": "processing"},
                  {"status": "completed"}, SONIOX_DONE]
        remaining = list(script)
        events: list[tuple[str, float | None]] = []

        def handler(request, timeout=None):
            _drain(request)
            step = remaining.pop(0)
            if isinstance(step, Exception): raise step
            return _Response(step)

        with mock.patch("providers.http.urlopen", handler):
            provider = SonioxProvider("sx-key", poll_interval=5.0, poll_attempts=50, retry_attempts=4,
                                      sleeper=self.clock.sleep, clock=self.clock)
            segments = provider.transcribe(str(self.audio), "ro", 5,
                                           lambda message, fraction: events.append((message, fraction)))
        self.assertEqual(len(segments), 2)
        self.assertEqual({item.speaker_id for item in segments}, {"Speaker 1", "Speaker 2"})
        self.assertTrue(any(m.startswith("Processing on Soniox — elapsed") for m, _ in events))


class RetryPolicyTests(unittest.TestCase):
    def test_transient_errors_are_retried_and_permanent_ones_are_not(self) -> None:
        attempts: list[int] = []

        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3: raise ProviderError("blip", transient=True)
            return "done"

        self.assertEqual(with_retry(flaky, attempts=5, sleeper=lambda _: None), "done")
        self.assertEqual(len(attempts), 3)

        permanent: list[int] = []

        def bad_key() -> str:
            permanent.append(1)
            raise ProviderError("invalid key", transient=False)

        with self.assertRaises(ProviderError):
            with_retry(bad_key, attempts=5, sleeper=lambda _: None)
        self.assertEqual(len(permanent), 1, "a permanent failure must not be retried")

    def test_backoff_grows_and_is_capped(self) -> None:
        delays: list[float] = []

        def always_fails() -> None:
            raise ProviderError("blip", transient=True)

        with self.assertRaises(ProviderError):
            with_retry(always_fails, attempts=6, sleeper=delays.append)
        self.assertEqual(delays, sorted(delays))
        self.assertEqual(delays[0], 2.0)
        self.assertLessEqual(max(delays), 30.0)

    def test_the_status_codes_treated_as_transient(self) -> None:
        self.assertIn(503, TRANSIENT_STATUS)
        self.assertIn(429, TRANSIENT_STATUS)
        self.assertNotIn(401, TRANSIENT_STATUS)
        self.assertNotIn(404, TRANSIENT_STATUS)

    def test_elapsed_formatting(self) -> None:
        self.assertEqual(format_elapsed(5), "00:05")
        self.assertEqual(format_elapsed(95), "01:35")
        self.assertEqual(format_elapsed(3725), "1:02:05")


if __name__ == "__main__": unittest.main()
