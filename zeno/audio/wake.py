"""
Zeno Wake Word Engine
Tries the local neural keyword-spotting engine first (see
zeno/audio/wake_word_nn.py) — a small dedicated model that runs
continuously at near-zero CPU/power cost. Falls back to this module's
own VAD + short-chunk STT polling on platforms where that isn't
available (e.g. Termux, no PipeWire): termux-microphone-record for raw
audio when available, or periodic STT polling otherwise. The fallback
is considerably more expensive to run continuously, since it invokes
full speech-to-text repeatedly rather than a dedicated small model.
"""

import math
import os
import struct
import subprocess
import tempfile
import time
from pathlib import Path

from zeno.audio.stt import listen
from zeno.audio import wake_word_nn

_WAKE_WORDS = ("zeno", "hey", "hey zeno")
_CHUNK_SEC = 1.0
_VAD_THRESHOLD = 500
_SAMPLE_RATE = 16000


def _can_record() -> bool:
    try:
        r = subprocess.run(
            ["termux-microphone-record", "--help"],
            capture_output=True, timeout=2
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _record_wav(path: str, duration: float = _CHUNK_SEC) -> bool:
    try:
        subprocess.run(
            ["termux-microphone-record", "-f", path,
             "-d", str(int(duration * 1000)), "-r", str(_SAMPLE_RATE),
             "-c", "1", "-b", "16"],
            capture_output=True, timeout=int(duration) + 3
        )
        return os.path.getsize(path) > 44
    except Exception:
        return False


def _rms_from_wav(path: str) -> float:
    try:
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 44:
            return 0.0
        audio = data[44:]
        if len(audio) < 2:
            return 0.0
        n = len(audio) // 2
        fmt = "<" + "h" * n
        samples = struct.unpack(fmt, audio[:n * 2])
        sq = sum(s * s for s in samples)
        return math.sqrt(sq / n)
    except Exception:
        return 0.0


def _has_speech(path: str) -> bool:
    return _rms_from_wav(path) > _VAD_THRESHOLD


def wait_for_wake_word(timeout: int = 30) -> str | None:
    """
    Listen for the wake word and return the command spoken after it,
    or None on timeout.

    Prefers the low-power neural KWS engine (wake_word_nn) when it's
    available; falls back to VAD + short-chunk STT polling otherwise.
    """
    if wake_word_nn.is_available():
        detected = wake_word_nn.wait_for_wake_word(timeout=timeout)
        if detected:
            return listen(timeout=10)
        return None
    return _legacy_wait_for_wake_word(timeout=timeout)


def _legacy_wait_for_wake_word(timeout: int = 30) -> str | None:
    """
    Continuously listen for wake word using VAD + short-chunk STT.
    Returns the full command after wake word is detected.
    First checks for termux-microphone-record; falls back to
    periodic STT polling.
    """
    has_raw = _can_record()
    deadline = time.time() + timeout
    cmd_timeout = int(timeout)

    if not has_raw:
        return _poll_stt_fallback(cmd_timeout)

    tmpdir = Path(tempfile.mkdtemp(prefix="zeno_wake_"))
    try:
        while time.time() < deadline:
            chunk = tmpdir / f"chunk_{int(time.time() * 1000)}.wav"
            ok = _record_wav(str(chunk))
            if not ok:
                continue
            if not _has_speech(str(chunk)):
                chunk.unlink(missing_ok=True)
                continue
            text = listen(timeout=_CHUNK_SEC + 1)
            chunk.unlink(missing_ok=True)
            if text and any(w in text.lower() for w in _WAKE_WORDS):
                remaining = int(deadline - time.time())
                cmd = listen(timeout=min(remaining, 10))
                return cmd or text
    finally:
        for f in tmpdir.iterdir():
            f.unlink(missing_ok=True)
        tmpdir.rmdir()
    return None


def _poll_stt_fallback(timeout: int) -> str | None:
    """Fallback: run STT in short cycles, checking for wake word."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        text = listen(timeout=3)
        if text and any(w in text.lower() for w in _WAKE_WORDS):
            remaining = int(deadline - time.time())
            cmd = listen(timeout=min(remaining, 10))
            return cmd or text
    return None
