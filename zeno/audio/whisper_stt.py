"""
Zeno Whisper.cpp STT
Local speech-to-text using whisper.cpp with a tiny model.
Falls back to existing platform STT when whisper is not available.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from zeno.audio.pipewire import record as pw_record, is_available as pw_available

_WHISPER_BIN = shutil.which("whisper-cli") or shutil.which("whisper")
_MODEL_DIR = Path.home() / ".zeno" / "whisper-models"
_DEFAULT_MODEL = "tiny"


def _model_path(model: str = _DEFAULT_MODEL) -> Path:
    return _MODEL_DIR / f"ggml-{model}.bin"


def is_available() -> bool:
    return _WHISPER_BIN is not None


def download_model(model: str = _DEFAULT_MODEL) -> bool:
    """Download a whisper.cpp model if not present."""
    target = _model_path(model)
    if target.exists():
        return True

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    url = (
        f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
        f"ggml-{model}.bin"
    )

    try:
        import urllib.request
        print(f"[Zeno] Downloading whisper {model} model ({url})...")
        urllib.request.urlretrieve(url, str(target))
        return target.exists()
    except Exception as e:
        print(f"[Zeno] Failed to download whisper model: {e}")
        if target.exists():
            target.unlink()
        return False


def transcribe(audio_path: str, model: str = _DEFAULT_MODEL,
               language: str = "auto") -> str | None:
    """Transcribe an audio file using whisper.cpp.
    Returns the transcribed text, or None on failure."""
    if not _WHISPER_BIN:
        return None

    model_file = _model_path(model)
    if not model_file.exists():
        return None

    try:
        cmd = [
            _WHISPER_BIN,
            "-m", str(model_file),
            "-f", audio_path,
            "-l", language,
            "-otxt",  # output as plain text
            "--no-timestamps",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
            text=True,
        )
        text = result.stdout.strip()
        if not text and result.stderr:
            # Try parsing stderr for the transcription
            for line in result.stderr.splitlines():
                if "][" in line and "]" in line:
                    parts = line.split("]", 1)
                    if len(parts) > 1:
                        text = parts[1].strip()
                        break
        return text if text else None
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"[Zeno] Whisper error: {e}")
        return None


def transcribe_file(audio_path: str, model: str = _DEFAULT_MODEL) -> str | None:
    """Transcribe a WAV file."""
    return transcribe(audio_path, model)


def listen(timeout: float = 10.0, model: str = _DEFAULT_MODEL,
           language: str = "auto") -> str | None:
    """Record audio via PipeWire and transcribe with whisper.cpp.
    Returns transcribed text or None."""
    if not pw_available():
        return None

    path = pw_record(duration=timeout)
    if not path:
        return None

    try:
        text = transcribe(path, model, language)
        return text
    finally:
        if os.path.exists(path):
            os.unlink(path)


def is_model_downloaded(model: str = _DEFAULT_MODEL) -> bool:
    return _model_path(model).exists()


def list_models() -> list[Path]:
    """List downloaded whisper models."""
    if not _MODEL_DIR.exists():
        return []
    return sorted(_MODEL_DIR.glob("ggml-*.bin"))
