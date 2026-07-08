"""
Zeno Platform — Termux/Android Provider
Uses termux-* binaries for device control, TTS, STT, and notifications.
"""

import shutil
import subprocess
import threading
from zeno.platform.providers.base import PlatformProvider, PlatformCaps


class TermuxProvider(PlatformProvider):
    name = "termux"

    @property
    def caps(self) -> PlatformCaps:
        return PlatformCaps(
            tts=shutil.which("termux-tts-speak") is not None,
            stt=shutil.which("termux-speech-to-text") is not None,
            notification=shutil.which("termux-notification") is not None,
            volume=shutil.which("termux-volume") is not None,
            brightness=shutil.which("termux-brightness") is not None,
            lock_screen=False,
            open_app=True,
            toast=shutil.which("termux-toast") is not None,
            vibrate=shutil.which("termux-vibrate") is not None,
            clipboard=shutil.which("termux-clipboard-get") is not None,
            battery=shutil.which("termux-battery-status") is not None,
            torch=shutil.which("termux-torch") is not None,
            sms=shutil.which("termux-sms-send") is not None,
            call=shutil.which("termux-telephony-call") is not None,
        )

    def tts_speak(self, text: str) -> bool:
        if not self.caps.tts:
            return False
        try:
            proc = subprocess.Popen(
                ["termux-tts-speak"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.stdin.write(text.encode())
            proc.stdin.close()
            threading.Thread(target=proc.wait, daemon=True).start()
            return True
        except Exception:
            return False

    def stt_listen(self, timeout: int = 15) -> str | None:
        if not self.caps.stt:
            return None
        try:
            result = subprocess.run(
                ["termux-speech-to-text"],
                capture_output=True, timeout=timeout,
            )
            text = result.stdout.decode().strip()
            return text if text else None
        except (subprocess.TimeoutExpired, Exception):
            return None

    def show_notification(
        self, title: str, content: str,
        notification_id: str = "zeno", alert_once: bool = True,
    ) -> bool:
        if not self.caps.notification:
            return False
        try:
            cmd = [
                "termux-notification",
                "-i", notification_id,
                "--title", title,
                "--content", content,
            ]
            if alert_once:
                cmd.append("--alert-once")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def set_volume(self, stream: str = "music", level: int = 50) -> bool:
        if not self.caps.volume:
            return False
        if not (0 <= level <= 100):
            return False
        termux_vol = max(0, min(15, level * 15 // 100))
        try:
            subprocess.run(
                ["termux-volume", stream, str(termux_vol)],
                capture_output=True, timeout=3,
            )
            return True
        except Exception:
            return False

    def set_brightness(self, level: int) -> bool:
        if not self.caps.brightness:
            return False
        if not (0 <= level <= 100):
            return False
        android_val = max(0, min(255, level * 255 // 100))
        try:
            subprocess.run(
                ["termux-brightness", str(android_val)],
                capture_output=True, timeout=3,
            )
            return True
        except Exception:
            return False

    def open_app(self, app_id: str) -> bool:
        try:
            subprocess.run(
                ["am", "start", "-n", app_id],
                capture_output=True, timeout=5,
            )
            return True
        except Exception:
            return False

    def show_toast(self, text: str, short: bool = True) -> bool:
        if not self.caps.toast:
            return False
        try:
            cmd = ["termux-toast", "-b", "center", text]
            if short:
                cmd.insert(1, "-s")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def vibrate(self, duration_ms: int = 200) -> bool:
        if not self.caps.vibrate:
            return False
        try:
            subprocess.Popen(
                ["termux-vibrate", "-d", str(duration_ms)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def get_clipboard(self) -> str | None:
        if not self.caps.clipboard:
            return None
        try:
            result = subprocess.run(
                ["termux-clipboard-get"],
                capture_output=True, timeout=3,
            )
            return result.stdout.decode().strip() or None
        except Exception:
            return None

    def set_clipboard(self, text: str) -> bool:
        try:
            proc = subprocess.Popen(
                ["termux-clipboard-set"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            proc.stdin.write(text.encode())
            proc.stdin.close()
            proc.wait(timeout=3)
            return True
        except Exception:
            return False

    def battery_status(self) -> dict | None:
        if not self.caps.battery:
            return None
        try:
            import json
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True, timeout=5,
            )
            data = json.loads(result.stdout.decode())
            # termux-battery-status returns e.g.
            # {"health": "GOOD", "percentage": 87, "plugged": "UNPLUGGED",
            #  "status": "DISCHARGING", "temperature": 28.6, "current": -123}
            return {
                "percentage": data.get("percentage"),
                "plugged": data.get("plugged", "UNPLUGGED") != "UNPLUGGED",
                "status": str(data.get("status", "UNKNOWN")).lower(),
            }
        except Exception:
            return None

    def set_torch(self, on: bool) -> bool:
        if not self.caps.torch:
            return False
        try:
            subprocess.run(
                ["termux-torch", "on" if on else "off"],
                capture_output=True, timeout=3,
            )
            return True
        except Exception:
            return False

    def send_sms(self, number: str, message: str) -> bool:
        """Send a real SMS via termux-sms-send. This has a real-world
        effect (cost, delivery to a real recipient) — callers should
        confirm with the user before invoking this, not just before
        showing this capability exists."""
        if not self.caps.sms:
            return False
        try:
            result = subprocess.run(
                ["termux-sms-send", "-n", number, message],
                capture_output=True, timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False

    def make_call(self, number: str) -> bool:
        """Place a real phone call via termux-telephony-call. Like
        send_sms, this has an immediate real-world effect and should be
        confirmed with the user before being invoked, not just before
        being offered."""
        if not self.caps.call:
            return False
        try:
            result = subprocess.run(
                ["termux-telephony-call", number],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False
