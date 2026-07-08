"""
Zeno Piper TTS
Local, natural-sounding text-to-speech using Piper (https://github.com/rhasspy/piper).

Two backends, tried in order:
  1. The `piper-tts` pip package (in-process, ONNX Runtime under the hood,
     bundles espeak-ng-data) — no external binary needed.
  2. The standalone `piper` CLI binary, if installed system-wide instead.

Falls back to the platform's native TTS (espeak-ng, termux-tts-speak, etc.)
when neither is available or a voice hasn't been downloaded.
"""

import shutil
import subprocess
import tempfile
import wave
import os
from pathlib import Path

try:
    from piper.voice import PiperVoice as _PiperVoice
except ImportError:
    _PiperVoice = None

_PIPER_BIN = shutil.which("piper")
_VOICE_DIR = Path.home() / ".zeno" / "piper-voices"
_DEFAULT_VOICE = "en_US-lessac-medium"

# Piper voices are published under this base path on Hugging Face, e.g.
# .../en/en_US/lessac/medium/en_US-lessac-medium.onnx
_VOICE_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

_loaded_voices: dict[str, "_PiperVoice"] = {}  # cache so we don't reload the model every utterance


def _voice_paths(voice: str = _DEFAULT_VOICE) -> tuple[Path, Path]:
    onnx = _VOICE_DIR / f"{voice}.onnx"
    config = _VOICE_DIR / f"{voice}.onnx.json"
    return onnx, config


def is_available() -> bool:
    return _PiperVoice is not None or _PIPER_BIN is not None


def is_voice_downloaded(voice: str = _DEFAULT_VOICE) -> bool:
    onnx, config = _voice_paths(voice)
    return onnx.exists() and config.exists()


def list_voices() -> list[str]:
    """List voice names with both .onnx and .onnx.json present."""
    if not _VOICE_DIR.exists():
        return []
    return sorted(
        p.stem for p in _VOICE_DIR.glob("*.onnx")
        if (_VOICE_DIR / f"{p.stem}.onnx.json").exists()
    )


def download_voice(voice: str = _DEFAULT_VOICE) -> bool:
    """Download a Piper voice (.onnx + .onnx.json) if not already present.

    Voice names follow Piper's own naming, e.g. 'en_US-lessac-medium'.
    The path layout on the model repo is <lang>/<locale>/<name>/<quality>/,
    which we derive from the voice name itself.
    """
    onnx, config = _voice_paths(voice)
    if onnx.exists() and config.exists():
        return True

    parts = voice.split("-")
    if len(parts) != 3:
        print(f"[Zeno] Unrecognized Piper voice name format: {voice}")
        return False
    locale, name, quality = parts
    lang = locale.split("_")[0]
    remote_dir = f"{lang}/{locale}/{name}/{quality}"

    _VOICE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
        for path, suffix in ((onnx, ".onnx"), (config, ".onnx.json")):
            url = f"{_VOICE_BASE_URL}/{remote_dir}/{voice}{suffix}"
            print(f"[Zeno] Downloading Piper voice ({url})...")
            urllib.request.urlretrieve(url, str(path))
        return onnx.exists() and config.exists()
    except Exception as e:
        print(f"[Zeno] Failed to download Piper voice: {e}")
        for path in (onnx, config):
            if path.exists():
                path.unlink()
        return False


def _play_wav(path: str) -> bool:
    """Play a WAV file with whatever playback tool is available."""
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


def _speak_via_package(text: str, voice: str, onnx: Path, config: Path) -> bool:
    try:
        if voice not in _loaded_voices:
            _loaded_voices[voice] = _PiperVoice.load(str(onnx), str(config))
        piper_voice = _loaded_voices[voice]

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            with wave.open(tmp.name, "wb") as wav_file:
                piper_voice.synthesize_wav(text, wav_file)
            if os.path.getsize(tmp.name) <= 44:
                return False
            return _play_wav(tmp.name)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
    except Exception as e:
        print(f"[Zeno] Piper (package) error: {e}")
        return False


def _speak_via_cli(text: str, onnx: Path, config: Path) -> bool:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    out_path = tmp.name
    try:
        proc = subprocess.run(
            [_PIPER_BIN, "--model", str(onnx), "--config", str(config),
             "--output_file", out_path],
            input=text.encode(),
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) <= 44:
            return False
        return _play_wav(out_path)
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"[Zeno] Piper (CLI) error: {e}")
        return False
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def speak(text: str, voice: str = _DEFAULT_VOICE) -> bool:
    """Synthesize `text` with Piper and play it. Returns False (rather than
    raising) on any failure so callers can fall back to platform TTS."""
    onnx, config = _voice_paths(voice)
    if not (onnx.exists() and config.exists()):
        return False

    if _PiperVoice is not None:
        if _speak_via_package(text, voice, onnx, config):
            return True
        # Package path failed for some reason (bad model file, playback
        # tool missing) — try the CLI binary if it's also present before
        # giving up entirely.
    if _PIPER_BIN is not None:
        return _speak_via_cli(text, onnx, config)
    return False
