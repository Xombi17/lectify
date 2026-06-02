"""Audio chunking utilities for long-lecture handling.

We rely on the `ffmpeg`/`ffprobe` binaries (installed in the container and the
Docker image) — calling them via subprocess is more reliable than wiring a
Python audio library and avoids native-build pain.

Two operations:
  - `get_duration_seconds(path)` -> float, via ffprobe
  - `split_into_chunks(path, chunk_seconds)` -> list[Path] of chunk files

Chunks are written next to the source file in a sibling `.chunks/` directory.
Caller owns cleanup via `cleanup_chunks(paths)` once processing is done.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class FFmpegNotAvailable(RuntimeError):
    """Raised when ffmpeg / ffprobe are not on PATH."""


def _ensure_binaries() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise FFmpegNotAvailable(
            "ffmpeg/ffprobe must be installed on PATH. "
            "Debian/Ubuntu: `apt-get install -y ffmpeg`."
        )


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", "ignore"), err.decode("utf-8", "ignore")


async def get_duration_seconds(path: Path) -> float:
    """Return audio duration in seconds. Raises on failure."""
    _ensure_binaries()
    rc, out, err = await _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    if rc != 0:
        raise RuntimeError(f"ffprobe failed: {err.strip()}")
    try:
        return float(out.strip())
    except ValueError as exc:
        raise RuntimeError(f"Could not parse duration: {out!r}") from exc


async def split_into_chunks(
    source: Path,
    chunk_seconds: int,
    out_format: str = "mp3",
) -> List[Path]:
    """Split `source` into N-second segments. Returns list of chunk paths in order.

    Re-encodes to MP3 for compact uploads (Gemini accepts most formats but MP3
    keeps file sizes predictable and small).
    """
    _ensure_binaries()
    chunks_dir = source.parent / ".chunks"
    chunks_dir.mkdir(exist_ok=True)
    # Wipe stale chunks for this source
    for f in chunks_dir.glob(f"{source.stem}_*.{out_format}"):
        try:
            f.unlink()
        except OSError:
            pass

    pattern = chunks_dir / f"{source.stem}_%03d.{out_format}"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
        "-vn",                 # no video
        "-acodec", "libmp3lame",
        "-b:a", "64k",         # 64 kbps mono-ish — plenty for speech recognition
        "-ac", "1",            # downmix to mono
        "-f", "segment",
        "-segment_time", str(int(chunk_seconds)),
        "-reset_timestamps", "1",
        str(pattern),
    ]
    rc, _out, err = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"ffmpeg segmenting failed: {err.strip()}")

    chunks = sorted(chunks_dir.glob(f"{source.stem}_*.{out_format}"))
    if not chunks:
        raise RuntimeError("ffmpeg produced no chunks")
    logger.info("Split %s into %d chunk(s)", source.name, len(chunks))
    return chunks


def cleanup_chunks(paths: List[Path]) -> None:
    """Best-effort delete of chunk files (and parent dir if empty)."""
    parents = set()
    for p in paths:
        try:
            p.unlink()
            parents.add(p.parent)
        except OSError:
            pass
    for d in parents:
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass


def format_timestamp(seconds: float) -> str:
    """Render seconds as `HH:MM:SS` (or `MM:SS` when <1 hour)."""
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
