from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from models import MediaToolPaths


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _validate(ffmpeg: Path, ffprobe: Path, source: str) -> MediaToolPaths:
    if not ffmpeg.is_file() or not ffprobe.is_file():
        return MediaToolPaths()
    try:
        first = subprocess.run([str(ffmpeg), "-version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=8, creationflags=_creation_flags(), check=False)
        second = subprocess.run([str(ffprobe), "-version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=8, creationflags=_creation_flags(), check=False)
        if first.returncode or second.returncode:
            return MediaToolPaths()
        version = (first.stdout.splitlines() or ["FFmpeg"])[0].strip()
        return MediaToolPaths(str(ffmpeg.resolve()), str(ffprobe.resolve()), source, version, True)
    except (OSError, subprocess.SubprocessError):
        return MediaToolPaths()


def _candidate_roots() -> list[tuple[Path, str]]:
    app_root = Path(__file__).resolve().parent
    executable_root = Path(sys.executable).resolve().parent
    roots: list[tuple[Path, str]] = [
        (app_root / "assets" / "bin" / "windows", "bundled"),
        (executable_root / "assets" / "bin" / "windows", "bundled"),
        (executable_root / "bin" / "windows", "bundled"),
        (executable_root, "bundled"),
    ]
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        roots.insert(1, (Path(frozen_root) / "assets" / "bin" / "windows", "bundled"))
    return roots


def resolve_media_tools(user_configured_paths: Iterable[str] | None = None) -> MediaToolPaths:
    """Locate and validate one matching FFmpeg/FFprobe pair in the required priority order."""
    seen: set[str] = set()
    for root, source in _candidate_roots():
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        result = _validate(root / "ffmpeg.exe", root / "ffprobe.exe", source)
        if result.is_valid:
            return result

    ffmpeg_found, ffprobe_found = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if ffmpeg_found and ffprobe_found:
        ffmpeg, ffprobe = Path(ffmpeg_found), Path(ffprobe_found)
        if ffmpeg.parent.resolve() == ffprobe.parent.resolve():
            result = _validate(ffmpeg, ffprobe, "system_path")
            if result.is_valid:
                return result

    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget.is_dir():
        for ffmpeg in winget.glob("**/ffmpeg.exe"):
            ffprobe = ffmpeg.with_name("ffprobe.exe")
            result = _validate(ffmpeg, ffprobe, "winget")
            if result.is_valid:
                return result
    for raw in user_configured_paths or []:
        if raw:
            path = Path(raw).expanduser()
            root = path.parent if path.is_file() else path
            result = _validate(root / "ffmpeg.exe", root / "ffprobe.exe", "user_selected")
            if result.is_valid:
                return result
    return MediaToolPaths()
