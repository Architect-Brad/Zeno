"""
Zeno Speech-to-Text
Tries local engines first, falling back to the platform provider's
native STT, then to a stdin prompt.

Default order: faster-whisper (best accuracy, desktop only) -> whisper.cpp
(cross-platform, lighter) -> platform-native -> stdin.

Override with the ZENO_STT_ENGINE env var: "faster_whisper", "whisper_cpp",
"platform", or "auto" (default). An engine that's installed but not yet
ready (no model downloaded) is skipped rather than erroring.
"""

import os
import sys
from zeno.platform import stt_listen, caps
from zeno.audio import whisper_stt, faster_whisper_stt

_ENGINES = ("faster_whisper", "whisper_cpp")  # tried in this order under "auto"


def _try_faster_whisper(timeout: int) -> str | None:
    if faster_whisper_stt.is_available() and faster_whisper_stt.is_model_downloaded():
        return faster_whisper_stt.listen(timeout=timeout)
    return None


def _try_whisper_cpp(timeout: int) -> str | None:
    if whisper_stt.is_available() and whisper_stt.is_model_downloaded():
        return whisper_stt.listen(timeout=timeout)
    return None


_ENGINE_FUNCS = {"faster_whisper": _try_faster_whisper, "whisper_cpp": _try_whisper_cpp}


def listen(timeout: int = 15) -> str | None:
    requested = os.environ.get("ZENO_STT_ENGINE", "auto").lower()

    if requested in _ENGINE_FUNCS:
        order = [requested]
    elif requested == "platform":
        order = []
    else:
        order = list(_ENGINES)  # "auto" or anything unrecognized

    for name in order:
        text = _ENGINE_FUNCS[name](timeout)
        if text:
            return text
        # That engine is set up but this attempt produced nothing (no
        # mic, silence, capture failure) — try the next one.

    if caps().stt:
        return stt_listen(timeout=timeout)
    print("[Press Enter after speaking, or type your command]")
    sys.stdout.flush()
    try:
        return sys.stdin.readline().strip()
    except (EOFError, KeyboardInterrupt):
        return None
