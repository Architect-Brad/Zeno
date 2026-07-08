"""
Zeno Doctor — a self-diagnosis command.

Zeno has a lot of moving parts (STT/TTS backends that vary per OS, an
optional web dashboard, optional LAN sync, optional TUI), and when
something doesn't work it's rarely obvious *why* from the ordinary
error messages. `zeno --doctor` runs a battery of cheap, read-only
checks and prints a clear pass/warn/fail report so a user can
self-diagnose instead of filing an issue or digging through logs.
"""

from __future__ import annotations

import importlib
import shutil
import socket
import sys
from dataclasses import dataclass

from zeno.core.term import green, yellow, red, bold, dim, cyan


@dataclass
class CheckResult:
    name: str
    status: str      # "ok" | "warn" | "fail"
    detail: str = ""


def _ok(name: str, detail: str = "") -> CheckResult:
    return CheckResult(name, "ok", detail)


def _warn(name: str, detail: str = "") -> CheckResult:
    return CheckResult(name, "warn", detail)


def _fail(name: str, detail: str = "") -> CheckResult:
    return CheckResult(name, "fail", detail)


# ---------------------------------------------------------------------------
# Individual checks — each is self-contained and never raises; a check
# that can't complete reports "fail" with the exception message rather
# than crashing the whole report.
# ---------------------------------------------------------------------------

def _check_python() -> CheckResult:
    v = sys.version_info
    if v < (3, 10):
        return _fail("Python version", f"{v.major}.{v.minor} — Zeno needs 3.10+")
    return _ok("Python version", f"{v.major}.{v.minor}.{v.micro}")


def _check_platform() -> CheckResult:
    try:
        from zeno.platform import detect_platform, caps
        name = detect_platform()
        c = caps()
        if name == "dummy":
            return _warn(
                "Platform detection",
                "no supported OS backend found — TTS/STT/system control "
                "will be no-ops. This is expected in a bare container.",
            )
        enabled = [f for f in ("tts", "stt", "notification", "volume",
                                "brightness", "lock_screen", "open_app",
                                "battery", "torch")
                   if getattr(c, f, False)]
        return _ok("Platform detection", f"{name} ({', '.join(enabled) or 'no capabilities detected'})")
    except Exception as e:
        return _fail("Platform detection", str(e))


def _check_store() -> CheckResult:
    try:
        from zeno.memory.store import get_store
        store = get_store()
        store.set("doctor.ping", "pong")
        ok = store.get("doctor.ping") == "pong"
        store.delete("doctor.ping")
        if not ok:
            return _fail("Local data store", "write/read roundtrip failed")
        return _ok("Local data store", str(store.path))
    except Exception as e:
        return _fail("Local data store", str(e))


def _check_graph() -> CheckResult:
    try:
        from zeno.memory.graph import get_graph
        graph = get_graph()
        graph.get_usage_stats(top_n=1)
        return _ok("Knowledge graph", str(graph.path))
    except Exception as e:
        return _fail("Knowledge graph", str(e))


def _check_nlu() -> CheckResult:
    try:
        from zeno.nlu.intent import classify_intent
        result = classify_intent("what time is it")
        if result.intent != "time_query":
            return _warn(
                "NLU classifier",
                f"sanity check misclassified a simple query as '{result.intent}'",
            )
        return _ok("NLU classifier", f"loaded, confidence={result.confidence:.2f}")
    except Exception as e:
        return _fail("NLU classifier", str(e))


def _check_optional_dep(module: str, feature: str) -> CheckResult:
    try:
        importlib.import_module(module)
        return _ok(feature, f"'{module}' installed")
    except ImportError:
        return _warn(feature, f"'{module}' not installed — {feature} unavailable")


def _check_port(port: int) -> CheckResult:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        in_use = sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()
    if in_use:
        try:
            from zeno.core.daemon import is_running
            if is_running():
                return _ok(f"Web port {port}", "in use by the Zeno daemon")
        except Exception:
            pass
        return _warn(f"Web port {port}", "already in use by another process")
    return _ok(f"Web port {port}", "free")


def _check_daemon() -> CheckResult:
    try:
        from zeno.core.daemon import is_running, _pid
        if is_running():
            return _ok("Background daemon", f"running (PID {_pid()})")
        return _ok("Background daemon", "not running")
    except Exception as e:
        return _fail("Background daemon", str(e))


def _check_sync_token() -> CheckResult:
    try:
        from zeno.core.sync import sync_token
        tok = sync_token()
        return _ok("LAN sync pairing token", f"{tok[:8]}… (set ZENO_SYNC_TOKEN to override)")
    except Exception as e:
        return _fail("LAN sync pairing token", str(e))


def _check_piper() -> CheckResult:
    try:
        from zeno.audio import piper_tts
        if not piper_tts.is_available():
            return _warn(
                "Piper TTS (optional)",
                "'piper' binary not found — using platform-native TTS instead",
            )
        if not piper_tts.is_voice_downloaded():
            return _warn(
                "Piper TTS (optional)",
                f"piper found but no voice downloaded — run "
                f"piper_tts.download_voice() to fetch '{piper_tts._DEFAULT_VOICE}'",
            )
        return _ok("Piper TTS (optional)", f"voice '{piper_tts._DEFAULT_VOICE}' ready")
    except Exception as e:
        return _fail("Piper TTS (optional)", str(e))


def _check_whisper() -> CheckResult:
    try:
        from zeno.audio import whisper_stt
        if not whisper_stt.is_available():
            return _warn(
                "whisper.cpp STT (optional)",
                "'whisper-cli'/'whisper' binary not found — using platform-native STT instead",
            )
        if not whisper_stt.is_model_downloaded():
            return _warn(
                "whisper.cpp STT (optional)",
                f"whisper found but no model downloaded — run "
                f"whisper_stt.download_model() to fetch '{whisper_stt._DEFAULT_MODEL}'",
            )
        return _ok("whisper.cpp STT (optional)", f"model '{whisper_stt._DEFAULT_MODEL}' ready")
    except Exception as e:
        return _fail("whisper.cpp STT (optional)", str(e))


def _check_faster_whisper() -> CheckResult:
    try:
        from zeno.audio import faster_whisper_stt
        import os as _os
        from pathlib import Path as _Path
        is_termux = ("com.termux" in _os.environ.get("PREFIX", "")
                     or _Path("/data/data/com.termux").exists())
        if is_termux:
            return _warn(
                "faster-whisper STT (optional)",
                "not supported on Termux (ctranslate2 wheels don't build there) — "
                "whisper.cpp is the Termux-friendly option",
            )
        if not faster_whisper_stt.is_available():
            return _warn(
                "faster-whisper STT (optional)",
                "'faster-whisper' package not installed — pip install faster-whisper",
            )
        if not faster_whisper_stt.is_model_downloaded():
            return _warn(
                "faster-whisper STT (optional)",
                f"installed but no model cached yet — run "
                f"faster_whisper_stt.download_model() to fetch '{faster_whisper_stt._DEFAULT_MODEL}'",
            )
        return _ok("faster-whisper STT (optional)", f"model '{faster_whisper_stt._DEFAULT_MODEL}' ready")
    except Exception as e:
        return _fail("faster-whisper STT (optional)", str(e))


def _check_kokoro() -> CheckResult:
    try:
        from zeno.audio import kokoro_tts
        if not kokoro_tts.is_available():
            return _warn(
                "Kokoro-82M TTS (optional)",
                "'kokoro-onnx' package not installed — pip install kokoro-onnx",
            )
        if not kokoro_tts.is_model_downloaded():
            return _warn(
                "Kokoro-82M TTS (optional)",
                "installed but model not downloaded (~350MB) — run "
                "kokoro_tts.download_model() to fetch it",
            )
        return _ok("Kokoro-82M TTS (optional)", f"voice '{kokoro_tts._DEFAULT_VOICE}' ready")
    except Exception as e:
        return _fail("Kokoro-82M TTS (optional)", str(e))


def _check_nlu_embeddings() -> CheckResult:
    try:
        from zeno.nlu import embeddings
        if not embeddings.is_available():
            return _warn(
                "NLU semantic tie-breaker (optional)",
                "onnxruntime/tokenizers not installed — the n-gram classifier "
                "runs alone (this is the normal, fully-supported default)",
            )
        if not embeddings.is_model_downloaded():
            return _warn(
                "NLU semantic tie-breaker (optional)",
                "installed but model not downloaded (~90MB) — run "
                "embeddings.download_model() to fetch it",
            )
        return _ok("NLU semantic tie-breaker (optional)", "embedding model ready")
    except Exception as e:
        return _fail("NLU semantic tie-breaker (optional)", str(e))


def _check_wake_word() -> CheckResult:
    try:
        from zeno.audio import wake_word_nn
        if wake_word_nn.is_available():
            return _ok(
                "Wake word (neural KWS)",
                f"using '{wake_word_nn._DEFAULT_MODELS[0]}' as a stand-in "
                f"wake phrase (no custom 'hey zeno' model trained yet)",
            )
        return _warn(
            "Wake word (neural KWS)",
            "openwakeword and/or PipeWire not available — falling back to "
            "the STT-polling wake word approach (works, but far more "
            "CPU/battery-hungry when left listening continuously)",
        )
    except Exception as e:
        return _fail("Wake word (neural KWS)", str(e))


CHECKS = [
    _check_python,
    _check_platform,
    _check_store,
    _check_graph,
    _check_nlu,
    _check_nlu_embeddings,
    lambda: _check_optional_dep("fastapi", "Web dashboard"),
    lambda: _check_optional_dep("textual", "Terminal UI (--tui)"),
    _check_piper,
    _check_kokoro,
    _check_whisper,
    _check_faster_whisper,
    _check_wake_word,
    lambda: _check_port(8080),
    _check_daemon,
    _check_sync_token,
]


def run_doctor() -> int:
    """Run all checks, print a report, return an exit code (0 ok, 1 if any failed)."""
    print(bold(cyan("Zeno Doctor — running diagnostics\n")))

    results: list[CheckResult] = []
    for check in CHECKS:
        try:
            results.append(check())
        except Exception as e:  # a check itself misbehaving shouldn't crash the report
            results.append(_fail(getattr(check, "__name__", "unknown check"), str(e)))

    width = max(len(r.name) for r in results) + 2
    for r in results:
        if r.status == "ok":
            icon, label = green("✓"), r.name.ljust(width)
        elif r.status == "warn":
            icon, label = yellow("!"), r.name.ljust(width)
        else:
            icon, label = red("✗"), r.name.ljust(width)
        detail = dim(r.detail) if r.detail else ""
        print(f"  {icon}  {label} {detail}")

    n_fail = sum(1 for r in results if r.status == "fail")
    n_warn = sum(1 for r in results if r.status == "warn")

    print()
    if n_fail:
        print(red(f"{n_fail} check(s) failed") + (f", {n_warn} warning(s)" if n_warn else ""))
    elif n_warn:
        print(yellow(f"All checks passed, {n_warn} warning(s) — Zeno should work with reduced functionality"))
    else:
        print(green("All checks passed — Zeno looks healthy"))

    return 1 if n_fail else 0
