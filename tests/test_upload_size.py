"""A long interview must be made small enough to upload in one reliable request.

Sending hundreds of megabytes in a single request stalls on an ordinary connection. These
tests pin the decision to compress, the encoding profile, retry-not-restart behaviour, and
the rule that only one percentage is ever reported for an upload.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import URLError

import strings as s
from app_controller import AppController
from app_state import AppState
from audio_processing import compress_command, should_compress
from models import AudioInfo
from providers import DeepgramProvider, GladiaProvider, OpenAIDiarizeProvider, SonioxProvider
from providers.http import UPLOAD_TIMEOUT, UploadReader, upload_file
from utils import human_size

MEGABYTE = 1024 * 1024


def recording(size_mb: float, name: str = "interview.m4a") -> AudioInfo:
    return AudioInfo(rf"C:\research\{name}", name, int(size_mb * MEGABYTE), 7837.5, "aac", 48000, 2, 148000)


class CompressionDecisionTests(unittest.TestCase):
    def test_only_large_recordings_are_re_encoded(self) -> None:
        threshold = AppState().settings.upload_compress_above_mb
        self.assertEqual(threshold, 64.0)
        # A three-minute clip uploads fine as-is; a two-hour interview does not.
        self.assertFalse(should_compress(int(6 * MEGABYTE), threshold))
        self.assertFalse(should_compress(int(64 * MEGABYTE), threshold))
        self.assertTrue(should_compress(int(65 * MEGABYTE), threshold))
        self.assertTrue(should_compress(int(1400 * MEGABYTE), threshold))

    def test_a_threshold_of_zero_disables_compression(self) -> None:
        self.assertFalse(should_compress(int(900 * MEGABYTE), 0))

    def test_the_encoding_profile_is_speech_sized(self) -> None:
        command = compress_command("ffmpeg.exe", Path("in.wav"), Path("out.m4a"), 32)
        self.assertEqual(command[command.index("-ac") + 1], "1")           # mono
        self.assertEqual(command[command.index("-ar") + 1], "16000")       # 16 kHz
        self.assertEqual(command[command.index("-b:a") + 1], "32k")
        self.assertEqual(command[command.index("-c:a") + 1], "aac")
        self.assertIn("-vn", command)
        self.assertEqual(command[-1], "out.m4a")
        self.assertNotIn("-ss", command)   # the whole file: the range cut is a separate step

    def test_the_default_bitrate_makes_a_two_hour_interview_uploadable(self) -> None:
        settings = AppState().settings
        seconds = 7837.5
        predicted_mb = settings.upload_bitrate_kbps * 1000 * seconds / 8 / MEGABYTE
        self.assertLess(predicted_mb, 40, f"a 2h interview would still be {predicted_mb:.0f} MB")


class PrepareSourceTests(unittest.TestCase):
    """`prepare_source` decides what actually gets uploaded."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="prepare_")
        self.folder = self._temp.name
        self.addCleanup(self._temp.cleanup)
        self.controller = AppController()
        self.messages: list[str] = []

    def update(self, message: str, fraction: float | None) -> None:
        self.messages.append(message)

    def test_a_large_file_is_compressed_before_upload(self) -> None:
        large = recording(320)
        compact = recording(28, "upload_interview.m4a")
        with mock.patch("app_controller.compress_for_upload", return_value=compact) as compress:
            path, offset = self.controller.prepare_source(large, self.folder, self.update, True)
        compress.assert_called_once()
        self.assertEqual(path, compact.path)
        self.assertEqual(offset, 0.0)
        self.assertTrue(any(m.startswith("Preparing a compact copy") for m in self.messages))
        self.assertTrue(any("reduced to" in m for m in self.messages))

    def test_a_small_file_is_uploaded_untouched(self) -> None:
        small = recording(6)
        with mock.patch("app_controller.compress_for_upload") as compress:
            path, _ = self.controller.prepare_source(small, self.folder, self.update, True)
        compress.assert_not_called()
        self.assertEqual(path, small.path)
        self.assertEqual(self.messages, [])

    def test_the_fragmenting_provider_is_never_pre_compressed(self) -> None:
        """OpenAI splits and re-encodes locally; compressing first would just cost time."""
        large = recording(320)
        with mock.patch("app_controller.compress_for_upload") as compress:
            path, _ = self.controller.prepare_source(large, self.folder, self.update, False)
        compress.assert_not_called()
        self.assertEqual(path, large.path)

    def test_a_range_is_cut_first_and_the_clip_is_compressed_if_still_large(self) -> None:
        large = recording(320)
        self.controller.state.selected_file_metadata = large
        self.controller.set_range(720.0, 4320.0)
        clip = recording(160, "range_clip.m4a")
        compact = recording(14, "upload_range_clip.m4a")
        with mock.patch("app_controller.extract_range", return_value=clip) as cut, \
             mock.patch("app_controller.compress_for_upload", return_value=compact) as compress:
            path, offset = self.controller.prepare_source(large, self.folder, self.update, True)
        cut.assert_called_once()
        compress.assert_called_once()
        # Compression runs on the clip, not the original.
        self.assertEqual(compress.call_args[0][0], clip)
        self.assertEqual(path, compact.path)
        self.assertEqual(offset, 720.0, "timestamps stay anchored to the original recording")

    def test_which_providers_upload_the_whole_file(self) -> None:
        for provider in (GladiaProvider, SonioxProvider, DeepgramProvider):
            self.assertTrue(provider.info.uploads_whole_file, provider.info.key)
        self.assertFalse(OpenAIDiarizeProvider.info.uploads_whole_file)


class UploadTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="upload_")
        self.audio = Path(self._temp.name) / "compact.m4a"
        self.audio.write_bytes(b"0" * 300_000)
        self.addCleanup(self._temp.cleanup)

    def test_a_failed_upload_is_retried_from_a_fresh_reader_not_a_consumed_one(self) -> None:
        attempts: list[int] = []
        events: list[tuple[str, float | None]] = []

        class _Response:
            def read(self) -> bytes: return b'{"audio_url":"https://gladia/a.m4a"}'
            def __enter__(self): return self
            def __exit__(self, *exc): return False

        def handler(request, timeout=None):
            attempts.append(1)
            body = request.data
            consumed = 0
            while True:
                block = body.read(8192)
                if not block: break
                consumed += len(block)
            if len(attempts) == 1:
                raise URLError("connection reset by peer")
            # The retry must have sent the whole body again, not zero bytes from a spent handle.
            self.assertGreater(consumed, 300_000)
            return _Response()

        with mock.patch("providers.http.urlopen", handler):
            payload = upload_file("Gladia", "https://api.gladia.io/v2/upload", {}, self.audio, "audio",
                                  None, lambda m, f: events.append((m, f)), None,
                                  "Uploading the recording to Gladia", .55, "done",
                                  attempts=3, sleeper=lambda _: None)
        self.assertEqual(payload["audio_url"], "https://gladia/a.m4a")
        self.assertEqual(len(attempts), 2, "the upload retried once")
        # Progress restarts from zero on the retry rather than continuing from a stale count.
        opening = f"Uploading the recording to Gladia: {human_size(0)} of {human_size(300_000)}."
        self.assertEqual(len([m for m, _ in events if m == opening]), 2)
        self.assertFalse([m for m, _ in events if "%" in m], "no message may carry a percentage")

    def test_the_upload_reports_bytes_and_the_bar_owns_the_only_percentage(self) -> None:
        events: list[tuple[str, float | None]] = []
        with self.audio.open("rb") as handle:
            reader = UploadReader(handle, 300_000, lambda m, f: events.append((m, f)), None,
                                  b"", b"", "Uploading the recording to Gladia", .55, "processing")
            while reader.read(8192): pass
        messages = [m for m, _ in events]
        # No message may carry a percentage: the card showed 45% and 24% at once before this.
        self.assertFalse([m for m in messages if "%" in m], messages[:3])
        self.assertTrue(any(f"of {human_size(300_000)}" in m for m in messages))
        fractions = [f for _, f in events if f is not None]
        self.assertEqual(fractions, sorted(fractions))
        self.assertLessEqual(max(fractions), .55 + 1e-9, "upload occupies only its share of the bar")

    def test_a_stalled_socket_fails_fast_instead_of_hanging(self) -> None:
        # Per socket operation, so a healthy slow upload is unaffected but a dead one is caught.
        self.assertEqual(UPLOAD_TIMEOUT, 120)

    def test_the_upload_is_cancellable_mid_stream(self) -> None:
        sent: list[int] = []
        cancelled = lambda: len(sent) > 3
        with self.audio.open("rb") as handle:
            reader = UploadReader(handle, 300_000, None, cancelled, b"", b"", "Uploading", 1.0, "")
            with self.assertRaises(Exception) as caught:
                while True:
                    block = reader.read(8192)
                    if not block: break
                    sent.append(len(block))
        self.assertIn("cancelled", str(caught.exception).lower())
        self.assertLess(sum(sent), 300_000, "cancelling stopped the upload part way through")


if __name__ == "__main__": unittest.main()
