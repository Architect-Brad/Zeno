"""
Zeno VAD — Voice Activity Detection for continuous listening
Energy-based (RMS) with adaptive threshold. No external dependencies.
Supports PipeWire streaming and termux-microphone-record polling.
"""

import math
import os
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from threading import Event

from zeno.audio.pipewire import stream_chunks, is_available as pw_available

_SAMPLE_RATE = 16000
_CHUNK_SEC = 0.08
_BYTES_PER_CHUNK = int(_CHUNK_SEC * _SAMPLE_RATE) * 2

# VAD tuning
_SILENCE_HANGOVER = 0.6
_MIN_UTTERANCE = 0.5
_MAX_UTTERANCE = 30.0
_SPEECH_THRESHOLD = 400
_ADAPT_FACTOR = 0.005


def rms(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    n = len(data) // 2
    fmt = "<" + "h" * n
    try:
        samples = struct.unpack(fmt, data[:n * 2])
    except struct.error:
        return 0.0
    sq = sum(s * s for s in samples)
    return math.sqrt(sq / n) if n else 0.0


class EnergyVAD:
    def __init__(self, threshold: int = _SPEECH_THRESHOLD, sample_rate: int = _SAMPLE_RATE):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._noise_floor: float = 100.0
        self._hangover_chunks = int(_SILENCE_HANGOVER / _CHUNK_SEC)
        self._min_chunks = int(_MIN_UTTERANCE / _CHUNK_SEC)
        self._max_chunks = int(_MAX_UTTERANCE / _CHUNK_SEC)

    def _classify(self, energy: float) -> bool:
        self._noise_floor += (energy - self._noise_floor) * _ADAPT_FACTOR
        dyn_threshold = max(self._noise_floor * 2.5, self.threshold)
        return energy > dyn_threshold

    def listen(self, stop: Event | None = None) -> bytes | None:
        """Capture one utterance from the microphone.
        Blocks until speech is detected, then records until silence.
        Returns raw PCM s16le bytes, or None if cancelled.
        """
        gen = stream_chunks(_CHUNK_SEC, self.sample_rate)
        if not gen:
            return None

        buffer = bytearray()
        speaking = False
        silence_count = 0
        total_chunks = 0

        for chunk in gen:
            if stop and stop.is_set():
                gen.close()
                return None

            energy = rms(chunk)
            is_speech = self._classify(energy)

            if is_speech and not speaking:
                speaking = True
                buffer.extend(chunk)
                silence_count = 0
                total_chunks = 1
                continue

            if speaking:
                buffer.extend(chunk)
                total_chunks += 1

                if is_speech:
                    silence_count = 0
                else:
                    silence_count += 1

                if (silence_count >= self._hangover_chunks
                        and total_chunks >= self._min_chunks):
                    gen.close()
                    return bytes(buffer)

                if total_chunks >= self._max_chunks:
                    gen.close()
                    return bytes(buffer)

        return bytes(buffer) if buffer else None


def record_utterance_termux(timeout: float = 30.0) -> str | None:
    """Termux fallback: record short chunks, check VAD, accumulate utterance."""
    deadline = time.time() + timeout
    vad = EnergyVAD()
    buffer = bytearray()
    speaking = False
    silence_count = 0

    while time.time() < deadline:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            subprocess.run(
                ["termux-microphone-record", "-f", tmp.name,
                 "-d", "300", "-r", str(_SAMPLE_RATE),
                 "-c", "1", "-b", "16"],
                capture_output=True, timeout=2,
            )
            with open(tmp.name, "rb") as f:
                data = f.read()
        except Exception:
            os.unlink(tmp.name)
            continue
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

        if len(data) <= 44:
            continue
        pcm = data[44:]
        if not pcm:
            continue
        energy = rms(pcm)
        is_speech = vad._classify(energy)

        if is_speech and not speaking:
            speaking = True
            buffer.extend(pcm)
            silence_count = 0
            continue

        if speaking:
            buffer.extend(pcm)
            if is_speech:
                silence_count = 0
            else:
                silence_count += 1
            if silence_count >= 3 and len(buffer) > _SAMPLE_RATE // 2:
                break

    if not buffer:
        return None
    return _pcm_to_wav(bytes(buffer))


def _pcm_to_wav(pcm: bytes) -> str:
    """Wrap raw PCM s16le data in a WAV container and return the file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    path = tmp.name
    sample_rate = _SAMPLE_RATE
    bits = 16
    channels = 1
    data_size = len(pcm)
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * channels * bits // 8))
        f.write(struct.pack("<H", channels * bits // 8))
        f.write(struct.pack("<H", bits))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(pcm)
    return path


_TERMUX_HAS_MIC = None


def _can_termux_mic() -> bool:
    global _TERMUX_HAS_MIC
    if _TERMUX_HAS_MIC is None:
        try:
            r = subprocess.run(
                ["termux-microphone-record", "--help"],
                capture_output=True, timeout=2,
            )
            _TERMUX_HAS_MIC = r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            _TERMUX_HAS_MIC = False
    return _TERMUX_HAS_MIC


def listen_continuous(timeout: float = 30.0, stop: Event | None = None) -> str | None:
    """Wait for a complete utterance using VAD.
    Returns path to a WAV file, or None on timeout/cancel.
    """
    if pw_available():
        pcm = EnergyVAD().listen(stop=stop)
        if pcm:
            return _pcm_to_wav(pcm)
        return None

    if _can_termux_mic():
        return record_utterance_termux(timeout=timeout)

    return None
