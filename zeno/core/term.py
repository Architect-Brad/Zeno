"""Terminal color and style utilities for Zeno's CLI."""

import os
import sys
import shutil


_STYLES = {
    "reset": "0",
    "bold": "1",
    "dim": "2",
    "italic": "3",
    "underline": "4",
    # foreground
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
    # bright foreground
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
    # background
    "bg_black": "40",
    "bg_red": "41",
    "bg_green": "42",
    "bg_yellow": "43",
    "bg_blue": "44",
    "bg_magenta": "45",
    "bg_cyan": "46",
    "bg_white": "47",
}


def _color_enabled() -> bool:
    if "NO_COLOR" in os.environ:
        return False
    if "FORCE_COLOR" in os.environ:
        return True
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


def style(text: str, *codes: str) -> str:
    if not _color_enabled():
        return text
    if not codes:
        return text
    seq = ";".join(_STYLES.get(c, c) for c in codes)
    return f"\033[{seq}m{text}\033[0m"


def green(text: str) -> str:
    return style(text, "green")


def cyan(text: str) -> str:
    return style(text, "cyan")


def yellow(text: str) -> str:
    return style(text, "yellow")


def red(text: str) -> str:
    return style(text, "red")


def bold(text: str) -> str:
    return style(text, "bold")


def dim(text: str) -> str:
    return style(text, "dim")


def zeno_prefix() -> str:
    return cyan("[Zeno]")


def error_prefix() -> str:
    return red("[Error]")


def user_prefix() -> str:
    return green("> ")


def terminal_width() -> int:
    return shutil.get_terminal_size((80, 20)).columns


def strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)
