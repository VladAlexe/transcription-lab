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
    target=Path(path); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)


def write_text(path: str, data: str) -> None:
    target=Path(path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(data, encoding="utf-8-sig")


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
