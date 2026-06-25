"""
Zeno Platform — Windows Provider (PowerShell + Cmd)
Uses PowerShell for TTS, notifications, volume, and app launching.
Falls back to cmd.exe when PowerShell isn't available.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from zeno.platform.providers.base import PlatformProvider, PlatformCaps


def _has_powershell() -> bool:
    return shutil.which("powershell.exe") is not None


def _run_ps(script: str, timeout: int = 10) -> tuple[str | None, bool]:
    """Run a PowerShell script. Returns (stdout, success)."""
    exe = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not exe:
        return None, False
    try:
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=timeout,
        )
        out = result.stdout.decode(errors="replace").strip()
        return out, result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return None, False


class WindowsProvider(PlatformProvider):
    name = "windows"

    @property
    def caps(self) -> PlatformCaps:
        has_ps = _has_powershell()
        return PlatformCaps(
            tts=has_ps,
            stt=False,
            notification=True,
            volume=has_ps,
            brightness=has_ps,
            lock_screen=has_ps,
            open_app=True,
            toast=has_ps,
            vibrate=False,
            clipboard=has_ps,
        )

    def tts_speak(self, text: str) -> bool:
        if not self.caps.tts:
            return False
        escaped = text.replace("'", "''")
        script = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.Speak('{escaped}')
        """
        return _run_ps(script, timeout=30)[1]

    def stt_listen(self, timeout: int = 15) -> str | None:
        return None

    def show_notification(
        self, title: str, content: str,
        notification_id: str = "zeno", alert_once: bool = True,
    ) -> bool:
        if _has_powershell():
            esc_title = title.replace('"', '`"')
            esc_content = content.replace('"', '`"')
            script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{esc_title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{esc_content}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier().Show($toast)
            """
            success = _run_ps(script, timeout=10)[1]
            if success:
                return True

        try:
            subprocess.Popen(
                ["msg", "*", f"{title}: {content}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def set_volume(self, stream: str = "master", level: int = 50) -> bool:
        if not self.caps.volume:
            return False
        if not (0 <= level <= 100):
            return False
        script = f"""
        $obj = New-Object -ComObject Sapi.SpAudio
        $vol = $obj.Volume
        $vol.Volume = {level}
        """
        return _run_ps(script, timeout=5)[1]

    def set_brightness(self, level: int) -> bool:
        if not self.caps.brightness:
            return False
        if not (0 <= level <= 100):
            return False
        script = f"""
        $monitor = Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods
        if ($monitor) {{
            $monitor.WmiSetBrightness(1, {level})
        }}
        """
        return _run_ps(script, timeout=5)[1]

    def lock_screen(self) -> bool:
        try:
            subprocess.run(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                timeout=3,
            )
            return True
        except Exception:
            return False

    def open_app(self, app_id: str) -> bool:
        try:
            subprocess.run(
                ["cmd.exe", "/c", "start", "", app_id],
                capture_output=True, timeout=5,
            )
            return True
        except Exception:
            return False

    def show_toast(self, text: str, short: bool = True) -> bool:
        return self.show_notification("Zeno", text)

    def get_clipboard(self) -> str | None:
        out, ok = _run_ps("Get-Clipboard", timeout=5)
        return out if ok else None

    def set_clipboard(self, text: str) -> bool:
        escaped = text.replace("'", "''")
        return _run_ps(f"Set-Clipboard -Value '{escaped}'", timeout=5)[1]
