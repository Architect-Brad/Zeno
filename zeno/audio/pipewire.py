"""
Zeno PipeWire Audio Capture
Records audio from PipeWire nodes for STT processing.
Used as the Linux audio input backend.
"""

import os
import subprocess
import tempfile
import time
import shutil
from pathlib import Path


_SAMPLE_RATE = 16000
_CHANNELS = 1
_FORMAT = "s16"


def _which_pw() -> str | None:
    return shutil.which("pw-record") or shutil.which("pw-cat")


def is_available() -> bool:
    return _which_pw() is not None


def record(duration: float = 5.0, sample_rate: int = _SAMPLE_RATE) -> str | None:
    """Record audio from PipeWire default source.
    Returns path to a WAV file, or None on failure."""
    pw = _which_pw()
    if not pw:
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    path = tmp.name

    try:
        cmd = [
            pw, "--latency", "0",
            "--quality", "10",
            "--rate", str(sample_rate),
            "--channels", str(_CHANNELS),
            "--format", _FORMAT,
            "-d", str(int(duration * 1000)),
            path,
        ]
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=int(duration) + 5,
        )
        if os.path.getsize(path) > 44:
            return path
        os.unlink(path)
        return None
    except (subprocess.TimeoutExpired, OSError):
        if os.path.exists(path):
            os.unlink(path)
        return None


def record_stdout(duration: float = 5.0, sample_rate: int = _SAMPLE_RATE) -> bytes | None:
    """Record audio from PipeWire and return raw PCM bytes (s16le)."""
    pw = _which_pw()
    if not pw:
        return None

    try:
        result = subprocess.run(
            [
                pw, "--latency", "0",
                "--quality", "10",
                "--rate", str(sample_rate),
                "--channels", str(_CHANNELS),
                "--format", _FORMAT,
                "-d", str(int(duration * 1000)),
                "-",
            ],
            capture_output=True,
            timeout=int(duration) + 5,
        )
        data = result.stdout
        if len(data) > 44:
            return data
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def stream_chunks(chunk_seconds: float = 0.08, sample_rate: int = _SAMPLE_RATE):
    """Continuously yield fixed-size raw PCM (s16le) chunks from the
    default PipeWire source via a single long-running subprocess.

    This exists specifically for continuous, low-latency use cases like
    wake-word keyword spotting, which need audio in ~80ms chunks —
    record()/record_stdout() spawn a brand new subprocess per call,
    which is fine for one-shot STT capture but has enough overhead
    (process startup, PipeWire negotiation) to make it impractical to
    call once per 80ms without dropping audio.

    Usage:
        gen = stream_chunks(0.08)
        for chunk in gen:
            ...
            if done:
                gen.close()   # terminates the underlying subprocess
                break
    """
    pw = _which_pw()
    if not pw:
        return

    bytes_per_chunk = int(chunk_seconds * sample_rate) * 2  # s16 = 2 bytes/sample
    proc = subprocess.Popen(
        [
            pw, "--latency", "0",
            "--quality", "10",
            "--rate", str(sample_rate),
            "--channels", str(_CHANNELS),
            "--format", _FORMAT,
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        while True:
            data = proc.stdout.read(bytes_per_chunk)
            if not data or len(data) < bytes_per_chunk:
                break
            yield data
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def list_sources() -> list[dict]:
    """List available PipeWire audio sources."""
    pw = shutil.which("pw-cli")
    if not pw:
        return []
    try:
        result = subprocess.run(
            [pw, "list-objects", "Node"],
            capture_output=True, timeout=5, text=True,
        )
        sources: list[dict] = []
        current: dict = {}
        for line in result.stdout.splitlines():
            if "node.name" in line:
                current["name"] = line.split("=")[-1].strip().strip('"')
            if "node.description" in line:
                current["description"] = line.split("=")[-1].strip().strip('"')
            if "media.class" in line and "Audio/Source" in line:
                if current:
                    sources.append(current)
                    current = {}
        return sources
    except Exception:
        return []
