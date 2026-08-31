from __future__ import annotations

import json, math, subprocess
from pathlib import Path
from typing import Callable

from media_tools import resolve_media_tools
from models import AudioChunk, AudioInfo, MediaToolPaths

SUPPORTED_EXTENSIONS = {".m4a", ".wav", ".mp3", ".mp4", ".aac", ".flac", ".webm"}
SAFETY_FACTOR = 0.88


class AudioProcessingError(RuntimeError): pass


def check_tools(tools: MediaToolPaths | None = None) -> MediaToolPaths:
    resolved = tools or resolve_media_tools()
    if not resolved.is_valid: raise AudioProcessingError("FFmpeg și FFprobe nu sunt disponibile sau nu au putut fi validate.")
    return resolved


def validate_audio_path(raw_path: str) -> Path:
    path = Path(raw_path.strip().strip('"')).expanduser()
    if not path.is_file(): raise AudioProcessingError("Calea nu indică un fișier existent.")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise AudioProcessingError("Format nesuportat. Folosiți M4A, WAV, MP3, MP4, AAC, FLAC sau WEBM.")
    return path.resolve()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)


def probe_audio(raw_path: str, tools: MediaToolPaths | None = None) -> AudioInfo:
    resolved = check_tools(tools); path = validate_audio_path(raw_path)
    result = _run([resolved.ffprobe_path, "-v", "error", "-show_entries",
        "format=duration,bit_rate:stream=index,codec_type,codec_name,sample_rate,channels,bit_rate", "-of", "json", str(path)])
    if result.returncode: raise AudioProcessingError(f"ffprobe nu a putut analiza fișierul: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout); stream = next(x for x in data.get("streams", []) if x.get("codec_type") == "audio")
        duration = float(data.get("format", {}).get("duration") or 0)
    except (ValueError, TypeError, StopIteration, json.JSONDecodeError) as exc:
        raise AudioProcessingError("Fișierul nu conține un flux audio valid.") from exc
    if duration <= 0: raise AudioProcessingError("Durata fluxului audio nu este validă.")
    bitrate = stream.get("bit_rate") or data.get("format", {}).get("bit_rate")
    return AudioInfo(str(path), path.name, path.stat().st_size, duration, str(stream.get("codec_name") or "necunoscut"),
                     int(stream.get("sample_rate") or 0), int(stream.get("channels") or 0), int(bitrate) if bitrate else None)


def estimate_chunk_duration(info: AudioInfo, max_mb: float = 23.0) -> float:
    target = max_mb * 1024 * 1024 * SAFETY_FACTOR / max(info.size_bytes / info.duration, 1)
    return max(60.0, min(target, 22 * 60.0))


def estimated_chunk_count(info: AudioInfo, overlap_seconds: float = 0, max_mb: float = 23.0) -> int:
    duration = estimate_chunk_duration(info, max_mb); step = max(1.0, duration - overlap_seconds)
    return max(1, math.ceil(max(0.0, info.duration - overlap_seconds) / step))


def _make_chunk(ffmpeg_path: str, source: Path, output: Path, start: float, duration: float, copy: bool, bitrate_kbps: int) -> None:
    cmd = [ffmpeg_path, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", str(source),
           "-t", f"{duration:.3f}", "-map", "0:a:0", "-vn"]
    cmd += ["-c:a", "copy"] if copy else ["-c:a", "aac", "-ac", "1", "-ar", "16000", "-b:a", f"{bitrate_kbps}k"]
    cmd.append(str(output)); result = _run(cmd)
    if result.returncode or not output.is_file() or not output.stat().st_size:
        raise AudioProcessingError(f"FFmpeg nu a putut crea fragmentul: {result.stderr.strip()}")


def create_chunks(info: AudioInfo, output_dir: str, overlap_seconds: float = 0,
                  progress: Callable[[int, int, str], None] | None = None, max_mb: float = 23.0,
                  bitrate_kbps: int = 48, force_encode: bool = False,
                  cancelled: Callable[[], bool] | None = None, tools: MediaToolPaths | None = None) -> list[AudioChunk]:
    resolved = check_tools(tools)
    source, folder = Path(info.path), Path(output_dir); folder.mkdir(parents=True, exist_ok=True)
    max_bytes = int(max_mb * 1024 * 1024); chunk_duration = estimate_chunk_duration(info, max_mb)
    overlap_seconds = max(0.0, min(overlap_seconds, chunk_duration / 2)); count = estimated_chunk_count(info, overlap_seconds, max_mb)
    copy_allowed = not force_encode and source.suffix.lower() in {".m4a", ".mp4", ".aac", ".mp3", ".webm"}

    def build(copy: bool) -> list[AudioChunk]:
        chunks: list[AudioChunk] = []; start = 0.0; index = 1
        while start < info.duration - .05:
            if cancelled and cancelled(): raise AudioProcessingError("Procesarea a fost anulată.")
            duration = min(chunk_duration, info.duration - start)
            if progress: progress(index, count, f"Se creează fragmentul {index} din {count}.")
            suffix = source.suffix.lower() if copy else ".m4a"; path = folder / f"fragment_{index:03d}{suffix}"
            _make_chunk(resolved.ffmpeg_path, source, path, start, duration, copy, bitrate_kbps)
            if path.stat().st_size > max_bytes: raise AudioProcessingError("Un fragment depășește limita sigură configurată.")
            chunks.append(AudioChunk(index, str(path), start, duration, path.stat().st_size,
                                     "copiere flux" if copy else f"AAC mono 16 kHz, {bitrate_kbps} kbps",
                                     overlap_seconds if index > 1 else 0.0))
            if start + duration >= info.duration - .05: break
            start += max(1.0, chunk_duration - overlap_seconds); index += 1
        return chunks

    if copy_allowed:
        try: return build(True)
        except AudioProcessingError:
            for child in folder.iterdir():
                if child.is_file(): child.unlink(missing_ok=True)
    chunks = build(False)
    if not chunks: raise AudioProcessingError("Nu a fost creat niciun fragment audio.")
    return chunks
