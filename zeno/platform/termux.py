"""
Zeno Platform — Legacy Termux compatibility shim.
Redirects to the new cross-platform zeno.platform module.
"""
from zeno.platform import (
    caps, tts_speak, stt_listen, show_notification,
    set_volume, set_brightness, show_toast, vibrate,
    get_provider, detect_platform,
)
from zeno.platform.providers.termux import TermuxProvider

__all__ = [
    "caps", "tts_speak", "stt_listen", "show_notification",
    "set_volume", "set_brightness", "show_toast", "vibrate",
    "get_provider", "detect_platform", "TermuxProvider",
]
