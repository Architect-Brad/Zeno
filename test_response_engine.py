"""Tests for zeno/response/engine.py: fragment-based composition for
high-frequency categories, no-repeat cycling for everything else, and
the consolidation that removed BaseSkill's duplicate (smaller) phrase pool."""

import os
import tempfile

import zeno.memory.store as store_mod
from zeno.memory.store import Store


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)


# ---------------------------------------------------------------------------
# Fragment composition
# ---------------------------------------------------------------------------

def test_farewell_never_produces_double_spaces():
    from zeno.response.engine import pick
    for _ in range(30):
        result = pick("farewell")
        assert "  " not in result, f"double space in: {result!r}"


def test_thanks_never_produces_double_spaces():
    from zeno.response.engine import pick
    for _ in range(30):
        result = pick("thanks")
        assert "  " not in result, f"double space in: {result!r}"


def test_farewell_produces_more_unique_outputs_than_the_old_fixed_list():
    from zeno.response.engine import pick
    seen = {pick("farewell") for _ in range(40)}
    # The old fixed-list version had 14 possible full sentences; fragment
    # composition (8 openers x 6 tags, minus empty-tag collisions) should
    # comfortably clear that within 40 samples.
    assert len(seen) > 14


def test_composed_responses_start_with_a_known_opener():
    from zeno.response.engine import pick, _FRAGMENTS
    openers = set(_FRAGMENTS["thanks"]["opener"])
    for _ in range(20):
        result = pick("thanks")
        assert any(result.startswith(o) for o in openers), result


def test_empty_tag_returns_bare_opener():
    from zeno.response.engine import _compose
    from unittest.mock import patch
    with patch("zeno.response.engine.pick_no_repeat", side_effect=["Bye", ""]):
        assert _compose("farewell") == "Bye"


def test_punctuation_tag_attaches_without_space():
    from zeno.response.engine import _compose
    from unittest.mock import patch
    with patch("zeno.response.engine.pick_no_repeat", side_effect=["Bye", "!"]):
        assert _compose("farewell") == "Bye!"


def test_word_tag_attaches_with_single_space():
    from zeno.response.engine import _compose
    from unittest.mock import patch
    with patch("zeno.response.engine.pick_no_repeat", side_effect=["Bye", "for now."]):
        assert _compose("farewell") == "Bye for now."


def test_compose_returns_none_for_non_fragment_keys():
    from zeno.response.engine import _compose
    assert _compose("weather_report") is None
    assert _compose("timer_set") is None


def test_no_opener_tag_combination_is_redundant():
    """Systematic check across every possible combination — catches the
    class of bug where an opener and tag independently make sense but
    combine into something redundant, like 'Bye for now for now.' or
    'Talk soon — talk soon.', both of which were caught this way."""
    from zeno.response.engine import _FRAGMENTS

    for key, grammar in _FRAGMENTS.items():
        for opener in grammar["opener"]:
            for tag in grammar["tag"]:
                if not tag:
                    continue
                stripped_tag = tag.strip(" —,.!")
                if stripped_tag and stripped_tag.lower() in opener.lower():
                    raise AssertionError(
                        f"[{key}] opener {opener!r} + tag {tag!r} is redundant"
                    )
                tag_words = set(stripped_tag.lower().split())
                opener_words = set(opener.lower().split())
                overlap = tag_words & opener_words
                assert len(overlap) < 2, (
                    f"[{key}] opener {opener!r} + tag {tag!r} shares too many words: {overlap}"
                )


# ---------------------------------------------------------------------------
# No-repeat cycling for plain template categories
# ---------------------------------------------------------------------------

def test_plain_template_category_cycles_before_repeating():
    from zeno.response.engine import pick, _PHRASES
    pool = _PHRASES["timer_cancelled"]
    seen = set()
    for _ in range(len(pool)):
        seen.add(pick("timer_cancelled"))
    assert len(seen) == len(pool)


def test_pick_fills_kwargs_after_composition_or_template_selection():
    from zeno.response.engine import pick
    result = pick("weather_report", temp=72, unit="F", conditions="clear", location="Austin")
    assert "72" in result and "Austin" in result


def test_unknown_key_falls_back_to_default_message():
    from zeno.response.engine import pick
    assert pick("some_key_that_does_not_exist") == "I'm not sure about that"


# ---------------------------------------------------------------------------
# Time-aware greeting
# ---------------------------------------------------------------------------

def test_time_aware_greeting_returns_a_string():
    from zeno.response.engine import pick
    result = pick("greeting")
    assert isinstance(result, str) and result


def test_time_aware_greeting_cycles_within_its_time_bucket():
    from zeno.response.engine import _time_aware_greeting, _AM_PM_TEMPLATES
    import time
    from unittest.mock import patch

    class FixedTime:
        tm_hour = 9  # morning

    with patch("time.localtime", return_value=FixedTime()):
        pool = _AM_PM_TEMPLATES["morning"]
        seen = {_time_aware_greeting() for _ in range(len(pool))}
    assert len(seen) == len(pool)


# ---------------------------------------------------------------------------
# BaseSkill.pick() consolidation — no more separate, smaller phrase pool
# ---------------------------------------------------------------------------

def test_base_skill_no_longer_has_its_own_phrases_dict():
    import zeno.skills.base as base_mod
    assert not hasattr(base_mod, "_PHRASES")


def test_base_skill_pick_uses_the_richer_engine_pool():
    from zeno.skills.base import BaseSkill
    from zeno.response.engine import _PHRASES as engine_phrases

    skill = BaseSkill()
    seen = set()
    for _ in range(len(engine_phrases["unknown"])):
        seen.add(skill.pick("unknown"))
    assert len(seen) == len(engine_phrases["unknown"])


def test_base_skill_pick_and_response_engine_pick_share_state():
    """Since BaseSkill.pick() now delegates to response.engine.pick(),
    a skill using self.pick(...) and code using response_pick(...)
    directly should be cycling through the *same* pool, not two
    independent ones."""
    from zeno.skills.base import BaseSkill
    from zeno.response.engine import pick as engine_pick, _PHRASES

    skill = BaseSkill()
    pool = _PHRASES["unknown"]
    seen = set()
    for i in range(len(pool)):
        picker = skill.pick if i % 2 == 0 else (lambda k: engine_pick(k))
        seen.add(picker("unknown"))
    assert len(seen) == len(pool)  # no repeats even though picks alternate sources
