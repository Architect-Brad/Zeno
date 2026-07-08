"""Direct tests for zeno/core/no_repeat.py — the shared picker used by
both response/engine.py and BaseSkill.choice_no_repeat()."""

import os
import tempfile

import zeno.memory.store as store_mod
from zeno.memory.store import Store
from zeno.core.no_repeat import pick_no_repeat


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)


def test_cycles_through_pool_before_repeating():
    pool = ["a", "b", "c", "d"]
    seen = {pick_no_repeat("k", pool) for _ in range(len(pool))}
    assert seen == set(pool)


def test_resets_after_full_cycle():
    pool = ["a", "b"]
    for _ in range(len(pool)):
        pick_no_repeat("reset_key", pool)
    # Doesn't raise, and picks from the pool again
    assert pick_no_repeat("reset_key", pool) in pool


def test_independent_keys_do_not_interfere():
    pool = ["x", "y"]
    pick_no_repeat("key_a", pool)
    pick_no_repeat("key_a", pool)  # exhausts key_a
    # key_b should still have both options
    seen_b = {pick_no_repeat("key_b", pool) for _ in range(2)}
    assert seen_b == set(pool)


def test_persists_across_separate_calls_as_if_stateless_caller():
    pool = ["1", "2", "3"]
    first = pick_no_repeat("persist_key", pool)
    remaining = {pick_no_repeat("persist_key", pool) for _ in range(2)}
    assert first not in remaining


def test_raises_on_empty_pool():
    try:
        pick_no_repeat("empty", [])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_works_with_non_string_items():
    pool = [(1, "a"), (2, "b"), (3, "c")]
    seen = {pick_no_repeat("tuples", pool) for _ in range(len(pool))}
    assert seen == set(pool)
