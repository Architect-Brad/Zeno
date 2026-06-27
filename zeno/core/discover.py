"""Zeno Plugin Discovery — browse and install community plugins."""

import json
import urllib.request
import urllib.error
import sys
import os
from pathlib import Path

_PLUGIN_INDEX_URL = "https://raw.githubusercontent.com/Architect-Brad/zeno-plugins/main/index.json"
_PLUGINS_DIR = Path.home() / ".zeno" / "plugins"

_LOCAL_INDEX: list[dict] = [
    {
        "id": "spotify_control",
        "description": "Spotify playback control (play, pause, skip, search)",
        "url": "https://raw.githubusercontent.com/Architect-Brad/zeno-plugins/main/spotify_control.py",
        "author": "The Architect",
        "version": "1.0.0",
    },
    {
        "id": "todo_list",
        "description": "Simple in-memory todo list manager",
        "url": "https://raw.githubusercontent.com/Architect-Brad/zeno-plugins/main/todo_list.py",
        "author": "The Architect",
        "version": "1.0.0",
    },
    {
        "id": "covid_stats",
        "description": "Fetch COVID-19 case counts by country",
        "url": "https://raw.githubusercontent.com/Architect-Brad/zeno-plugins/main/covid_stats.py",
        "author": "The Architect",
        "version": "1.0.0",
    },
    {
        "id": "crypto_price",
        "description": "Check cryptocurrency prices via CoinGecko",
        "url": "https://raw.githubusercontent.com/Architect-Brad/zeno-plugins/main/crypto_price.py",
        "author": "The Architect",
        "version": "1.0.0",
    },
    {
        "id": "lyrics_finder",
        "description": "Look up song lyrics by title and artist",
        "url": "https://raw.githubusercontent.com/Architect-Brad/zeno-plugins/main/lyrics_finder.py",
        "author": "The Architect",
        "version": "1.0.0",
    },
]


def _ensure_plugins_dir():
    _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_index() -> list[dict]:
    """Fetch plugin index from GitHub; fall back to local copy on error."""
    try:
        req = urllib.request.Request(_PLUGIN_INDEX_URL, headers={"User-Agent": "Zeno/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            remote = json.loads(resp.read().decode())
            if isinstance(remote, list) and remote:
                return remote
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        print(f"[Zeno] Could not fetch remote plugin index: {e}")
        print(f"[Zeno] Using local plugin registry ({len(_LOCAL_INDEX)} plugins).")
    return list(_LOCAL_INDEX)


def install_plugin(plugin_id: str, plugins: list[dict]) -> bool:
    """Download a plugin.py file to ~/.zeno/plugins/."""
    plugin = next((p for p in plugins if p.get("id") == plugin_id), None)
    if not plugin:
        print(f"[Zeno] Unknown plugin: {plugin_id}")
        return False

    url = plugin.get("url") or plugin.get("source", "")
    if not url:
        print(f"[Zeno] No download URL for {plugin_id}")
        return False

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Zeno/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.read().decode()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"[Zeno] Download failed: {e}")
        return False

    _ensure_plugins_dir()
    dest = _PLUGINS_DIR / f"{plugin_id}.py"
    with open(dest, "w") as f:
        f.write(code)
    print(f"[Zeno] Installed plugin '{plugin_id}' to {dest}")
    return True


def discover():
    plugins = fetch_index()
    if not plugins:
        print("[Zeno] No community plugins available.")
        return

    print(f"\n{'Plugin':<24} {'Version':<10} {'Description'}")
    print("-" * 72)
    for p in plugins:
        pid = p.get("id", "?")
        ver = p.get("version", "?")
        desc = p.get("description", "")[:55]
        print(f"  {pid:<22} {ver:<8} {desc}")
    print()

    # Check for install argument
    args = [a for a in sys.argv[1:] if a != "--discover"]
    install_id = None
    for a in args:
        if not a.startswith("-"):
            install_id = a
            break

    if install_id:
        install_plugin(install_id, plugins)
    else:
        print("To install: python -m zeno --discover <plugin_id>")
