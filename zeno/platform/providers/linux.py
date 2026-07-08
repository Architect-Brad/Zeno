"""
Zeno Platform — Linux Desktop Provider
Uses espeak-ng/spd-say for TTS, notify-send for notifications,
pactl/amixer for volume, xdg-open for apps.
"""

import os
import shutil
import subprocess
import re
from pathlib import Path
from zeno.platform.providers.base import PlatformProvider, PlatformCaps


def _which(*names: str) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


class LinuxProvider(PlatformProvider):
    name = "linux"

    @property
    def caps(self) -> PlatformCaps:
        return PlatformCaps(
            tts=_which("espeak-ng", "espeak", "spd-say", "festival") is not None,
            stt=self._can_stt(),
            notification=_which("notify-send", "zenity", "kdialog") is not None,
            volume=_which("pactl", "amixer", "pulsemixer") is not None,
            brightness=_which("brightnessctl", "xbacklight", "xrandr") is not None,
            lock_screen=_which("xdg-screensaver", "gnome-screensaver-command") is not None,
            open_app=_which("xdg-open", "gtk-launch") is not None,
            toast=False,
            vibrate=False,
            clipboard=_which("xclip", "wl-copy", "xsel") is not None,
        )

    def _can_stt(self) -> bool:
        """STT is available if PipeWire capture + whisper binary are present."""
        pw = shutil.which("pw-record") or shutil.which("pw-cat")
        whisper = shutil.which("whisper-cli") or shutil.which("whisper")
        return pw is not None and whisper is not None

    def stt_listen(self, timeout: int = 15) -> str | None:
        """Record audio via PipeWire and transcribe with whisper.cpp."""
        if not self.caps.stt:
            return None
        try:
            from zeno.audio.whisper_stt import listen as whisper_listen
            text = whisper_listen(timeout=timeout)
            if text:
                return text
            # Fallback: try with language detection
            return whisper_listen(timeout=timeout, language="en")
        except Exception as e:
            print(f"[Zeno] STT error: {e}")
            return None

    def tts_speak(self, text: str) -> bool:
        if not self.caps.tts:
            return False
        espeak = _which("espeak-ng", "espeak")
        if espeak:
            try:
                subprocess.Popen(
                    [espeak, text],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
        spd = shutil.which("spd-say")
        if spd:
            try:
                subprocess.Popen(
                    [spd, "-t", "female1", text],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
        festival = shutil.which("festival")
        if festival:
            try:
                proc = subprocess.Popen(
                    [festival],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                proc.stdin.write(f"(SayText \"{text}\")\n".encode())
                proc.stdin.close()
                return True
            except Exception:
                pass
        return False

    def show_notification(
        self, title: str, content: str,
        notification_id: str = "zeno", alert_once: bool = True,
    ) -> bool:
        notify = shutil.which("notify-send")
        if notify:
            try:
                subprocess.Popen(
                    [notify, "-a", "Zeno", title, content],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
        zenity = shutil.which("zenity")
        if zenity:
            try:
                subprocess.Popen(
                    [zenity, "--notification", "--text", f"{title}: {content}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
        return False

    def set_volume(self, stream: str = "master", level: int = 50) -> bool:
        if not self.caps.volume:
            return False
        if not (0 <= level <= 100):
            return False
        pactl = shutil.which("pactl")
        if pactl:
            sink = "@DEFAULT_SINK@"
            try:
                vol_pct = f"{level}%"
                subprocess.run(
                    [pactl, "set-sink-volume", sink, vol_pct],
                    capture_output=True, timeout=3,
                )
                return True
            except Exception:
                pass
        amixer = shutil.which("amixer")
        if amixer:
            try:
                subprocess.run(
                    [amixer, "set", stream, f"{level}%"],
                    capture_output=True, timeout=3,
                )
                return True
            except Exception:
                pass
        return False

    def set_brightness(self, level: int) -> bool:
        if not self.caps.brightness:
            return False
        if not (0 <= level <= 100):
            return False
        bc = shutil.which("brightnessctl")
        if bc:
            try:
                subprocess.run(
                    [bc, "set", f"{level}%"],
                    capture_output=True, timeout=3,
                )
                return True
            except Exception:
                pass
        xb = shutil.which("xbacklight")
        if xb:
            try:
                subprocess.run(
                    [xb, "-set", str(level)],
                    capture_output=True, timeout=3,
                )
                return True
            except Exception:
                pass
        return False

    def lock_screen(self) -> bool:
        ss = shutil.which("xdg-screensaver")
        if ss:
            try:
                subprocess.run(
                    [ss, "lock"],
                    capture_output=True, timeout=3,
                )
                return True
            except Exception:
                pass
        gs = shutil.which("gnome-screensaver-command")
        if gs:
            try:
                subprocess.run(
                    [gs, "-l"],
                    capture_output=True, timeout=3,
                )
                return True
            except Exception:
                pass
        try:
            subprocess.run(
                ["loginctl", "lock-session"],
                capture_output=True, timeout=3,
            )
            return True
        except Exception:
            pass
        return False

    def open_app(self, app_id: str) -> bool:
        xdg = shutil.which("xdg-open")
        if xdg:
            try:
                subprocess.Popen(
                    [xdg, app_id],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
        return False

    def get_clipboard(self) -> str | None:
        xclip = shutil.which("xclip")
        if xclip:
            try:
                result = subprocess.run(
                    [xclip, "-o", "-selection", "clipboard"],
                    capture_output=True, timeout=3,
                )
                return result.stdout.decode().strip() or None
            except Exception:
                pass
        wl = shutil.which("wl-copy")
        if wl:
            try:
                result = subprocess.run(
                    [shutil.which("wl-paste")],
                    capture_output=True, timeout=3,
                )
                return result.stdout.decode().strip() or None
            except Exception:
                pass
        return None

    def set_clipboard(self, text: str) -> bool:
        xclip = shutil.which("xclip")
        if xclip:
            try:
                proc = subprocess.Popen(
                    [xclip, "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                proc.stdin.write(text.encode())
                proc.stdin.close()
                proc.wait(timeout=3)
                return True
            except Exception:
                pass
        wl = shutil.which("wl-copy")
        if wl:
            try:
                proc = subprocess.Popen(
                    [wl],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                proc.stdin.write(text.encode())
                proc.stdin.close()
                proc.wait(timeout=3)
                return True
            except Exception:
                pass
        return False
