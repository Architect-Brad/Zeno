"""Tests for zeno/audio/pipewire.py's stream_chunks() and
zeno/audio/wake_word_nn.py's neural keyword-spotting wake word engine."""

from unittest.mock import patch, MagicMock
import numpy as np


# ---------------------------------------------------------------------------
# pipewire.stream_chunks
# ---------------------------------------------------------------------------

def test_stream_chunks_yields_nothing_when_pw_missing():
    from zeno.audio import pipewire
    with patch("zeno.audio.pipewire._which_pw", return_value=None):
        chunks = list(pipewire.stream_chunks(chunk_seconds=0.08))
    assert chunks == []


def test_stream_chunks_yields_fixed_size_chunks_then_stops_on_short_read():
    from zeno.audio import pipewire

    bytes_per_chunk = int(0.08 * 16000) * 2  # matches stream_chunks' own math
    fake_proc = MagicMock()
    # Two full chunks, then a short read that ends the stream
    reads = [b"\x00" * bytes_per_chunk, b"\x00" * bytes_per_chunk, b""]
    fake_proc.stdout.read.side_effect = reads

    with patch("zeno.audio.pipewire._which_pw", return_value="/usr/bin/pw-cat"), \
         patch("subprocess.Popen", return_value=fake_proc):
        chunks = list(pipewire.stream_chunks(chunk_seconds=0.08))

    assert len(chunks) == 2
    assert all(len(c) == bytes_per_chunk for c in chunks)
    fake_proc.terminate.assert_called_once()


def test_stream_chunks_terminates_process_on_early_close():
    from zeno.audio import pipewire

    bytes_per_chunk = int(0.08 * 16000) * 2
    fake_proc = MagicMock()
    fake_proc.stdout.read.return_value = b"\x00" * bytes_per_chunk  # infinite supply

    with patch("zeno.audio.pipewire._which_pw", return_value="/usr/bin/pw-cat"), \
         patch("subprocess.Popen", return_value=fake_proc):
        gen = pipewire.stream_chunks(chunk_seconds=0.08)
        next(gen)  # pull one chunk
        gen.close()  # caller decides it's done

    fake_proc.terminate.assert_called_once()


# ---------------------------------------------------------------------------
# wake_word_nn
# ---------------------------------------------------------------------------

def test_wake_word_nn_unavailable_when_package_missing():
    with patch("zeno.audio.wake_word_nn._OWWModel", None):
        from zeno.audio import wake_word_nn
        assert wake_word_nn.is_available() is False


def test_wake_word_nn_unavailable_without_pipewire():
    from zeno.audio import wake_word_nn
    with patch("zeno.audio.wake_word_nn._OWWModel", MagicMock()), \
         patch("zeno.audio.wake_word_nn._pw_available", return_value=False):
        assert wake_word_nn.is_available() is False


def test_wake_word_nn_available_when_both_present():
    from zeno.audio import wake_word_nn
    with patch("zeno.audio.wake_word_nn._OWWModel", MagicMock()), \
         patch("zeno.audio.wake_word_nn._pw_available", return_value=True):
        assert wake_word_nn.is_available() is True


def test_predict_chunk_restricts_to_requested_models():
    from zeno.audio import wake_word_nn
    fake_model = MagicMock()
    fake_model.predict.return_value = {"hey_jarvis": 0.9, "alexa": 0.1, "weather": 0.0}

    with patch("zeno.audio.wake_word_nn._get_model", return_value=fake_model):
        result = wake_word_nn.predict_chunk(np.zeros(1280, dtype=np.int16), wake_models=("hey_jarvis",))

    assert result == {"hey_jarvis": 0.9}


def test_wait_for_wake_word_returns_false_when_unavailable():
    from zeno.audio import wake_word_nn
    with patch("zeno.audio.wake_word_nn.is_available", return_value=False):
        assert wake_word_nn.wait_for_wake_word(timeout=1.0) is False


def test_wait_for_wake_word_detects_above_threshold():
    from zeno.audio import wake_word_nn

    fake_model = MagicMock()
    fake_model.predict.return_value = {"hey_jarvis": 0.8}

    chunk = b"\x00\x00" * 1280  # 1280 int16 samples

    with patch("zeno.audio.wake_word_nn.is_available", return_value=True), \
         patch("zeno.audio.wake_word_nn._get_model", return_value=fake_model), \
         patch("zeno.audio.wake_word_nn._pw_stream", return_value=iter([chunk])):
        detected = wake_word_nn.wait_for_wake_word(
            wake_models=("hey_jarvis",), threshold=0.5, timeout=5.0
        )
    assert detected is True


def test_wait_for_wake_word_false_when_below_threshold_and_stream_ends():
    from zeno.audio import wake_word_nn

    fake_model = MagicMock()
    fake_model.predict.return_value = {"hey_jarvis": 0.1}
    chunk = b"\x00\x00" * 1280

    with patch("zeno.audio.wake_word_nn.is_available", return_value=True), \
         patch("zeno.audio.wake_word_nn._get_model", return_value=fake_model), \
         patch("zeno.audio.wake_word_nn._pw_stream", return_value=iter([chunk, chunk])):
        detected = wake_word_nn.wait_for_wake_word(
            wake_models=("hey_jarvis",), threshold=0.5, timeout=5.0
        )
    assert detected is False


def test_wait_for_wake_word_closes_stream_on_exit():
    from zeno.audio import wake_word_nn

    fake_model = MagicMock()
    fake_model.predict.return_value = {"hey_jarvis": 0.9}
    chunk = b"\x00\x00" * 1280

    class FakeStream:
        def __init__(self, chunks):
            self._it = iter(chunks)
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._it)

        def close(self):
            self.closed = True

    fake_stream = FakeStream([chunk])

    with patch("zeno.audio.wake_word_nn.is_available", return_value=True), \
         patch("zeno.audio.wake_word_nn._get_model", return_value=fake_model), \
         patch("zeno.audio.wake_word_nn._pw_stream", return_value=fake_stream):
        wake_word_nn.wait_for_wake_word(wake_models=("hey_jarvis",), timeout=5.0)

    assert fake_stream.closed is True


# ---------------------------------------------------------------------------
# wake.py: prefers the neural engine, falls back to STT-polling
# ---------------------------------------------------------------------------

def test_wake_prefers_neural_engine_when_available():
    from zeno.audio import wake
    with patch("zeno.audio.wake.wake_word_nn.is_available", return_value=True), \
         patch("zeno.audio.wake.wake_word_nn.wait_for_wake_word", return_value=True), \
         patch("zeno.audio.wake.listen", return_value="what time is it") as mock_listen, \
         patch("zeno.audio.wake._legacy_wait_for_wake_word") as mock_legacy:
        result = wake.wait_for_wake_word(timeout=5)

    assert result == "what time is it"
    mock_legacy.assert_not_called()


def test_wake_falls_back_to_legacy_when_neural_engine_unavailable():
    from zeno.audio import wake
    with patch("zeno.audio.wake.wake_word_nn.is_available", return_value=False), \
         patch("zeno.audio.wake._legacy_wait_for_wake_word", return_value="hi there") as mock_legacy:
        result = wake.wait_for_wake_word(timeout=5)

    assert result == "hi there"
    mock_legacy.assert_called_once()


def test_wake_returns_none_when_neural_engine_available_but_no_detection():
    from zeno.audio import wake
    with patch("zeno.audio.wake.wake_word_nn.is_available", return_value=True), \
         patch("zeno.audio.wake.wake_word_nn.wait_for_wake_word", return_value=False), \
         patch("zeno.audio.wake._legacy_wait_for_wake_word") as mock_legacy:
        result = wake.wait_for_wake_word(timeout=5)

    assert result is None
    mock_legacy.assert_not_called()  # timing out on detection shouldn't retry via the legacy path
