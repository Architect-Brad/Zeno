"""
Zeno Text-to-Speech
Tries local engines first (best quality to most portable), falling back
to the platform provider's native TTS, then to printing the text.

Default order: Kokoro-82M (highest quality, biggest download) -> Piper
(natural-sounding, small, cross-platform) -> platform-native (espeak-ng,
termux-tts-speak, etc.) -> print.

Override with the ZENO_TTS_ENGINE env var: "kokoro", "piper", "platform",
or "auto" (default). An engine that's installed but not yet ready (no
voice/model downloaded) is skipped rather than erroring.
"""

import os
import sys
from zeno.platform import tts_speak, caps
from zeno.audio import piper_tts, kokoro_tts

_ENGINES = ("kokoro", "piper")  # tried in this order under "auto"


def _try_kokoro(text: str) -> bool:
    return kokoro_tts.is_available() and kokoro_tts.is_model_downloaded() and kokoro_tts.speak(text)


def _try_piper(text: str) -> bool:
    return piper_tts.is_available() and piper_tts.is_voice_downloaded() and piper_tts.speak(text)


_ENGINE_FUNCS = {"kokoro": _try_kokoro, "piper": _try_piper}


def speak(text: str) -> bool:
    requested = os.environ.get("ZENO_TTS_ENGINE", "auto").lower()

    if requested in _ENGINE_FUNCS:
        order = [requested]
    elif requested == "platform":
        order = []
    else:
        order = list(_ENGINES)  # "auto" or anything unrecognized

    for name in order:
        if _ENGINE_FUNCS[name](text):
            return True
        # That engine is installed but failed for this utterance (bad
        # model, playback tool missing, etc.) — try the next one rather
        # than silently dropping the response.

    if caps().tts:
        return tts_speak(text)
    print(f"[Zeno] {text}")
    sys.stdout.flush()
    return True
