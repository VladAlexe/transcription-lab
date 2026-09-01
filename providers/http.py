"""Utilitare HTTP comune furnizorilor: încărcare în flux și cereri JSON.

Se folosește exclusiv biblioteca standard, ca aplicația să nu capete dependențe noi.
Testele înlocuiesc `providers.http.urlopen` pentru a simula răspunsurile serverelor.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, BinaryIO, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from providers.base import CancelCallback, ProgressCallback, ProviderError, emit_progress
from utils import human_size

BOUNDARY = "----transcriere-interviuri-boundary"
UPLOAD_STEPS = 20
REQUEST_TIMEOUT = 900
# A two-hour recording is a large upload; a poll is a few hundred bytes. They need very
# different patience, and a short poll timeout is what keeps a hung socket from stalling a job.
# Per socket operation, not per transfer: a healthy upload keeps resetting it, while a
# genuinely stalled socket raises within two minutes instead of hanging for half an hour.
UPLOAD_TIMEOUT = 120
POLL_TIMEOUT = 60
JOB_TIMEOUT = 120
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 2.0
RETRY_MAX_DELAY = 30.0
# Statuses worth trying again: overload, throttling, gateway trouble. Everything else in the
# 4xx range is our mistake and will fail identically on a retry.
TRANSIENT_STATUS = {408, 425, 429, 500, 502, 503, 504}

_CONTENT_TYPES = {".m4a": "audio/mp4", ".mp4": "audio/mp4", ".aac": "audio/aac", ".mp3": "audio/mpeg",
                  ".wav": "audio/wav", ".flac": "audio/flac", ".webm": "audio/webm"}


def content_type(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


class UploadReader:
    """Trimite fișierul către socket fără a-l încărca în memorie și raportează progresul.

    Poate încadra conținutul între un antet și un subsol (folosite pentru multipart/form-data).
    """

    def __init__(self, handle: BinaryIO, total: int, progress_cb: ProgressCallback | None = None,
                 cancelled: CancelCallback | None = None, head: bytes = b"", tail: bytes = b"",
                 label: str = "Se încarcă înregistrarea", share: float = 1.0,
                 done_message: str = "") -> None:
        self._handle = handle; self._total = max(total, 1); self._sent = 0; self._step = -1
        self._progress_cb = progress_cb; self._cancelled = cancelled
        self._head = memoryview(head); self._tail = memoryview(tail)
        self._label = label; self._share = share; self._done_message = done_message; self._announced = False

    def _slice(self, buffer: memoryview, size: int) -> tuple[bytes, memoryview]:
        take = len(buffer) if size < 0 else min(size, len(buffer))
        return bytes(buffer[:take]), buffer[take:]

    @property
    def sent(self) -> int:
        return self._sent

    def read(self, size: int = -1) -> bytes:
        if self._cancelled and self._cancelled():
            raise ProviderError("The upload was cancelled.")
        if len(self._head):
            block, self._head = self._slice(self._head, size)
            return block
        block = self._handle.read(size)
        if block:
            self._sent += len(block)
            share = min(1.0, self._sent / self._total)
            step = int(share * UPLOAD_STEPS)
            if step != self._step:
                self._step = step
                # Bytes, not a second percentage: the progress bar owns the only percentage on
                # screen, so the card can never show two different numbers for one upload.
                emit_progress(self._progress_cb,
                              f"{self._label}: {human_size(self._sent)} of {human_size(self._total)}.",
                              share * self._share)
            return block
        if len(self._tail):
            block, self._tail = self._slice(self._tail, size)
            return block
        self._announce()
        return b""

    def _announce(self) -> None:
        if self._announced or not self._done_message: return
        self._announced = True
        emit_progress(self._progress_cb, self._done_message, self._share)


def multipart_parts(fields: dict[str, str], file_field: str, path: Path) -> tuple[bytes, bytes, str]:
    """Antetul și subsolul unui corp multipart care conține câmpuri simple și un fișier."""
    head = bytearray()
    for name, value in fields.items():
        head += f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8")
    head += (f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
             f"filename=\"{path.name}\"\r\nContent-Type: {content_type(path)}\r\n\r\n").encode("utf-8")
    tail = f"\r\n--{BOUNDARY}--\r\n".encode("utf-8")
    return bytes(head), tail, f"multipart/form-data; boundary={BOUNDARY}"


def _read_json(response: Any) -> dict[str, Any]:
    raw = response.read()
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    if not text.strip(): return {}
    try: parsed = json.loads(text)
    except ValueError: return {"text": text}
    return parsed if isinstance(parsed, dict) else {"items": parsed}


def error_detail(exc: HTTPError) -> str:
    try: body = json.loads(exc.read().decode("utf-8", "replace"))
    except Exception: return ""
    if isinstance(body, dict):
        for key in ("err_msg", "message", "error", "detail", "error_message"):
            value = body.get(key)
            if isinstance(value, dict): value = value.get("message")
            if value: return str(value)
    return ""


def friendly(service: str, code: int, detail: str) -> str:
    if code in (401, 403): return f"The {service} API key is invalid or lacks the required permissions."
    if code == 402: return f"Insufficient {service} credit. Check the billing on your account."
    if code == 404: return f"The requested address does not exist at {service}. Check the URL and the model name."
    if code == 413: return f"The recording exceeds the limit accepted by {service}."
    if code == 429: return f"Too many requests to {service}. Try again in a few moments."
    if code >= 500: return f"The {service} service is temporarily unavailable. Try again."
    return f"The request to {service} failed ({code}). {detail}".strip()


def send(service: str, url: str, headers: dict[str, str], data: Any = None, method: str = "GET",
         timeout: int = REQUEST_TIMEOUT) -> dict[str, Any]:
    """Trimite o cerere și returnează răspunsul JSON, cu erorile deja traduse."""
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return _read_json(response)
    except HTTPError as exc:
        raise ProviderError(friendly(service, exc.code, error_detail(exc)),
                            transient=exc.code in TRANSIENT_STATUS) from exc
    except URLError as exc:
        raise ProviderError(f"Could not connect to {service}: {exc.reason}", transient=True) from exc
    except ProviderError: raise
    except TimeoutError as exc:
        raise ProviderError(f"The connection to {service} stalled — no data moved for "
                            f"{timeout} seconds.", transient=True) from exc
    except OSError as exc:
        # A reset or truncated read mid-response; the job on the server is unaffected.
        raise ProviderError(f"The {service} response could not be read: {exc}", transient=True) from exc
    except ValueError as exc:
        raise ProviderError(f"The {service} response could not be read: {exc}") from exc


def send_json(service: str, url: str, headers: dict[str, str], payload: dict[str, Any],
              method: str = "POST", timeout: int = REQUEST_TIMEOUT) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    merged = {**headers, "Content-Type": "application/json", "Content-Length": str(len(body))}
    return send(service, url, merged, body, method, timeout)


RetryNotice = Callable[[int, int, float, ProviderError], None]


def with_retry(operation: Callable[[], Any], attempts: int = RETRY_ATTEMPTS,
               base_delay: float = RETRY_BASE_DELAY, on_retry: RetryNotice | None = None,
               sleeper: Callable[[float], None] = time.sleep,
               cancelled: CancelCallback | None = None) -> Any:
    """Run `operation`, retrying transient failures with exponential backoff.

    Permanent errors (a bad key, an unknown model) are raised on the first attempt: retrying
    them only wastes the researcher's time.
    """
    for attempt in range(1, attempts + 1):
        if cancelled and cancelled():
            raise ProviderError("The transcription was cancelled.")
        try:
            return operation()
        except ProviderError as exc:
            if attempt == attempts or not getattr(exc, "transient", False):
                raise
            delay = min(RETRY_MAX_DELAY, base_delay * (2 ** (attempt - 1)))
            if on_retry:
                on_retry(attempt, attempts, delay, exc)
            sleeper(delay)
    raise ProviderError("The request could not be completed.")


def upload_file(service: str, url: str, headers: dict[str, str], path: Path, file_field: str = "audio",
                fields: dict[str, str] | None = None, progress_cb: ProgressCallback | None = None,
                cancelled: CancelCallback | None = None, label: str = "Uploading the recording",
                share: float = 1.0, done_message: str = "", timeout: int = UPLOAD_TIMEOUT,
                attempts: int = 3, on_retry: RetryNotice | None = None,
                sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """Upload a file as streaming multipart/form-data, reporting progress.

    The body is a one-shot reader, so a retry cannot reuse it: each attempt reopens the file
    and starts a fresh reader. That makes the upload genuinely repeatable after a dropped
    connection instead of failing on a consumed handle.
    """
    head, tail, boundary_type = multipart_parts(fields or {}, file_field, path)
    size = path.stat().st_size
    merged = {**headers, "Content-Type": boundary_type, "Content-Length": str(len(head) + size + len(tail))}

    def attempt_upload() -> dict[str, Any]:
        # Bytes here too: the opening line must not introduce a percentage the bar contradicts.
        emit_progress(progress_cb, f"{label}: {human_size(0)} of {human_size(size)}.", 0.0)
        with path.open("rb") as handle:
            reader = UploadReader(handle, size, progress_cb, cancelled, head, tail, label, share, done_message)
            return send(service, url, merged, reader, "POST", timeout)

    return with_retry(attempt_upload, attempts, on_retry=on_retry, sleeper=sleeper, cancelled=cancelled)
