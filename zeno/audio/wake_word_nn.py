"""
Zeno Wake Word — local neural keyword spotting via openWakeWord

Replaces the older approach in zeno/audio/wake.py, which detects a wake
word by repeatedly running full speech-to-text (Whisper etc.) on short
chunks and pattern-matching the transcript. That works, but STT is a
heavy model to run every ~1 second continuously — expensive on CPU and
battery for something that's 99% of the time just background noise.

This module instead runs a small (~keyword-spotting-scale) ONNX model
continuously — the same class of model phone assistants use to listen
for "Hey Siri"/"OK Google" at near-zero power draw. Full STT is only
invoked after the wake word actually fires.

Ships with generic pretrained models (openWakeWord downloads them into
its own package directory on first use): "hey_jarvis", "alexa",
"hey_mycroft", plus a few phrase models. There is no pretrained
"hey zeno" model yet — training one is a separate undertaking (see the
note at the bottom of this file) — so this defaults to "hey_jarvis" as
a stand-in wake phrase until a custom model exists.

Desktop-only for now: needs PipeWire for continuous low-latency audio
capture, which Termux doesn't have. Falls back to zeno/audio/wake.py's
STT-polling approach on platforms where this isn't available.
"""

import time

try:
    from openwakeword.model import Model as _OWWModel
except ImportError:
    _OWWModel = None

from zeno.audio.pipewire import is_available as _pw_available, stream_chunks as _pw_stream

_CHUNK_SECONDS = 0.08  # openWakeWord wants multiples of 80ms (1280 samples @ 16kHz)
_DEFAULT_MODELS = ("hey_jarvis",)  # stand-in until a custom "hey zeno" model exists
_DEFAULT_THRESHOLD = 0.5

_model_instance = None


def is_available() -> bool:
    return _OWWModel is not None and _pw_available()


def _get_model():
    """Lazily create the shared Model instance. openWakeWord downloads
    its pretrained ONNX models into its own package data directory the
    first time this runs — no separate download_model() step needed."""
    global _model_instance
    if _model_instance is None:
        _model_instance = _OWWModel()
    return _model_instance


def predict_chunk(pcm_int16, wake_models: tuple = _DEFAULT_MODELS) -> dict:
    """Run one chunk of int16 PCM audio through the KWS model(s).
    Returns {model_name: score} restricted to the requested models."""
    model = _get_model()
    scores = model.predict(pcm_int16)
    return {name: scores.get(name, 0.0) for name in wake_models if name in scores}


def wait_for_wake_word(wake_models: tuple = _DEFAULT_MODELS,
                        threshold: float = _DEFAULT_THRESHOLD,
                        timeout: float = 30.0) -> bool:
    """Continuously stream short audio chunks through the KWS model
    until a wake word is detected or `timeout` elapses. Returns True if
    detected, False on timeout or if this engine isn't available (in
    which case the caller should fall back to zeno.audio.wake)."""
    if not is_available():
        return False

    import numpy as np

    model = _get_model()
    deadline = time.time() + timeout
    stream = _pw_stream(chunk_seconds=_CHUNK_SECONDS)
    try:
        for raw in stream:
            if time.time() > deadline:
                return False
            pcm = np.frombuffer(raw, dtype=np.int16)
            scores = model.predict(pcm)
            if any(scores.get(name, 0.0) >= threshold for name in wake_models):
                return True
        return False
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()


# ---------------------------------------------------------------------------
# NOTE on training a real "Hey Zeno" model
#
# openWakeWord's own training pipeline works by synthesizing positive
# examples with TTS, layering in background-noise/room-impulse-response
# augmentation, and training a small classifier on top of shared audio
# features. Zeno already has two local TTS engines (Piper, Kokoro) that
# could generate a meaningful chunk of that synthetic "hey zeno" positive
# data without needing any cloud TTS service. It still needs negative/
# background audio data and realistically a GPU for a full training run,
# so it's a genuine follow-up project, not something to bolt on casually.
# See: https://github.com/dscripka/openWakeWord (training notebook).
# ---------------------------------------------------------------------------
