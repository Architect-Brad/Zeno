"""
Zeno faster-whisper STT
Local speech-to-text using faster-whisper (CTranslate2-based Whisper).
Generally more accurate and faster than whisper.cpp on desktop CPUs, but
the ctranslate2 wheels this depends on don't build/install on Termux
(Android/bionic libc), so this engine is desktop-only by design —
is_available() returns False on Termux even if the package happens to
be importable.

Falls back to whisper.cpp, then platform-native STT, when unavailable.
"""

import os
from pathlib import Path

try:
    import faster_whisper as _fw
except ImportError:
    _fw = None

_DEFAULT_MODEL = "small"
_model_cache: dict[str, object] = {}


def _is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or Path("/data/data/com.termux").exists()


def is_available() -> bool:
    return _fw is not None and not _is_termux()


def is_model_downloaded(model: str = _DEFAULT_MODEL) -> bool:
    """faster-whisper manages its own Hugging Face cache, so 'downloaded'
    means 'loadable without hitting the network'."""
    if not is_available():
        return False
    try:
        _fw.WhisperModel(model, device="cpu", compute_type="int8", local_files_only=True)
        return True
    except Exception:
        return False


def download_model(model: str = _DEFAULT_MODEL) -> bool:
    """Trigger faster-whisper's own download-and-cache of a model."""
    if not is_available():
        return False
    try:
        print(f"[Zeno] Downloading faster-whisper model '{model}' (first use only)...")
        _model_cache[model] = _fw.WhisperModel(model, device="cpu", compute_type="int8")
        return True
    except Exception as e:
        print(f"[Zeno] Failed to download faster-whisper model: {e}")
        return False


def _get_model(model: str = _DEFAULT_MODEL):
    if model not in _model_cache:
        _model_cache[model] = _fw.WhisperModel(model, device="cpu", compute_type="int8")
    return _model_cache[model]


def transcribe(audio_path: str, model: str = _DEFAULT_MODEL,
               language: str | None = None) -> str | None:
    """Transcribe an audio file. Returns the transcribed text, or None
    on failure (missing dependency, no cached model, bad audio, etc.)."""
    if not is_available():
        return None
    try:
        whisper_model = _get_model(model)
        segments, _info = whisper_model.transcribe(
            audio_path, language=language, beam_size=1, vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text if text else None
    except Exception as e:
        print(f"[Zeno] faster-whisper error: {e}")
        return None


def listen(timeout: float = 10.0, model: str = _DEFAULT_MODEL) -> str | None:
    """Record audio via PipeWire and transcribe with faster-whisper."""
    from zeno.audio.pipewire import record as pw_record, is_available as pw_available
    if not pw_available():
        return None

    path = pw_record(duration=timeout)
    if not path:
        return None
    try:
        return transcribe(path, model)
    finally:
        if os.path.exists(path):
            os.unlink(path)
