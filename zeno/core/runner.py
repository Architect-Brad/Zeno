"""
Zeno Runner — async voice interaction loop + text CLI.
Orchestrates: listen -> process -> speak.
Gracefully handles Termux API absence (falls back to text I/O).
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

from zeno.core.term import (
    zeno_prefix, error_prefix, user_prefix,
    green, cyan, yellow, red, bold, dim,
)
from zeno.core.context import Context
from zeno.core.loop import process_input
from zeno.audio.stt import listen
from zeno.audio.tts import speak
from zeno.memory.store import get_store
from zeno.core.proactive import get_engine as get_proactive

_VERSION = "1.0.0"
_WAKE_WORDS = ("zeno", "hey")
_DAEMON_PORT = 8080


# ── readline integration ─────────────────────────────────────────────

_HISTORY_FILE = Path.home() / ".zeno_history"
_SLASH_COMMANDS = [
    "/help", "/exit", "/cancel",
    "/w", "/weather", "/f", "/forecast",
    "/t", "/time", "/d", "/date",
    "/a", "/alarm",
    "/timer", "/remind",
    "/v", "/v+", "/v-", "/m", "/mute",
    "/b+", "/b-",
    "/lock", "/open",
    "/s", "/search",
    "/n", "/news",
    "/lights", "/lights on", "/lights off",
    "/timer status", "/timer stop",
    "/contacts", "/profile",
]

_COMPLETION_TRIGGERS = [
    "/", "wea", "tim", "alarm", "rem", "vol", "bright",
    "light", "hel", "exi", "qui", "can", "sea", "new",
]


def _setup_readline():
    try:
        import readline
    except ImportError:
        return

    hist = str(_HISTORY_FILE)
    try:
        readline.read_history_file(hist)
    except (FileNotFoundError, OSError):
        pass
    readline.set_history_length(500)

    try:
        import atexit
        atexit.register(lambda: readline.write_history_file(hist))
    except Exception:
        pass

    try:
        readline.set_completer(_tab_complete)
        readline.parse_and_bind("tab: complete")
        delims = readline.get_completer_delims()
        delims = delims.replace("/", "").replace("-", "")
        readline.set_completer_delims(delims)
    except Exception:
        pass


def _tab_complete(text: str, state: int) -> str | None:
    matches = [c for c in _SLASH_COMMANDS if c.startswith(text)]
    try:
        return matches[state]
    except IndexError:
        return None


# ── Slash commands ────────────────────────────────────────────────────

_SLASH_MAP: dict[str, str | None] = {
    "/help": None,  # handled directly
    "/exit": None,
    "/cancel": "cancel",
    "/w": "weather_query",
    "/weather": "weather_query",
    "/f": "weather_forecast",
    "/forecast": "weather_forecast",
    "/t": "time_query",
    "/time": "time_query",
    "/d": "date_query",
    "/date": "date_query",
    "/a": "set_alarm",
    "/alarm": "set_alarm",
    "/timer": "set_timer",
    "/remind": "set_reminder",
    "/v": "set_volume_exact",
    "/v+": "volume_up",
    "/v-": "volume_down",
    "/m": "volume_mute",
    "/mute": "volume_mute",
    "/b+": "brightness_up",
    "/b-": "brightness_down",
    "/lock": "system_lock",
    "/open": "open_app",
    "/s": None,  # search fallback
    "/search": None,
    "/n": "news_query",
    "/news": "news_query",
    "/lights": "lights_on",  # /lights off handled via text check
}


def _parse_slash_command(text: str) -> tuple[str | None, str, str | None]:
    """Parse a slash command. Returns (intent, remainder, raw_command).
    The third element is the raw remainder for commands that need it."""
    lower = text.strip()
    if not lower.startswith("/"):
        return None, text, None

    parts = lower.split(maxsplit=1)
    cmd = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""

    if cmd == "/exit":
        return None, "", None
    if cmd == "/help":
        _print_slash_help()
        return None, "", None
    if cmd == "/s" or cmd == "/search":
        return None, remainder, None  # passed as raw search

    intent = _SLASH_MAP.get(cmd)
    if intent:
        return intent, remainder, cmd
    return None, text, None


_SLASH_TO_PHRASE = {
    "/v": "set volume to",
    "/v+": "volume up",
    "/v-": "volume down",
    "/m": "volume mute",
    "/mute": "volume mute",
    "/b+": "brightness up",
    "/b-": "brightness down",
    "/lock": "lock the screen",
    "/open": "open",
    "/t": "what time is it",
    "/time": "what time is it",
    "/d": "what is today date",
    "/date": "what is today date",
    "/n": "what is in the news",
    "/news": "what is in the news",
    "/lights": "lights",
    "/w": "weather",
    "/weather": "weather",
    "/f": "weather forecast",
    "/forecast": "weather forecast",
    "/a": "set alarm",
    "/alarm": "set alarm",
    "/timer": "set timer",
    "/remind": "remind me to",
    "/cancel": "cancel",
}


def _print_slash_help():
    lines = [
        bold("Slash Commands"),
        "  /help              Show this help",
        "  /exit              Exit Zeno",
        "  /cancel            Cancel current operation",
        "",
        bold("Weather"),
        "  /w [city]          Current weather",
        "  /f [city]          5-day forecast",
        "",
        bold("Time & Date"),
        "  /t                 Current time",
        "  /d                 Current date",
        "",
        bold("Alarms, Timers, Reminders"),
        "  /a <time> [label]  Set alarm",
        "  /timer <dur> [lbl] Set timer",
        "  /remind <text>     Set reminder",
        "",
        bold("System"),
        "  /v <level>         Set volume (0-100)",
        "  /v+                Volume up",
        "  /v-                Volume down",
        "  /m                 Mute",
        "  /b+                Brightness up",
        "  /b-                Brightness down",
        "  /lock              Lock screen",
        "  /open <app>        Open app",
        "",
        bold("Smart Home"),
        "  /lights [on|off]   Toggle lights",
        "",
        bold("Info"),
        "  /n                 News headlines",
        "  /s <query>         Search DuckDuckGo",
        "",
        bold("Shorthand"),
        "  5m pizza           Set 5-minute timer 'pizza'",
        "  7am wake up        Set alarm 7:00 AM 'wake up'",
        "  10min              Set 10-minute timer (no label)",
    ]
    for line in lines:
        print(f"  {line}")


# ── Shorthand syntax ─────────────────────────────────────────────────

_SHORT_DUR_RE = re.compile(r"^(\d+)\s*(m|min|mins|minute|minutes|s|sec|secs|second|seconds|h|hr|hrs|hour|hours)(?:\s+(.+))?$", re.IGNORECASE)
_SHORT_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s+(.+))?$", re.IGNORECASE)


def _try_shorthand(text: str) -> tuple[str | None, str | None, str]:
    """Try to parse shorthand syntax. Returns (intent, entities_text, normalized)."""
    lower = text.strip().lower()

    # 5m pizza → set_timer 5 minutes pizza
    m = _SHORT_DUR_RE.match(lower)
    if m:
        amount = m.group(1)
        unit = m.group(2).lower()
        label = m.group(3)
        if unit.startswith("h"):
            dur = f"{amount} hours"
        elif unit.startswith("m"):
            dur = f"{amount} minutes"
        else:
            dur = f"{amount} seconds"
        if label:
            normalized = f"set a timer for {dur} called {label}"
            return "set_timer", normalized, text
        normalized = f"set a timer for {dur}"
        return "set_timer", normalized, text

    # 7am wake up → set_alarm 7:00 AM wake up
    m = _SHORT_TIME_RE.match(lower)
    if m:
        hour = int(m.group(1))
        minute = m.group(2)
        meridiem = m.group(3)
        label = m.group(4)
        if meridiem:
            meridiem = meridiem.upper()
        else:
            if hour >= 12:
                meridiem = "PM"
            else:
                meridiem = "AM"
            if hour > 12:
                hour = hour - 12
        if minute is None:
            minute = "00"
        time_str = f"{hour}:{minute} {meridiem}"
        if label:
            normalized = f"set an alarm for {time_str} called {label}"
            return "set_alarm", normalized, text
        normalized = f"set an alarm for {time_str}"
        return "set_alarm", normalized, text

    return None, None, text


# ── Core helpers ─────────────────────────────────────────────────────

async def listen_async(timeout: int = 15) -> str | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, listen, timeout)


async def speak_async(text: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, speak, text)


async def listen_for_wake(timeout: int = 15) -> str | None:
    while True:
        text = await listen_async(timeout=timeout)
        if not text:
            continue
        lower = text.lower()
        if any(ww in lower for ww in _WAKE_WORDS):
            return text
        print(".", end="", flush=True)


async def run_voice_interaction(context: Context,
                                require_wake: bool = False,
                                native_wake: bool = False) -> str | None:
    # Check for proactive suggestion first
    try:
        proactive = get_proactive().check()
        if proactive:
            await speak_async(proactive)
    except Exception:
        pass
    if native_wake:
        from zeno.audio.wake import wait_for_wake_word
        text = await asyncio.get_running_loop().run_in_executor(
            None, lambda: wait_for_wake_word(timeout=30)
        )
    elif require_wake:
        text = await listen_for_wake()
    else:
        text = await listen_async()

    if not text:
        return None

    lower = text.lower()
    if not any(ww in lower for ww in _WAKE_WORDS):
        text = f"hey zeno {text}"

    response = process_input(text, context)
    await speak_async(response)
    return response


async def run_voice_loop(require_wake: bool = False, native_wake: bool = False):
    context = Context()
    if native_wake:
        mode = "native wake word (VAD)"
    elif require_wake:
        mode = "wake word"
    else:
        mode = "push-to-talk"
    print(f"{zeno_prefix()} Voice assistant ready. {dim(f'Mode: {mode}')}. {dim('Ctrl+C to exit.')}")
    sys.stdout.flush()

    while True:
        try:
            response = await run_voice_interaction(
                context, require_wake=require_wake, native_wake=native_wake
            )
            if response is None:
                continue
        except (EOFError, KeyboardInterrupt):
            print(f"\n{zeno_prefix()} Goodbye!")
            break
        except Exception as e:
            print(f"{error_prefix()} {e}")
            continue


# ── Daemon proxy ──────────────────────────────────────────────────────

def _proxy_through_daemon(text: str, daemon_port: int) -> str | None:
    from zeno.core.daemon import is_running, proxy_request
    if not is_running():
        return None
    return proxy_request(text, daemon_port)


# ── Text loop ─────────────────────────────────────────────────────────

def _handle_slash_or_shorthand(text: str, context: Context) -> str | None:
    """Try slash command + shorthand. Returns response or None to continue normally."""
    intent, remainder, cmd = _parse_slash_command(text)
    if intent is not None:
        if intent == "cancel":
            context.clear_awaiting()
            from zeno.response.engine import pick
            return pick("cancel")
        phrase = _SLASH_TO_PHRASE.get(cmd, intent.replace("_", " "))
        if remainder:
            full = f"{phrase} {remainder}"
        else:
            full = phrase
        return process_input(full, context)
    if text.startswith("/"):
        return ""

    if not context.awaiting():
        shorthand_intent, normalized, _ = _try_shorthand(text)
        if shorthand_intent and normalized:
            return process_input(normalized, context)

    return None


def run_text_loop(daemon_port: int | None = None):
    # Auto-proxy: if daemon is running, forward through it
    from zeno.core.daemon import is_running, proxy_request
    if daemon_port is None:
        daemon_port = _DAEMON_PORT
    using_daemon = is_running()

    if using_daemon:
        print(f"{zeno_prefix()} Text mode {dim('(proxied through daemon)')}. {dim('/help for commands, /exit to quit.')}")
    else:
        print(f"{zeno_prefix()} Text mode. {dim('Type /help for commands, /exit to quit.')}")

    _setup_readline()
    context = Context() if not using_daemon else None

    # Show proactive suggestion at start
    if not using_daemon:
        try:
            from zeno.core.proactive import get_engine as get_proactive
            suggestion = get_proactive().check()
            if suggestion:
                print(f"{zeno_prefix()} {cyan(suggestion)}")
        except Exception:
            pass

    while True:
        try:
            raw = input(user_prefix()).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{zeno_prefix()} Goodbye!")
            break

        if not raw:
            continue

        if raw.lower() in ("exit", "quit", "q"):
            print(f"{zeno_prefix()} Goodbye!")
            break

        if using_daemon:
            response = proxy_request(raw, daemon_port)
            if response is None:
                print(f"{error_prefix()} Daemon unreachable. {dim('Falling back to local processing.')}")
                using_daemon = False
                context = Context()
                response = process_input(raw, context)
        else:
            handled = _handle_slash_or_shorthand(raw, context)
            if handled is not None:
                if handled:
                    print(f"{zeno_prefix()} {green(handled)}")
                continue
            response = process_input(raw, context)

        print(f"{zeno_prefix()} {green(response)}")


# ── TUI mode ──────────────────────────────────────────────────────────

def run_tui():
    try:
        from zeno.tui.app import ZenoTUI
    except ImportError:
        print(f"{error_prefix()} TUI mode requires 'textual'. Install: pip install \"zeno[tui]\"")
        sys.exit(1)
    from zeno.tui.app import ZenoTUI
    app = ZenoTUI()
    app.run()


# ── Entry point ───────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zeno",
        description="Zeno — On-Device Voice Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  zeno                                     Text mode\n"
            "  zeno --voice                              Push-to-talk voice\n"
            "  zeno --wake                               Wake word activation\n"
            "  zeno --native-wake                        VAD-based wake\n"
            "  zeno --tui                                Terminal UI\n"
            "  zeno --daemon                             Start background daemon\n"
            "  zeno --stop                               Stop daemon\n"
            "  zeno --status                             Daemon status\n"
            "  zeno --discover                           Browse plugin registry\n"
            "  zeno --doctor                             Run diagnostics\n"
            "  zeno web                                  Web dashboard\n"
            "  zeno --help                               Show global help\n"
            "\n"
            "In text mode, type /help for slash commands."
        ),
    )
    parser.add_argument(
        "-v", "--voice", action="store_true",
        help="Push-to-talk voice mode (listen once, process, speak)",
    )
    parser.add_argument(
        "-w", "--wake", action="store_true",
        help="Wake word mode (listen until 'zeno' or 'hey' is detected)",
    )
    parser.add_argument(
        "-c", "--continuous", action="store_true",
        help="Continuous mode (keep listening after each response)",
    )
    parser.add_argument(
        "-n", "--native-wake", action="store_true",
        help="Native VAD-based wake word (lower latency, uses termux-microphone-record)",
    )
    parser.add_argument(
        "--discover", nargs="?",
        const="__list__", default=None,
        help="Browse or install community plugins from the registry",
    )
    parser.add_argument(
        "--tui", action="store_true",
        help="Launch the Textual terminal UI",
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help=f"Start background daemon (web server on port {_DAEMON_PORT})",
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="Stop the running daemon",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show daemon status",
    )
    parser.add_argument(
        "--doctor", action="store_true",
        help="Run diagnostics (platform, store, NLU, ports, sync) and report issues",
    )
    parser.add_argument(
        "--daemon-port", type=int, default=_DAEMON_PORT,
        help=f"Port for daemon (default: {_DAEMON_PORT})",
    )
    parser.add_argument(
        "--no-sync", action="store_true",
        help="Disable LAN sync for daemon mode",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"Zeno v{_VERSION}",
        help="Show version and exit",
    )
    return parser


def _resolve_args(args: list[str]) -> argparse.Namespace:
    """Backwards compatibility: if only bare flags are passed, parse them."""
    parser = _build_parser()
    return parser.parse_args(args)


def main():
    args = _resolve_args(sys.argv[1:])

    if args.discover:
        from zeno.core.discover import discover
        discover(name=None if args.discover == "__list__" else args.discover)
        sys.exit(0)

    if args.doctor:
        from zeno.core.doctor import run_doctor
        sys.exit(run_doctor())

    # ── Daemon management ──
    if args.stop:
        from zeno.core.daemon import stop
        ok, msg = stop()
        print(f"{zeno_prefix()} {msg}")
        sys.exit(0 if ok else 1)

    if args.status:
        from zeno.core.daemon import status as daemon_status
        s = daemon_status()
        if s["running"]:
            print(f"{zeno_prefix()} Daemon is running {dim(f'(PID {s["pid"]}, port {s["port"] or "?"})')}")
        else:
            print(f"{zeno_prefix()} Daemon is not running")
        sys.exit(0)

    if args.daemon:
        from zeno.core.daemon import start
        ok, msg = start(port=args.daemon_port, sync=not args.no_sync)
        print(f"{zeno_prefix()} {msg}")
        sys.exit(0 if ok else 1)

    # ── Interactive modes ──
    if args.tui:
        run_tui()
        sys.exit(0)

    if args.continuous or args.voice or args.wake or args.native_wake:
        asyncio.run(run_voice_loop(
            require_wake=args.wake or args.native_wake,
            native_wake=args.native_wake,
        ))
    else:
        run_text_loop(daemon_port=args.daemon_port)


if __name__ == "__main__":
    main()
