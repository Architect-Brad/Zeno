"""Tests for the optional local voice engines: Piper TTS and whisper.cpp STT."""

import os
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Piper TTS
# ---------------------------------------------------------------------------

def test_piper_unavailable_when_neither_backend_present():
    with patch("zeno.audio.piper_tts._PIPER_BIN", None), \
         patch("zeno.audio.piper_tts._PiperVoice", None):
        from zeno.audio import piper_tts
        assert piper_tts.is_available() is False


def test_piper_available_via_cli_binary():
    with patch("zeno.audio.piper_tts._PIPER_BIN", "/usr/bin/piper"), \
         patch("zeno.audio.piper_tts._PiperVoice", None):
        from zeno.audio import piper_tts
        assert piper_tts.is_available() is True


def test_piper_available_via_pip_package():
    with patch("zeno.audio.piper_tts._PIPER_BIN", None), \
         patch("zeno.audio.piper_tts._PiperVoice", MagicMock()):
        from zeno.audio import piper_tts
        assert piper_tts.is_available() is True


def test_voice_downloaded_false_when_files_missing(tmp_path):
    from zeno.audio import piper_tts
    with patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path):
        assert piper_tts.is_voice_downloaded("en_US-lessac-medium") is False


def test_voice_downloaded_true_when_both_files_present(tmp_path):
    from zeno.audio import piper_tts
    (tmp_path / "en_US-lessac-medium.onnx").write_bytes(b"fake")
    (tmp_path / "en_US-lessac-medium.onnx.json").write_text("{}")
    with patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path):
        assert piper_tts.is_voice_downloaded("en_US-lessac-medium") is True


def test_list_voices_requires_both_files(tmp_path):
    from zeno.audio import piper_tts
    (tmp_path / "complete-voice.onnx").write_bytes(b"x")
    (tmp_path / "complete-voice.onnx.json").write_text("{}")
    (tmp_path / "incomplete-voice.onnx").write_bytes(b"x")  # missing .json
    with patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path):
        voices = piper_tts.list_voices()
    assert voices == ["complete-voice"]


def test_download_voice_rejects_malformed_name():
    from zeno.audio import piper_tts
    assert piper_tts.download_voice("not-a-valid-voice-name-format-here") is False


def test_speak_returns_false_when_no_backend_available(tmp_path):
    from zeno.audio import piper_tts
    (tmp_path / "en_US-lessac-medium.onnx").write_bytes(b"fake")
    (tmp_path / "en_US-lessac-medium.onnx.json").write_text("{}")
    with patch("zeno.audio.piper_tts._PIPER_BIN", None), \
         patch("zeno.audio.piper_tts._PiperVoice", None), \
         patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path):
        assert piper_tts.speak("hello") is False


def test_speak_returns_false_when_voice_not_downloaded(tmp_path):
    from zeno.audio import piper_tts
    with patch("zeno.audio.piper_tts._PIPER_BIN", "/usr/bin/piper"), \
         patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path):
        assert piper_tts.speak("hello") is False


def test_speak_prefers_pip_package_over_cli(tmp_path):
    from zeno.audio import piper_tts
    (tmp_path / "en_US-lessac-medium.onnx").write_bytes(b"fake")
    (tmp_path / "en_US-lessac-medium.onnx.json").write_text("{}")

    with patch("zeno.audio.piper_tts._PIPER_BIN", "/usr/bin/piper"), \
         patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path), \
         patch("zeno.audio.piper_tts._speak_via_package", return_value=True) as mock_pkg, \
         patch("zeno.audio.piper_tts._speak_via_cli") as mock_cli, \
         patch("zeno.audio.piper_tts._PiperVoice", MagicMock()):
        assert piper_tts.speak("hello") is True
    mock_pkg.assert_called_once()
    mock_cli.assert_not_called()


def test_speak_falls_back_to_cli_when_package_fails(tmp_path):
    from zeno.audio import piper_tts
    (tmp_path / "en_US-lessac-medium.onnx").write_bytes(b"fake")
    (tmp_path / "en_US-lessac-medium.onnx.json").write_text("{}")

    with patch("zeno.audio.piper_tts._PIPER_BIN", "/usr/bin/piper"), \
         patch("zeno.audio.piper_tts._VOICE_DIR", tmp_path), \
         patch("zeno.audio.piper_tts._speak_via_package", return_value=False), \
         patch("zeno.audio.piper_tts._speak_via_cli", return_value=True) as mock_cli, \
         patch("zeno.audio.piper_tts._PiperVoice", MagicMock()):
        assert piper_tts.speak("hello") is True
    mock_cli.assert_called_once()


def test_speak_via_cli_synthesizes_and_plays_on_success(tmp_path):
    from zeno.audio import piper_tts
    onnx = tmp_path / "en_US-lessac-medium.onnx"
    config = tmp_path / "en_US-lessac-medium.onnx.json"
    onnx.write_bytes(b"fake-model")
    config.write_text("{}")

    def fake_run(cmd, **kwargs):
        out_index = cmd.index("--output_file") + 1
        with open(cmd[out_index], "wb") as f:
            f.write(b"RIFF" + b"\x00" * 100)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_run), \
         patch("zeno.audio.piper_tts._play_wav", return_value=True) as mock_play:
        result = piper_tts._speak_via_cli("hello world", onnx, config)

    assert result is True
    mock_play.assert_called_once()


def test_speak_via_cli_returns_false_on_synthesis_failure(tmp_path):
    from zeno.audio import piper_tts
    onnx = tmp_path / "en_US-lessac-medium.onnx"
    config = tmp_path / "en_US-lessac-medium.onnx.json"
    onnx.write_bytes(b"fake")
    config.write_text("{}")

    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        assert piper_tts._speak_via_cli("hello", onnx, config) is False


def test_speak_via_package_writes_wav_and_plays(tmp_path):
    from zeno.audio import piper_tts
    onnx = tmp_path / "en_US-lessac-medium.onnx"
    config = tmp_path / "en_US-lessac-medium.onnx.json"
    onnx.write_bytes(b"fake")
    config.write_text("{}")

    fake_voice = MagicMock()

    def fake_synthesize_wav(text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 100)

    fake_voice.synthesize_wav.side_effect = fake_synthesize_wav

    with patch("zeno.audio.piper_tts._PiperVoice") as mock_cls, \
         patch("zeno.audio.piper_tts._play_wav", return_value=True) as mock_play:
        mock_cls.load.return_value = fake_voice
        result = piper_tts._speak_via_package("hello", "en_US-lessac-medium", onnx, config)

    assert result is True
    mock_play.assert_called_once()


def test_speak_via_package_returns_false_on_exception(tmp_path):
    from zeno.audio import piper_tts
    onnx = tmp_path / "en_US-lessac-medium.onnx"
    config = tmp_path / "en_US-lessac-medium.onnx.json"
    onnx.write_bytes(b"fake")
    config.write_text("{}")

    with patch("zeno.audio.piper_tts._PiperVoice") as mock_cls:
        mock_cls.load.side_effect = RuntimeError("bad model")
        result = piper_tts._speak_via_package("hello", "some-voice-not-cached", onnx, config)

    assert result is False


# ---------------------------------------------------------------------------
# whisper.cpp STT
# ---------------------------------------------------------------------------

def test_whisper_unavailable_when_binary_missing():
    with patch("zeno.audio.whisper_stt._WHISPER_BIN", None):
        from zeno.audio import whisper_stt
        assert whisper_stt.is_available() is False


def test_whisper_model_downloaded_false_when_missing(tmp_path):
    from zeno.audio import whisper_stt
    with patch("zeno.audio.whisper_stt._MODEL_DIR", tmp_path):
        assert whisper_stt.is_model_downloaded("tiny") is False


def test_whisper_model_downloaded_true_when_present(tmp_path):
    from zeno.audio import whisper_stt
    (tmp_path / "ggml-tiny.bin").write_bytes(b"fake-model")
    with patch("zeno.audio.whisper_stt._MODEL_DIR", tmp_path):
        assert whisper_stt.is_model_downloaded("tiny") is True


def test_transcribe_returns_none_when_binary_missing():
    from zeno.audio import whisper_stt
    with patch("zeno.audio.whisper_stt._WHISPER_BIN", None):
        assert whisper_stt.transcribe("/tmp/fake.wav") is None


def test_transcribe_returns_none_when_model_missing(tmp_path):
    from zeno.audio import whisper_stt
    with patch("zeno.audio.whisper_stt._WHISPER_BIN", "/usr/bin/whisper-cli"), \
         patch("zeno.audio.whisper_stt._MODEL_DIR", tmp_path):
        assert whisper_stt.transcribe("/tmp/fake.wav", model="tiny") is None


def test_transcribe_returns_stdout_text(tmp_path):
    from zeno.audio import whisper_stt
    (tmp_path / "ggml-tiny.bin").write_bytes(b"fake-model")
    with patch("zeno.audio.whisper_stt._WHISPER_BIN", "/usr/bin/whisper-cli"), \
         patch("zeno.audio.whisper_stt._MODEL_DIR", tmp_path), \
         patch("subprocess.run", return_value=MagicMock(stdout="hello there", stderr="")):
        result = whisper_stt.transcribe("/tmp/fake.wav", model="tiny")
    assert result == "hello there"


def test_listen_returns_none_when_pipewire_unavailable():
    from zeno.audio import whisper_stt
    with patch("zeno.audio.whisper_stt.pw_available", return_value=False):
        assert whisper_stt.listen(timeout=1.0) is None


# ---------------------------------------------------------------------------
# Top-level speak()/listen(): full engine chain, in order, with overrides
# ---------------------------------------------------------------------------

def test_tts_speak_tries_kokoro_first_under_auto():
    from zeno.audio import tts
    with patch.dict("os.environ", {}, clear=False), \
         patch("zeno.audio.tts.kokoro_tts.is_available", return_value=True), \
         patch("zeno.audio.tts.kokoro_tts.is_model_downloaded", return_value=True), \
         patch("zeno.audio.tts.kokoro_tts.speak", return_value=True) as mock_kokoro, \
         patch("zeno.audio.tts.piper_tts.speak") as mock_piper:
        os.environ.pop("ZENO_TTS_ENGINE", None)
        assert tts.speak("hi") is True
    mock_kokoro.assert_called_once()
    mock_piper.assert_not_called()


def test_tts_speak_falls_back_to_piper_when_kokoro_not_ready():
    from zeno.audio import tts
    with patch("zeno.audio.tts.kokoro_tts.is_available", return_value=False), \
         patch("zeno.audio.tts.piper_tts.is_available", return_value=True), \
         patch("zeno.audio.tts.piper_tts.is_voice_downloaded", return_value=True), \
         patch("zeno.audio.tts.piper_tts.speak", return_value=True) as mock_piper, \
         patch("zeno.audio.tts.tts_speak") as mock_platform:
        os.environ.pop("ZENO_TTS_ENGINE", None)
        assert tts.speak("hi") is True
    mock_piper.assert_called_once()
    mock_platform.assert_not_called()


def test_tts_speak_falls_back_to_platform_when_all_local_engines_fail():
    from zeno.audio import tts
    from zeno.platform.providers.base import PlatformCaps
    with patch("zeno.audio.tts.kokoro_tts.is_available", return_value=False), \
         patch("zeno.audio.tts.piper_tts.is_available", return_value=True), \
         patch("zeno.audio.tts.piper_tts.is_voice_downloaded", return_value=True), \
         patch("zeno.audio.tts.piper_tts.speak", return_value=False), \
         patch("zeno.audio.tts.caps", return_value=PlatformCaps(tts=True)), \
         patch("zeno.audio.tts.tts_speak", return_value=True) as mock_platform:
        os.environ.pop("ZENO_TTS_ENGINE", None)
        assert tts.speak("hi") is True
    mock_platform.assert_called_once()


def test_tts_speak_engine_env_var_forces_piper_only():
    from zeno.audio import tts
    with patch.dict("os.environ", {"ZENO_TTS_ENGINE": "piper"}), \
         patch("zeno.audio.tts.kokoro_tts.is_available", return_value=True), \
         patch("zeno.audio.tts.kokoro_tts.is_model_downloaded", return_value=True), \
         patch("zeno.audio.tts.kokoro_tts.speak") as mock_kokoro, \
         patch("zeno.audio.tts.piper_tts.is_available", return_value=True), \
         patch("zeno.audio.tts.piper_tts.is_voice_downloaded", return_value=True), \
         patch("zeno.audio.tts.piper_tts.speak", return_value=True) as mock_piper:
        assert tts.speak("hi") is True
    mock_kokoro.assert_not_called()
    mock_piper.assert_called_once()


def test_tts_speak_engine_env_var_platform_skips_all_local_engines():
    from zeno.audio import tts
    from zeno.platform.providers.base import PlatformCaps
    with patch.dict("os.environ", {"ZENO_TTS_ENGINE": "platform"}), \
         patch("zeno.audio.tts.kokoro_tts.speak") as mock_kokoro, \
         patch("zeno.audio.tts.piper_tts.speak") as mock_piper, \
         patch("zeno.audio.tts.caps", return_value=PlatformCaps(tts=True)), \
         patch("zeno.audio.tts.tts_speak", return_value=True) as mock_platform:
        assert tts.speak("hi") is True
    mock_kokoro.assert_not_called()
    mock_piper.assert_not_called()
    mock_platform.assert_called_once()


def test_stt_listen_tries_faster_whisper_first_under_auto():
    from zeno.audio import stt
    with patch("zeno.audio.stt.faster_whisper_stt.is_available", return_value=True), \
         patch("zeno.audio.stt.faster_whisper_stt.is_model_downloaded", return_value=True), \
         patch("zeno.audio.stt.faster_whisper_stt.listen", return_value="hello") as mock_fw, \
         patch("zeno.audio.stt.whisper_stt.listen") as mock_whisper:
        os.environ.pop("ZENO_STT_ENGINE", None)
        assert stt.listen(timeout=5) == "hello"
    mock_fw.assert_called_once()
    mock_whisper.assert_not_called()


def test_stt_listen_falls_back_to_whisper_cpp_when_faster_whisper_not_ready():
    from zeno.audio import stt
    with patch("zeno.audio.stt.faster_whisper_stt.is_available", return_value=False), \
         patch("zeno.audio.stt.whisper_stt.is_available", return_value=True), \
         patch("zeno.audio.stt.whisper_stt.is_model_downloaded", return_value=True), \
         patch("zeno.audio.stt.whisper_stt.listen", return_value="hello") as mock_whisper, \
         patch("zeno.audio.stt.stt_listen") as mock_platform:
        os.environ.pop("ZENO_STT_ENGINE", None)
        assert stt.listen(timeout=5) == "hello"
    mock_whisper.assert_called_once()
    mock_platform.assert_not_called()


def test_stt_listen_falls_back_to_platform_when_all_local_engines_fail():
    from zeno.audio import stt
    from zeno.platform.providers.base import PlatformCaps
    with patch("zeno.audio.stt.faster_whisper_stt.is_available", return_value=False), \
         patch("zeno.audio.stt.whisper_stt.is_available", return_value=True), \
         patch("zeno.audio.stt.whisper_stt.is_model_downloaded", return_value=True), \
         patch("zeno.audio.stt.whisper_stt.listen", return_value=None), \
         patch("zeno.audio.stt.caps", return_value=PlatformCaps(stt=True)), \
         patch("zeno.audio.stt.stt_listen", return_value="platform result") as mock_platform:
        os.environ.pop("ZENO_STT_ENGINE", None)
        assert stt.listen(timeout=5) == "platform result"
    mock_platform.assert_called_once()


def test_stt_listen_engine_env_var_forces_whisper_cpp_only():
    from zeno.audio import stt
    with patch.dict("os.environ", {"ZENO_STT_ENGINE": "whisper_cpp"}), \
         patch("zeno.audio.stt.faster_whisper_stt.is_available", return_value=True), \
         patch("zeno.audio.stt.faster_whisper_stt.is_model_downloaded", return_value=True), \
         patch("zeno.audio.stt.faster_whisper_stt.listen") as mock_fw, \
         patch("zeno.audio.stt.whisper_stt.is_available", return_value=True), \
         patch("zeno.audio.stt.whisper_stt.is_model_downloaded", return_value=True), \
         patch("zeno.audio.stt.whisper_stt.listen", return_value="hello") as mock_whisper:
        assert stt.listen(timeout=5) == "hello"
    mock_fw.assert_not_called()
    mock_whisper.assert_called_once()


# ---------------------------------------------------------------------------
# faster-whisper STT engine
# ---------------------------------------------------------------------------

def test_faster_whisper_unavailable_when_package_missing():
    with patch("zeno.audio.faster_whisper_stt._fw", None):
        from zeno.audio import faster_whisper_stt
        assert faster_whisper_stt.is_available() is False


def test_faster_whisper_unavailable_on_termux_even_if_installed():
    from zeno.audio import faster_whisper_stt
    with patch("zeno.audio.faster_whisper_stt._fw", MagicMock()), \
         patch("zeno.audio.faster_whisper_stt._is_termux", return_value=True):
        assert faster_whisper_stt.is_available() is False


def test_faster_whisper_available_on_desktop_when_installed():
    from zeno.audio import faster_whisper_stt
    with patch("zeno.audio.faster_whisper_stt._fw", MagicMock()), \
         patch("zeno.audio.faster_whisper_stt._is_termux", return_value=False):
        assert faster_whisper_stt.is_available() is True


def test_faster_whisper_transcribe_returns_none_when_unavailable():
    from zeno.audio import faster_whisper_stt
    with patch("zeno.audio.faster_whisper_stt._fw", None):
        assert faster_whisper_stt.transcribe("/tmp/fake.wav") is None


def test_faster_whisper_transcribe_joins_segments():
    from zeno.audio import faster_whisper_stt
    fake_segments = [MagicMock(text=" hello "), MagicMock(text=" there ")]
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (fake_segments, MagicMock())

    with patch("zeno.audio.faster_whisper_stt._fw", MagicMock()), \
         patch("zeno.audio.faster_whisper_stt._is_termux", return_value=False), \
         patch("zeno.audio.faster_whisper_stt._get_model", return_value=fake_model):
        result = faster_whisper_stt.transcribe("/tmp/fake.wav")
    assert result == "hello there"


def test_faster_whisper_transcribe_handles_exception():
    from zeno.audio import faster_whisper_stt
    with patch("zeno.audio.faster_whisper_stt._fw", MagicMock()), \
         patch("zeno.audio.faster_whisper_stt._is_termux", return_value=False), \
         patch("zeno.audio.faster_whisper_stt._get_model", side_effect=RuntimeError("boom")):
        assert faster_whisper_stt.transcribe("/tmp/fake.wav") is None


def test_faster_whisper_listen_returns_none_without_pipewire():
    from zeno.audio import faster_whisper_stt
    with patch("zeno.audio.faster_whisper_stt._fw", MagicMock()), \
         patch("zeno.audio.faster_whisper_stt._is_termux", return_value=False), \
         patch("zeno.audio.pipewire.is_available", return_value=False):
        assert faster_whisper_stt.listen(timeout=1.0) is None


# ---------------------------------------------------------------------------
# Kokoro-82M TTS engine
# ---------------------------------------------------------------------------

def test_kokoro_unavailable_when_package_missing():
    with patch("zeno.audio.kokoro_tts._KokoroEngine", None):
        from zeno.audio import kokoro_tts
        assert kokoro_tts.is_available() is False


def test_kokoro_model_downloaded_false_when_files_missing(tmp_path):
    from zeno.audio import kokoro_tts
    with patch("zeno.audio.kokoro_tts._MODEL_DIR", tmp_path):
        assert kokoro_tts.is_model_downloaded() is False


def test_kokoro_model_downloaded_true_when_both_files_present(tmp_path):
    from zeno.audio import kokoro_tts
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"fake")
    (tmp_path / "voices-v1.0.bin").write_bytes(b"fake")
    with patch("zeno.audio.kokoro_tts._MODEL_DIR", tmp_path):
        assert kokoro_tts.is_model_downloaded() is True


def test_kokoro_speak_returns_false_when_unavailable():
    from zeno.audio import kokoro_tts
    with patch("zeno.audio.kokoro_tts._KokoroEngine", None):
        assert kokoro_tts.speak("hello") is False


def test_kokoro_speak_returns_false_when_model_not_downloaded(tmp_path):
    from zeno.audio import kokoro_tts
    with patch("zeno.audio.kokoro_tts._KokoroEngine", MagicMock()), \
         patch("zeno.audio.kokoro_tts._MODEL_DIR", tmp_path):
        assert kokoro_tts.speak("hello") is False


def test_kokoro_speak_synthesizes_and_plays_on_success(tmp_path):
    import numpy as np
    from zeno.audio import kokoro_tts
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"fake")
    (tmp_path / "voices-v1.0.bin").write_bytes(b"fake")

    fake_engine = MagicMock()
    fake_engine.create.return_value = (np.zeros(1000, dtype=np.float32), 24000)

    with patch("zeno.audio.kokoro_tts._KokoroEngine", MagicMock()), \
         patch("zeno.audio.kokoro_tts._MODEL_DIR", tmp_path), \
         patch("zeno.audio.kokoro_tts._get_engine", return_value=fake_engine), \
         patch("zeno.audio.kokoro_tts._play_wav", return_value=True) as mock_play:
        result = kokoro_tts.speak("hello world")

    assert result is True
    mock_play.assert_called_once()


def test_kokoro_speak_returns_false_on_synthesis_exception(tmp_path):
    from zeno.audio import kokoro_tts
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"fake")
    (tmp_path / "voices-v1.0.bin").write_bytes(b"fake")

    with patch("zeno.audio.kokoro_tts._KokoroEngine", MagicMock()), \
         patch("zeno.audio.kokoro_tts._MODEL_DIR", tmp_path), \
         patch("zeno.audio.kokoro_tts._get_engine", side_effect=RuntimeError("boom")):
        assert kokoro_tts.speak("hello") is False
