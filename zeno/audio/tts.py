"""
Zeno Text-to-Speech
Uses the platform provider for TTS, falls back to print.
"""

import sys
from zeno.platform import tts_speak, caps


def speak(text: str) -> bool:
    if caps().tts:
        return tts_speak(text)
    print(f"[Zeno] {text}")
    sys.stdout.flush()
    return True
