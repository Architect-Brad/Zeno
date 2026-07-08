"""
Shared no-repeat picker.

Plain random.choice() over a small pool repeats surprisingly fast — a
pool of even 10-15 items has better-than-even odds of a repeat within
a handful of picks. This cycles through the whole pool before allowing
any repeats, persisted in the local store so it holds across turns and
even across restarts.

Used by:
  - zeno/response/engine.py, for canned phrase variety across every
    response category (greetings, confirmations, status reports, etc.)
  - zeno/skills/base.py's BaseSkill.choice_no_repeat(), for content
    pools like jokes/facts/quotes/riddles.

Both used to have their own copy of this logic; it's centralized here
so there's one implementation to test and reason about.
"""

import random


def pick_no_repeat(pool_key: str, pool: list):
    """Pick a random item from `pool`, avoiding items already shown this
    cycle. Once every item has been shown, the cycle resets.

    `pool` can be any indexable sequence (list of strings, list of
    tuples, etc.) — the item itself is returned, not its index.
    """
    if not pool:
        raise ValueError("pick_no_repeat: pool is empty")
    from zeno.memory.store import get_store
    store = get_store()
    store_key = f"content_no_repeat.{pool_key}"
    shown = set(store.get(store_key, []))
    available = [i for i in range(len(pool)) if i not in shown]
    if not available:
        shown = set()
        available = list(range(len(pool)))
    idx = random.choice(available)
    shown.add(idx)
    store.set(store_key, list(shown))
    return pool[idx]
