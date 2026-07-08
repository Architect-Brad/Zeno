"""
Tests for Zeno Platform Providers — mock subprocess and shutil.
"""

from unittest.mock import patch, MagicMock, PropertyMock
import pytest


# ---------------------------------------------------------------------------
# Dummy Provider
# ---------------------------------------------------------------------------

class TestDummyProvider:
    def test_caps_all_false(self):
        from zeno.platform.providers.dummy import DummyProvider
        p = DummyProvider()
        c = p.caps
        assert c.tts is False
        assert c.stt is False
        assert c.notification is False
        assert c.volume is False
        assert c.brightness is False
        assert c.lock_screen is False
        assert c.open_app is False
        assert c.toast is False
        assert c.vibrate is False
        assert c.clipboard is False
        assert c.battery is False
        assert c.torch is False
        assert c.sms is False
        assert c.call is False

    def test_all_methods_return_false_or_none(self):
        from zeno.platform.providers.dummy import DummyProvider
        p = DummyProvider()
        assert p.tts_speak("hi") is False
        assert p.stt_listen() is None
        assert p.show_notification("t", "c") is False
        assert p.set_volume("master", 50) is False
        assert p.set_brightness(50) is False
        assert p.lock_screen() is False
        assert p.open_app("com.test") is False
        assert p.show_toast("hi") is False
        assert p.vibrate(200) is False
        assert p.get_clipboard() is None
        assert p.set_clipboard("hi") is False
        assert p.battery_status() is None
        assert p.set_torch(True) is False
        assert p.send_sms("+15551234567", "hi") is False
        assert p.make_call("+15551234567") is False


# ---------------------------------------------------------------------------
# Termux Provider
# ---------------------------------------------------------------------------

class TestTermuxProvider:
    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-tts-speak")
    def test_caps_with_binaries(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        c = p.caps
        # which returns non-None for all checks because mock always returns the path
        assert c.tts is True
        assert c.stt is True
        assert c.notification is True
        assert c.volume is True
        assert c.brightness is True
        assert c.toast is True
        assert c.vibrate is True
        assert c.clipboard is True

    @patch("shutil.which", return_value=None)
    def test_caps_without_binaries(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        c = p.caps
        assert c.tts is False
        assert c.stt is False
        assert c.volume is False

    @patch("shutil.which", return_value="/bin/termux-tts-speak")
    def test_tts_speak_success(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            mock_popen.return_value = proc
            result = p.tts_speak("hello world")
            assert result is True
            mock_popen.assert_called_once()
            args, _ = mock_popen.call_args
            assert "termux-tts-speak" in args[0]
            proc.stdin.write.assert_called_once_with(b"hello world")

    @patch("shutil.which", return_value=None)
    def test_tts_speak_no_caps(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.tts_speak("hi") is False

    @patch("shutil.which", return_value="/bin/termux-speech-to-text")
    def test_stt_listen_success(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"hello world\n", returncode=0)
            result = p.stt_listen(timeout=10)
            assert result == "hello world"
            mock_run.assert_called_once_with(
                ["termux-speech-to-text"],
                capture_output=True, timeout=10,
            )

    @patch("shutil.which", return_value="/bin/termux-speech-to-text")
    def test_stt_listen_timeout(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run", side_effect=TimeoutExpired("cmd", 5)):
            result = p.stt_listen(timeout=5)
            assert result is None

    @patch("shutil.which", return_value="/bin/termux-notification")
    def test_notification_success(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.show_notification("Test Title", "Test Content", "test-id")
            assert result is True
            args, _ = mock_popen.call_args
            assert "termux-notification" in args[0]
            assert "--title" in args[0]
            assert "Test Title" in args[0]
            assert "--alert-once" in args[0]

    @patch("shutil.which", return_value="/bin/termux-notification")
    def test_notification_no_alert_once(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.show_notification("T", "C", alert_once=False)
            assert result is True
            args, _ = mock_popen.call_args
            assert "--alert-once" not in args[0]

    @patch("shutil.which", return_value="/bin/termux-volume")
    def test_set_volume_success(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.set_volume("music", 50)
            assert result is True
            mock_run.assert_called_once_with(
                ["termux-volume", "music", "7"],  # 50 * 15 / 100 = 7
                capture_output=True, timeout=3,
            )

    @patch("shutil.which", return_value="/bin/termux-volume")
    def test_set_volume_invalid_level(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.set_volume("music", -1) is False
        assert p.set_volume("music", 101) is False

    @patch("shutil.which", return_value="/bin/termux-brightness")
    def test_set_brightness_success(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.set_brightness(50)
            assert result is True
            mock_run.assert_called_once_with(
                ["termux-brightness", "127"],  # 50 * 255 // 100 = 127
                capture_output=True, timeout=3,
            )

    @patch("shutil.which", return_value="/bin/termux-brightness")
    def test_set_brightness_invalid_level(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.set_brightness(-1) is False
        assert p.set_brightness(101) is False

    @patch("shutil.which", return_value="/system/bin/am")
    def test_open_app_success(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.open_app("com.test.app/.MainActivity")
            assert result is True
            mock_run.assert_called_once_with(
                ["am", "start", "-n", "com.test.app/.MainActivity"],
                capture_output=True, timeout=5,
            )

    @patch("shutil.which", return_value="/bin/termux-toast")
    def test_show_toast_short(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.show_toast("Hello", short=True)
            assert result is True
            args, _ = mock_popen.call_args
            assert args[0] == ["termux-toast", "-s", "-b", "center", "Hello"]

    @patch("shutil.which", return_value="/bin/termux-toast")
    def test_show_toast_long(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.show_toast("Hello", short=False)
            assert result is True
            args, _ = mock_popen.call_args
            assert "-s" not in args[0]

    @patch("shutil.which", return_value="/bin/termux-vibrate")
    def test_vibrate(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.vibrate(500)
            assert result is True
            args, _ = mock_popen.call_args
            assert "termux-vibrate" in args[0]
            assert "-d" in args[0]
            assert "500" in args[0]

    @patch("shutil.which", return_value="/bin/termux-clipboard-get")
    def test_get_clipboard(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"copied text\n", returncode=0)
            result = p.get_clipboard()
            assert result == "copied text"

    @patch("shutil.which", return_value="/bin/termux-clipboard-get")
    def test_get_clipboard_empty(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"  \n", returncode=0)
            result = p.get_clipboard()
            assert result is None

    @patch("shutil.which", return_value="/bin/termux-clipboard-set")
    def test_set_clipboard(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            mock_popen.return_value = proc
            result = p.set_clipboard("test data")
            assert result is True
            proc.stdin.write.assert_called_once_with(b"test data")
            proc.wait.assert_called_once_with(timeout=3)

    def test_lock_screen_always_false(self):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.lock_screen() is False


# ---------------------------------------------------------------------------
# Linux Provider
# ---------------------------------------------------------------------------

class TestLinuxProvider:
    @patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}" if x in ("espeak-ng", "notify-send", "pactl", "brightnessctl", "xdg-screensaver", "xdg-open", "xclip") else None)
    def test_caps_with_binaries(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        c = p.caps
        assert c.tts is True
        assert c.stt is False
        assert c.notification is True
        assert c.volume is True
        assert c.brightness is True
        assert c.lock_screen is True
        assert c.open_app is True
        assert c.toast is False
        assert c.vibrate is False
        assert c.clipboard is True

    @patch("shutil.which", return_value=None)
    def test_caps_no_binaries(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        c = p.caps
        assert c.tts is False
        assert c.stt is False

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/espeak-ng" if x == "espeak-ng" else None)
    def test_tts_espeak(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.tts_speak("hello")
            assert result is True
            mock_popen.assert_called_once_with(
                ["/usr/bin/espeak-ng", "hello"],
                stdout=-3, stderr=-3,  # DEVNULL
            )

    @patch("shutil.which", return_value=None)
    def test_tts_no_engine(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        result = p.tts_speak("hello")
        assert result is False

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/notify-send" if x == "notify-send" else None)
    def test_notification_notify_send(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.Popen") as mock_popen:
            result = p.show_notification("Title", "Body")
            assert result is True
            args, _ = mock_popen.call_args
            assert args[0][0] == "/usr/bin/notify-send"
            assert "Title" in args[0]
            assert "Body" in args[0]

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/pactl" if x == "pactl" else None)
    def test_set_volume_pactl(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.set_volume("master", 75)
            assert result is True
            mock_run.assert_called_once_with(
                ["/usr/bin/pactl", "set-sink-volume", "@DEFAULT_SINK@", "75%"],
                capture_output=True, timeout=3,
            )

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/brightnessctl" if x == "brightnessctl" else None)
    def test_set_brightness(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.set_brightness(60)
            assert result is True
            mock_run.assert_called_once_with(
                ["/usr/bin/brightnessctl", "set", "60%"],
                capture_output=True, timeout=3,
            )

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/xdg-screensaver" if x == "xdg-screensaver" else None)
    def test_lock_screen(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.lock_screen()
            assert result is True
            mock_run.assert_called_once_with(
                ["/usr/bin/xdg-screensaver", "lock"],
                capture_output=True, timeout=3,
            )

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/loginctl" if x == "loginctl" else None)
    def test_lock_screen_loginctl_fallback(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.lock_screen()
            assert result is True
            mock_run.assert_called_once_with(
                ["loginctl", "lock-session"],
                capture_output=True, timeout=3,
            )

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/xclip" if x == "xclip" else None)
    def test_get_clipboard(self, mock_which):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"clip data\n", returncode=0)
            result = p.get_clipboard()
            assert result == "clip data"

    def test_set_volume_invalid_level(self):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        assert p.set_volume("master", -1) is False
        assert p.set_volume("master", 101) is False

    def test_set_brightness_invalid_level(self):
        from zeno.platform.providers.linux import LinuxProvider
        p = LinuxProvider()
        assert p.set_brightness(-1) is False
        assert p.set_brightness(101) is False


# ---------------------------------------------------------------------------
# Windows Provider
# ---------------------------------------------------------------------------

class TestWindowsProvider:
    @patch("shutil.which", side_effect=lambda x: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" if x in ("powershell.exe", "pwsh") else None)
    def test_caps_with_powershell(self, mock_which):
        from zeno.platform.providers.windows import WindowsProvider
        p = WindowsProvider()
        c = p.caps
        assert c.tts is True
        assert c.stt is False
        assert c.notification is True
        assert c.volume is True
        assert c.brightness is True
        assert c.lock_screen is True
        assert c.open_app is True
        assert c.toast is True

    @patch("shutil.which", return_value=None)
    def test_caps_no_powershell(self, mock_which):
        from zeno.platform.providers.windows import WindowsProvider
        p = WindowsProvider()
        c = p.caps
        assert c.tts is False
        assert c.stt is False
        assert c.notification is True  # can fall back to msg.exe
        assert c.volume is False
        assert c.brightness is False
        assert c.lock_screen is False

    @patch("shutil.which", side_effect=lambda x: "powershell.exe" if x in ("powershell.exe", "pwsh") else None)
    def test_tts_speak(self, mock_which):
        from zeno.platform.providers.windows import WindowsProvider
        p = WindowsProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"", returncode=0)
            result = p.tts_speak("hello world")
            assert result is True
            # Verify PowerShell was called with Speech synthesis
            args, _ = mock_run.call_args
            assert "powershell.exe" in str(args[0])
            assert "SpeechSynthesizer" in str(args[0][-1])

    @patch("shutil.which", side_effect=lambda x: "powershell.exe" if x in ("powershell.exe", "pwsh") else None)
    def test_set_volume(self, mock_which):
        from zeno.platform.providers.windows import WindowsProvider
        p = WindowsProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"", returncode=0)
            result = p.set_volume("master", 50)
            assert result is True
            args, _ = mock_run.call_args
            assert "Sapi.SpAudio" in args[0][-1]

    @patch("shutil.which", side_effect=lambda x: "powershell.exe" if x in ("powershell.exe", "pwsh") else None)
    def test_lock_screen(self, mock_which):
        from zeno.platform.providers.windows import WindowsProvider
        p = WindowsProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.lock_screen()
            assert result is True
            args, _ = mock_run.call_args
            assert "rundll32.exe" in str(args[0])

    @patch("shutil.which", side_effect=lambda x: "powershell.exe" if x in ("powershell.exe", "pwsh") else None)
    def test_get_clipboard(self, mock_which):
        from zeno.platform.providers.windows import WindowsProvider
        p = WindowsProvider()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"clip text\n", returncode=0)
            result = p.get_clipboard()
            assert result == "clip text"


# ---------------------------------------------------------------------------
# Platform Detection
# ---------------------------------------------------------------------------

class TestPlatformDetection:
    @patch("shutil.which", return_value="/bin/termux-tts-speak")
    @patch.dict("os.environ", {"TERMUX_VERSION": "0.118.0"})
    @patch("platform.system", return_value="Android")
    def test_detect_termux(self, mock_system, mock_which):
        from zeno.platform import detect_platform
        assert detect_platform() == "termux"

    @patch("shutil.which", return_value="/usr/bin/notify-send")
    @patch.dict("os.environ", {}, clear=True)
    @patch("platform.system", return_value="Linux")
    def test_detect_linux(self, mock_system, mock_which):
        from zeno.platform import detect_platform
        assert detect_platform() == "linux"

    @patch("platform.system", return_value="Windows")
    @patch("shutil.which", side_effect=lambda x: "powershell.exe" if x in ("powershell.exe", "pwsh") else None)
    def test_detect_windows(self, mock_which, mock_system):
        from zeno.platform import detect_platform
        assert detect_platform() == "windows"

    @patch("platform.system", return_value="SomethingUnknown")
    @patch("shutil.which", return_value=None)
    def test_detect_fallback(self, mock_which, mock_system):
        from zeno.platform import detect_platform
        assert detect_platform() == "dummy"

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-battery-status")
    @patch("subprocess.run")
    def test_battery_status_success(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        mock_run.return_value = MagicMock(
            stdout=b'{"health": "GOOD", "percentage": 87, '
                   b'"plugged": "UNPLUGGED", "status": "DISCHARGING"}'
        )
        p = TermuxProvider()
        status = p.battery_status()
        assert status == {"percentage": 87, "plugged": False, "status": "discharging"}

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-battery-status")
    @patch("subprocess.run")
    def test_battery_status_charging(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        mock_run.return_value = MagicMock(
            stdout=b'{"percentage": 42, "plugged": "AC", "status": "CHARGING"}'
        )
        p = TermuxProvider()
        status = p.battery_status()
        assert status["plugged"] is True
        assert status["percentage"] == 42

    @patch("shutil.which", return_value=None)
    def test_battery_status_unavailable(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.battery_status() is None

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-battery-status")
    @patch("subprocess.run", side_effect=Exception("boom"))
    def test_battery_status_handles_errors(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.battery_status() is None

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-torch")
    @patch("subprocess.run")
    def test_set_torch_on(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.set_torch(True) is True
        args = mock_run.call_args[0][0]
        assert args == ["termux-torch", "on"]

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-torch")
    @patch("subprocess.run")
    def test_set_torch_off(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.set_torch(False) is True
        args = mock_run.call_args[0][0]
        assert args == ["termux-torch", "off"]

    @patch("shutil.which", return_value=None)
    def test_set_torch_unavailable(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.set_torch(True) is False

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-sms-send")
    @patch("subprocess.run")
    def test_send_sms_success(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        mock_run.return_value = MagicMock(returncode=0)
        p = TermuxProvider()
        assert p.send_sms("+15551234567", "hello") is True
        args = mock_run.call_args[0][0]
        assert args == ["termux-sms-send", "-n", "+15551234567", "hello"]

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-sms-send")
    @patch("subprocess.run")
    def test_send_sms_failure_returncode(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        mock_run.return_value = MagicMock(returncode=1)
        p = TermuxProvider()
        assert p.send_sms("+15551234567", "hello") is False

    @patch("shutil.which", return_value=None)
    def test_send_sms_unavailable(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.send_sms("+15551234567", "hello") is False

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-telephony-call")
    @patch("subprocess.run")
    def test_make_call_success(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        mock_run.return_value = MagicMock(returncode=0)
        p = TermuxProvider()
        assert p.make_call("+15551234567") is True
        args = mock_run.call_args[0][0]
        assert args == ["termux-telephony-call", "+15551234567"]

    @patch("shutil.which", return_value="/data/data/com.termux/files/usr/bin/termux-telephony-call")
    @patch("subprocess.run", side_effect=Exception("boom"))
    def test_make_call_handles_errors(self, mock_run, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.make_call("+15551234567") is False

    @patch("shutil.which", return_value=None)
    def test_make_call_unavailable(self, mock_which):
        from zeno.platform.providers.termux import TermuxProvider
        p = TermuxProvider()
        assert p.make_call("+15551234567") is False


# ---------------------------------------------------------------------------
# Platform Top-Level Functions
# ---------------------------------------------------------------------------

class TestPlatformFunctions:
    def test_get_provider_caching(self):
        from zeno.platform import get_provider, _provider
        # Reset singleton
        import zeno.platform
        zeno.platform._provider = None

        with patch("zeno.platform.detect_platform", return_value="dummy"):
            p1 = get_provider()
            p2 = get_provider()
            assert p1 is p2  # Same instance cached

    def test_caps_delegation(self):
        from zeno.platform import caps
        with patch("zeno.platform.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.caps.tts = True
            mock_get.return_value = mock_provider
            c = caps()
            assert c.tts is True


# Need to import TimeoutExpired for tests
try:
    from subprocess import TimeoutExpired
except ImportError:
    class TimeoutExpired(Exception):
        pass
