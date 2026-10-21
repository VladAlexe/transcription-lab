from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any


def human_size(size: int) -> str:
    value=float(size)
    for unit in ("B","KB","MB","GB","TB"):
        if value < 1024 or unit == "TB": return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def open_with_system(path: str) -> None: os.startfile(path)  # type: ignore[attr-defined]


def write_bytes(path: str, data: bytes) -> None:
    """Replace the file whole or not at all.

    Written in place, a save interrupted half way — the window closed, the machine slept, a
    sync client holding the file — left a truncated project that would not open again. The
    data goes to a sibling file first and is swapped in only once it is all on disk.
    """
    target=Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    staging=target.with_name(f".{target.name}.saving")
    try:
        with staging.open("wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(staging,target)
    except OSError:
        # Some folders refuse the rename (a sync client or scanner holding the target).
        # Writing directly is what this always did, so it remains the fallback.
        try: staging.unlink(missing_ok=True)
        except OSError: pass
        target.write_bytes(data)


def write_text(path: str, data: str) -> None:
    write_bytes(path, data.encode("utf-8-sig"))


def log_path() -> Path:
    root=Path(os.environ.get("LOCALAPPDATA",Path.home()))/"TranscriereInterviuri"
    root.mkdir(parents=True,exist_ok=True);return root/"transcription.log"


def append_log(line: str) -> None:
    """One timestamped line in the transcription log. Never raises: a log must not be the
    reason a transcription fails."""
    try:
        from datetime import datetime
        path=log_path()
        # Kept small: once past 1 MB the older half goes.
        if path.is_file() and path.stat().st_size>1_000_000:
            text=path.read_text(encoding="utf-8",errors="replace"); path.write_text(text[len(text)//2:],encoding="utf-8")
        with path.open("a",encoding="utf-8") as stream:
            stream.write(f"{datetime.now().isoformat(timespec='seconds')}  {line}\n")
    except Exception:
        pass


def load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as stream: return json.load(stream)


def preferences_path() -> Path:
    root=Path(os.environ.get("LOCALAPPDATA",Path.home()))/"TranscriereInterviuri"
    root.mkdir(parents=True,exist_ok=True);return root/"preferences.json"


def load_preferences() -> dict[str,Any]:
    try:return load_json(str(preferences_path()))
    except (OSError,ValueError,json.JSONDecodeError):return {}


def save_preferences(data:dict[str,Any])->None:
    preferences_path().write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
