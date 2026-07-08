"""
Zeno Kokoro-82M TTS
Local TTS using the Kokoro-82M model (https://github.com/thewh1teagle/kokoro-onnx),
an 82-million-parameter model that runs on CPU via ONNX Runtime — noticeably
higher quality than Piper's small voices, at the cost of a larger download
(~326MB model + ~27MB voices file) and somewhat slower synthesis.

Falls back to Piper, then platform-native TTS, when unavailable.
"""

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

try:
    from kokoro_onnx import Kokoro as _KokoroEngine
except ImportError:
    _KokoroEngine = None

_MODEL_DIR = Path.home() / ".zeno" / "kokoro"
_MODEL_URL = ("https://github.com/thewh1teagle/kokoro-onnx/releases/"
              "download/model-files-v1.0/kokoro-v1.0.onnx")
_VOICES_URL = ("https://github.com/thewh1teagle/kokoro-onnx/releases/"
               "download/model-files-v1.0/voices-v1.0.bin")
_DEFAULT_VOICE = "af_sarah"  # the voice used in kokoro-onnx's own example

_engine = None  # lazily-loaded Kokoro instance (loading the model is the slow part)


def _model_path() -> Path:
    return _MODEL_DIR / "kokoro-v1.0.onnx"


def _voices_path() -> Path:
    return _MODEL_DIR / "voices-v1.0.bin"


def is_available() -> bool:
    return _KokoroEngine is not None


def is_model_downloaded() -> bool:
    return _model_path().exists() and _voices_path().exists()


def download_model() -> bool:
    """Download the Kokoro model + voices file if not already present."""
    if is_model_downloaded():
        return True

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
        for url, path in ((_MODEL_URL, _model_path()), (_VOICES_URL, _voices_path())):
            print(f"[Zeno] Downloading Kokoro file ({url})...")
            urllib.request.urlretrieve(url, str(path))
        return is_model_downloaded()
    except Exception as e:
        print(f"[Zeno] Failed to download Kokoro model: {e}")
        for path in (_model_path(), _voices_path()):
            if path.exists():
                path.unlink()
        return False


def _get_engine():
    global _engine
    if _engine is None:
        _engine = _KokoroEngine(str(_model_path()), str(_voices_path()))
    return _engine


def _write_wav(path: str, samples, sample_rate: int):
    """Write float32 [-1, 1] samples (as returned by Kokoro) to a WAV
    file using only the stdlib — avoids adding a soundfile dependency
    just to write a mono PCM16 file."""
    import numpy as np
    clipped = np.clip(samples, -1.0, 1.0)
    pcm16 = (clipped * 32767).astype(np.int16)
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16.tobytes())


def _play_wav(path: str) -> bool:
    for player, args in (
        ("paplay", [path]),
        ("aplay", ["-q", path]),
        ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet", path]),
    ):
        binpath = shutil.which(player)
        if binpath:
            try:
                subprocess.run([binpath, *args], capture_output=True, timeout=30)
                return True
            except Exception:
                continue
    return False


def speak(text: str, voice: str = _DEFAULT_VOICE, speed: float = 1.0,
          lang: str = "en-us") -> bool:
    """Synthesize `text` with Kokoro and play it. Returns False (rather
    than raising) on any failure so callers can fall back."""
    if not is_available() or not is_model_downloaded():
        return False

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        engine = _get_engine()
        samples, sample_rate = engine.create(text, voice=voice, speed=speed, lang=lang)
        _write_wav(tmp.name, samples, sample_rate)
        if os.path.getsize(tmp.name) <= 44:
            return False
        return _play_wav(tmp.name)
    except Exception as e:
        print(f"[Zeno] Kokoro error: {e}")
        return False
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
