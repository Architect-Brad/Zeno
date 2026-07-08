"""Tests for BaseSkill.choice_no_repeat and the content skills that use it."""

import os
import tempfile

import zeno.memory.store as store_mod
from zeno.memory.store import Store
from zeno.skills.base import BaseSkill


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)


def test_choice_no_repeat_cycles_through_whole_pool_before_repeating():
    skill = BaseSkill()
    pool = ["a", "b", "c", "d", "e"]
    seen = [skill.choice_no_repeat("test_pool", pool) for _ in range(len(pool))]
    # Every item shown exactly once across a full cycle
    assert sorted(seen) == sorted(pool)


def test_choice_no_repeat_resets_after_full_cycle():
    skill = BaseSkill()
    pool = ["a", "b", "c"]
    first_cycle = {skill.choice_no_repeat("cycle_test", pool) for _ in range(len(pool))}
    assert first_cycle == set(pool)
    # Next pick starts a fresh cycle rather than raising or hanging
    next_pick = skill.choice_no_repeat("cycle_test", pool)
    assert next_pick in pool


def test_choice_no_repeat_persists_across_skill_instances():
    pool = ["x", "y", "z"]
    skill1 = BaseSkill()
    first = skill1.choice_no_repeat("persist_test", pool)

    skill2 = BaseSkill()  # fresh instance, same underlying store
    remaining = {skill2.choice_no_repeat("persist_test", pool) for _ in range(2)}
    assert first not in remaining  # already shown, shouldn't repeat until cycle resets


def test_choice_no_repeat_different_keys_are_independent():
    skill = BaseSkill()
    pool = ["1", "2"]
    skill.choice_no_repeat("key_a", pool)
    skill.choice_no_repeat("key_a", pool)  # exhausts key_a's cycle
    # key_b should be unaffected by key_a's history
    result = skill.choice_no_repeat("key_b", pool)
    assert result in pool


def test_choice_no_repeat_works_with_tuples():
    skill = BaseSkill()
    pool = [("q1", "a1"), ("q2", "a2")]
    result = skill.choice_no_repeat("riddle_test", pool)
    assert result in pool


def test_choice_no_repeat_raises_on_empty_pool():
    skill = BaseSkill()
    try:
        skill.choice_no_repeat("empty_test", [])
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Content skills wired to the no-repeat picker
# ---------------------------------------------------------------------------

def test_joke_skill_does_not_repeat_until_pool_exhausted():
    from zeno.skills.joke import JokeSkill, _JOKES
    from zeno.nlu.entity import Entities
    from zeno.core.context import Context

    skill = JokeSkill()
    seen = set()
    for _ in range(len(_JOKES)):
        seen.add(skill.handle("joke", Entities(), Context()))
    assert len(seen) == len(_JOKES)  # no duplicates in one full cycle


def test_fact_skill_prefixes_and_does_not_repeat():
    from zeno.skills.fact import FactSkill, _FACTS
    from zeno.nlu.entity import Entities
    from zeno.core.context import Context

    skill = FactSkill()
    seen = set()
    for _ in range(len(_FACTS)):
        result = skill.handle("random_fact", Entities(), Context())
        assert result.startswith("Did you know?")
        seen.add(result)
    assert len(seen) == len(_FACTS)


def test_quote_skill_does_not_repeat_until_pool_exhausted():
    from zeno.skills.quote import QuoteSkill, _QUOTES
    from zeno.nlu.entity import Entities
    from zeno.core.context import Context

    skill = QuoteSkill()
    seen = set()
    for _ in range(len(_QUOTES)):
        seen.add(skill.handle("quote", Entities(), Context()))
    assert len(seen) == len(_QUOTES)


def test_riddle_skill_does_not_repeat_until_pool_exhausted():
    from zeno.skills.riddle import RiddleSkill, _RIDDLES
    from zeno.nlu.entity import Entities
    from zeno.core.context import Context

    skill = RiddleSkill()
    seen = set()
    for _ in range(len(_RIDDLES)):
        seen.add(skill.handle("riddle", Entities(), Context()))
    assert len(seen) == len(_RIDDLES)
