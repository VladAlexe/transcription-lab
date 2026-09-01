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
    if not resolved.is_valid: raise AudioProcessingError("FFmpeg and FFprobe are unavailable or could not be validated.")
    return resolved


def validate_audio_path(raw_path: str) -> Path:
    path = Path(raw_path.strip().strip('"')).expanduser()
    if not path.is_file(): raise AudioProcessingError("That path does not point to an existing file.")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise AudioProcessingError("Unsupported format. Use M4A, WAV, MP3, MP4, AAC, FLAC, or WEBM.")
    return path.resolve()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)


def probe_audio(raw_path: str, tools: MediaToolPaths | None = None) -> AudioInfo:
    resolved = check_tools(tools); path = validate_audio_path(raw_path)
    result = _run([resolved.ffprobe_path, "-v", "error", "-show_entries",
        "format=duration,bit_rate:stream=index,codec_type,codec_name,sample_rate,channels,bit_rate", "-of", "json", str(path)])
    if result.returncode: raise AudioProcessingError(f"ffprobe could not analyse the file: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout); stream = next(x for x in data.get("streams", []) if x.get("codec_type") == "audio")
        duration = float(data.get("format", {}).get("duration") or 0)
    except (ValueError, TypeError, StopIteration, json.JSONDecodeError) as exc:
        raise AudioProcessingError("The file contains no usable audio stream.") from exc
    if duration <= 0: raise AudioProcessingError("The audio stream duration is not valid.")
    bitrate = stream.get("bit_rate") or data.get("format", {}).get("bit_rate")
    return AudioInfo(str(path), path.name, path.stat().st_size, duration, str(stream.get("codec_name") or "necunoscut"),
                     int(stream.get("sample_rate") or 0), int(stream.get("channels") or 0), int(bitrate) if bitrate else None)


def compress_command(ffmpeg_path: str, source: Path, output: Path, bitrate_kbps: int = 32) -> list[str]:
    """Re-encode to a compact speech profile: mono, 16 kHz, low-bitrate AAC.

    Speech recognition works from a 16 kHz mono signal; everything above that is bandwidth the
    upload has to survive for no accuracy gain. A two-hour interview drops from hundreds of
    megabytes to tens.
    """
    return [ffmpeg_path, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
            "-map", "0:a:0", "-vn", "-c:a", "aac", "-ac", "1", "-ar", "16000",
            "-b:a", f"{bitrate_kbps}k", str(output)]


def should_compress(size_bytes: int, threshold_mb: float) -> bool:
    return threshold_mb > 0 and size_bytes > threshold_mb * 1024 * 1024


def compress_for_upload(info: AudioInfo, output_dir: str, tools: MediaToolPaths | None = None,
                        bitrate_kbps: int = 32,
                        cancelled: Callable[[], bool] | None = None) -> AudioInfo:
    """Write a compact copy of `info` into `output_dir` and describe it as a normal recording.

    The original file is never touched, and the timeline is unchanged, so absolute timestamps
    in the transcript still refer to the real recording.
    """
    resolved = check_tools(tools)
    if cancelled and cancelled(): raise AudioProcessingError("Processing was cancelled.")
    source, folder = Path(info.path), Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"upload_{source.stem[:40]}.m4a"
    target.unlink(missing_ok=True)
    result = _run(compress_command(resolved.ffmpeg_path, source, target, bitrate_kbps))
    if cancelled and cancelled(): raise AudioProcessingError("Processing was cancelled.")
    if result.returncode or not target.is_file() or not target.stat().st_size:
        raise AudioProcessingError(f"The compact copy could not be created: {result.stderr.strip()}")
    return probe_audio(str(target), resolved)


def range_command(ffmpeg_path: str, source: Path, output: Path, start: float, end: float,
                  copy: bool, bitrate_kbps: int = 48) -> list[str]:
    """FFmpeg invocation that cuts one sub-clip, mirroring `_make_chunk`'s conventions."""
    command = [ffmpeg_path, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", str(source),
               "-t", f"{max(0.0, end - start):.3f}", "-map", "0:a:0", "-vn"]
    command += ["-c:a", "copy"] if copy else ["-c:a", "aac", "-ac", "1", "-ar", "16000", "-b:a", f"{bitrate_kbps}k"]
    command.append(str(output))
    return command


def extract_range(info: AudioInfo, output_dir: str, start: float, end: float, tools: MediaToolPaths | None = None,
                  force_encode: bool = False, bitrate_kbps: int = 48) -> AudioInfo:
    """Cut `start`–`end` from the source and return the clip described as a normal recording.

    The original file is never modified; the clip lives in the run's temporary directory.
    """
    resolved = check_tools(tools)
    source, folder = Path(info.path), Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    copy_allowed = not force_encode and source.suffix.lower() in {".m4a", ".mp4", ".aac", ".mp3", ".webm"}
    for copy in ([True, False] if copy_allowed else [False]):
        target = folder / f"range_{int(start)}_{int(end)}{source.suffix.lower() if copy else '.m4a'}"
        target.unlink(missing_ok=True)
        result = _run(range_command(resolved.ffmpeg_path, source, target, start, end, copy, bitrate_kbps))
        if result.returncode or not target.is_file() or not target.stat().st_size:
            continue
        return probe_audio(str(target), resolved)
    raise AudioProcessingError("The selected range could not be extracted from the recording.")


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
        raise AudioProcessingError(f"FFmpeg could not create the fragment: {result.stderr.strip()}")


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
            if cancelled and cancelled(): raise AudioProcessingError("Processing was cancelled.")
            duration = min(chunk_duration, info.duration - start)
            if progress: progress(index, count, f"Creating fragment {index} of {count}.")
            suffix = source.suffix.lower() if copy else ".m4a"; path = folder / f"fragment_{index:03d}{suffix}"
            _make_chunk(resolved.ffmpeg_path, source, path, start, duration, copy, bitrate_kbps)
            if path.stat().st_size > max_bytes: raise AudioProcessingError("A fragment exceeds the configured safe limit.")
            chunks.append(AudioChunk(index, str(path), start, duration, path.stat().st_size,
                                     "stream copy" if copy else f"AAC mono 16 kHz, {bitrate_kbps} kbps",
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
    if not chunks: raise AudioProcessingError("No audio fragment was created.")
    return chunks
