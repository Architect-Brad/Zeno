"""
Zeno Platform — Base Provider
All platform providers inherit from this.
Every method has a default no-op fallback.
"""

from dataclasses import dataclass, field


@dataclass
class PlatformCaps:
    tts: bool = False
    stt: bool = False
    notification: bool = False
    volume: bool = False
    brightness: bool = False
    lock_screen: bool = False
    open_app: bool = False
    toast: bool = False
    vibrate: bool = False
    clipboard: bool = False
    battery: bool = False
    torch: bool = False
    sms: bool = False
    call: bool = False

    @property
    def any_audio_out(self) -> bool:
        return self.tts

    @property
    def any_audio_in(self) -> bool:
        return self.stt

    @property
    def any_output(self) -> bool:
        return self.tts or self.notification or self.toast


class PlatformProvider:
    name = "base"

    @property
    def caps(self) -> PlatformCaps:
        return PlatformCaps()

    def tts_speak(self, text: str) -> bool:
        return False

    def stt_listen(self, timeout: int = 15) -> str | None:
        return None

    def show_notification(
        self, title: str, content: str,
        notification_id: str = "zeno", alert_once: bool = True,
    ) -> bool:
        return False

    def set_volume(self, stream: str = "master", level: int = 50) -> bool:
        return False

    def set_brightness(self, level: int) -> bool:
        return False

    def lock_screen(self) -> bool:
        return False

    def open_app(self, app_id: str) -> bool:
        return False

    def show_toast(self, text: str, short: bool = True) -> bool:
        return False

    def vibrate(self, duration_ms: int = 200) -> bool:
        return False

    def get_clipboard(self) -> str | None:
        return None

    def set_clipboard(self, text: str) -> bool:
        return False

    def battery_status(self) -> dict | None:
        """Return {'percentage': int, 'plugged': bool, 'status': str} or None."""
        return None

    def set_torch(self, on: bool) -> bool:
        return False

    def send_sms(self, number: str, message: str) -> bool:
        return False

    def make_call(self, number: str) -> bool:
        return False
