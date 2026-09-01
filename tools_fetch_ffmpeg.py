"""Fetch the FFmpeg pair the application bundles.

The binaries are deliberately not committed. They are ~194 MB, they change only when the
pinned version below changes, and keeping them in Git LFS on a public repository spends a
finite monthly bandwidth allowance on every clone and every CI run.

So there is one place that knows which build we ship — this file — and both the release
workflow and a developer working from source call it. Run it with no arguments:

    python tools_fetch_ffmpeg.py

It is idempotent: if the correct pair is already in place it does nothing.

Only the essentials build is fetched. The application uses the native AAC encoder, the MP4
muxer and the standard demuxers, all of which essentials carries; the full build adds
external libraries this application never invokes and 268 MB of download for them.
"""
from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "8.1.2"
BUILD = "essentials"
ARCHIVE = f"ffmpeg-{VERSION}-{BUILD}_build.zip"
URL = f"https://github.com/GyanD/codexffmpeg/releases/download/{VERSION}/{ARCHIVE}"
TARGET = Path(__file__).resolve().parent / "assets" / "bin" / "windows"
WANTED = ("ffmpeg.exe", "ffprobe.exe")
# Below this a file is a Git LFS pointer, a truncated download, or an error page.
MIN_BYTES = 5 * 1024 * 1024


def present() -> bool:
    return all((TARGET / name).is_file() and (TARGET / name).stat().st_size >= MIN_BYTES
               for name in WANTED)


def reported_version(executable: Path) -> str:
    result = subprocess.run([str(executable), "-hide_banner", "-version"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    return (result.stdout.splitlines() or [""])[0].strip()


def fetch(log=print) -> Path:
    """Download, extract and verify. Returns the directory the pair now lives in."""
    if present():
        log(f"FFmpeg already present: {reported_version(TARGET / 'ffmpeg.exe')}")
        return TARGET
    log(f"Downloading {URL}")
    with urllib.request.urlopen(URL, timeout=600) as response:
        payload = response.read()
    log(f"Downloaded {len(payload) / 1024 / 1024:.1f} MB "
        f"(sha256 {hashlib.sha256(payload).hexdigest()[:16]}...)")
    TARGET.mkdir(parents=True, exist_ok=True)
    archive = zipfile.ZipFile(io.BytesIO(payload))
    for entry in archive.namelist():
        name = entry.rsplit("/", 1)[-1]
        if entry.endswith(tuple(f"bin/{binary}" for binary in WANTED)):
            (TARGET / name).write_bytes(archive.read(entry))
            log(f"  extracted {name} ({(TARGET / name).stat().st_size / 1024 / 1024:.1f} MB)")
        elif name == "LICENSE":
            (TARGET / "LICENSE-FFMPEG.txt").write_bytes(archive.read(entry))
            log("  extracted LICENSE-FFMPEG.txt")
    if not present():
        raise RuntimeError(f"{ARCHIVE} did not contain both of {WANTED}")
    for binary in WANTED:
        log(f"  {reported_version(TARGET / binary)}")
    return TARGET


if __name__ == "__main__":
    try:
        fetch()
    except Exception as error:                       # noqa: BLE001 - a CLI reports and exits
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
