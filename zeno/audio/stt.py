"""
Zeno Speech-to-Text
Uses the platform provider for STT, falls back to stdin.
"""

import sys
from zeno.platform import stt_listen, caps


def listen(timeout: int = 15) -> str | None:
    if caps().stt:
        return stt_listen(timeout=timeout)
    print("[Press Enter after speaking, or type your command]")
    sys.stdout.flush()
    try:
        return sys.stdin.readline().strip()
    except (EOFError, KeyboardInterrupt):
        return None
