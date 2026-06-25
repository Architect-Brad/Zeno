"""
Zeno Platform — Cross-Platform Abstraction Layer
Auto-detects OS and selects the best available provider.
Exposes a unified API for TTS, STT, notifications, system control, etc.
"""

import os
import platform as _platform
import shutil
from zeno.platform.providers.base import PlatformProvider, PlatformCaps


def detect_platform() -> str:
    """Detect the current platform and return a provider name."""
    system = _platform.system().lower()

    # Termux / Android
    if system == "android" or os.environ.get("TERMUX_VERSION"):
        if shutil.which("termux-tts-speak"):
            return "termux"

    # Windows
    if system == "windows":
        if shutil.which("powershell.exe") or shutil.which("pwsh"):
            return "windows"
        if shutil.which("cmd.exe"):
            return "windows"

    # Linux (including WSL)
    if system == "linux":
        # Detect WSL
        if "microsoft" in _platform.uname().release.lower():
            return "linux"
        # Desktop Linux with common tools
        if shutil.which("notify-send") or shutil.which("espeak") or shutil.which("pactl"):
            return "linux"
        return "linux"

    # macOS (treat as linux-capable via say command)
    if system == "darwin":
        return "linux"

    # Fallback
    return "dummy"


def _load_provider(name: str) -> PlatformProvider:
    if name == "termux":
        from zeno.platform.providers.termux import TermuxProvider
        return TermuxProvider()
    if name == "windows":
        from zeno.platform.providers.windows import WindowsProvider
        return WindowsProvider()
    if name == "linux":
        from zeno.platform.providers.linux import LinuxProvider
        return LinuxProvider()
    from zeno.platform.providers.dummy import DummyProvider
    return DummyProvider()


# Module-level singleton
_provider: PlatformProvider | None = None


def get_provider() -> PlatformProvider:
    global _provider
    if _provider is None:
        platform_name = detect_platform()
        _provider = _load_provider(platform_name)
    return _provider


def caps() -> PlatformCaps:
    return get_provider().caps


def tts_speak(text: str) -> bool:
    return get_provider().tts_speak(text)


def stt_listen(timeout: int = 15) -> str | None:
    return get_provider().stt_listen(timeout)


def show_notification(
    title: str, content: str,
    notification_id: str = "zeno", alert_once: bool = True,
) -> bool:
    return get_provider().show_notification(title, content, notification_id, alert_once)


def set_volume(stream: str = "master", level: int = 50) -> bool:
    return get_provider().set_volume(stream, level)


def set_brightness(level: int) -> bool:
    return get_provider().set_brightness(level)


def lock_screen() -> bool:
    return get_provider().lock_screen()


def open_app(app_id: str) -> bool:
    return get_provider().open_app(app_id)


def show_toast(text: str, short: bool = True) -> bool:
    return get_provider().show_toast(text, short)


def vibrate(duration_ms: int = 200) -> bool:
    return get_provider().vibrate(duration_ms)


def get_clipboard() -> str | None:
    return get_provider().get_clipboard()


def set_clipboard(text: str) -> bool:
    return get_provider().set_clipboard(text)
