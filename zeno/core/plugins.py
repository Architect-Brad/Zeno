"""
Zeno Plugin Loader — auto-discovers skills from plugin directories.
Scans ~/.zeno/plugins/ and any paths in ZENO_PLUGIN_PATH for BaseSkill subclasses.
"""

import importlib
import inspect
import os
import sys

from zeno.skills.base import BaseSkill


def _plugin_dirs() -> list[str]:
    dirs = []

    home = os.path.expanduser("~/.zeno/plugins")
    if os.path.isdir(home):
        dirs.append(home)

    env = os.environ.get("ZENO_PLUGIN_PATH", "")
    for p in env.split(":"):
        p = p.strip()
        if p and os.path.isdir(p):
            dirs.append(os.path.abspath(p))

    return dirs


def load_plugins() -> list[BaseSkill]:
    skills: list[BaseSkill] = []
    seen: set[str] = set()

    for d in _plugin_dirs():
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            path = os.path.join(d, fname)
            mod_name = f"_zeno_plugin_{os.path.splitext(fname)[0]}"

            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
            else:
                spec = importlib.util.spec_from_file_location(mod_name, path)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                try:
                    spec.loader.exec_module(mod)
                except Exception as e:
                    print(f"[Zeno] Plugin load failed: {fname} — {e}")
                    continue

            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    issubclass(obj, BaseSkill)
                    and obj is not BaseSkill
                    and obj.__name__ not in seen
                ):
                    try:
                        instance = obj()
                        skills.append(instance)
                        seen.add(obj.__name__)
                        print(f"[Zeno] Plugin loaded: {obj.__name__} from {fname}")
                    except Exception as e:
                        print(f"[Zeno] Plugin init failed: {obj.__name__} — {e}")

    return skills
