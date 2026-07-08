"""Tests for the proactive suggestion engine: trigger registration, cooldowns, idle gating."""

import os
import tempfile
import time
from unittest.mock import patch

import zeno.memory.store as store_mod
import zeno.memory.graph as graph_mod
from zeno.memory.store import Store
from zeno.memory.graph import KnowledgeGraph


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)

    fd2, path2 = tempfile.mkstemp(suffix=".db")
    os.close(fd2)
    graph_mod._graph = KnowledgeGraph(path=path2)

    import zeno.core.personalise as p
    p._personaliser = None
    import zeno.core.proactive as pr
    pr._engine = None


def _fresh_engine():
    from zeno.core.proactive import ProactiveEngine
    return ProactiveEngine()


def _mark_idle(engine, seconds_ago=700):
    engine.personaliser.store.set("personal.last_active", time.time() - seconds_ago)


def test_check_returns_none_when_not_idle():
    engine = _fresh_engine()
    engine.personaliser.store.set("personal.last_active", time.time())  # just active
    engine.register("always", lambda: "suggestion")
    assert engine.check() is None


def test_check_runs_registered_trigger_when_idle():
    engine = _fresh_engine()
    _mark_idle(engine)
    engine.register("always", lambda: "here's a suggestion")
    assert engine.check() == "here's a suggestion"


def test_check_skips_triggers_returning_none():
    engine = _fresh_engine()
    _mark_idle(engine)
    engine.register("silent", lambda: None)
    engine.register("vocal", lambda: "I have something to say")
    assert engine.check() == "I have something to say"


def test_check_respects_cooldown():
    engine = _fresh_engine()
    _mark_idle(engine)
    calls = {"n": 0}

    def trigger():
        calls["n"] += 1
        return "suggestion"

    engine.register("cooldown_test", trigger, cooldown=3600)
    first = engine.check()
    assert first == "suggestion"

    # Immediately checking again should be suppressed by cooldown
    _mark_idle(engine)
    second = engine.check()
    assert second is None
    assert calls["n"] == 1


def test_check_fires_again_after_cooldown_expires():
    engine = _fresh_engine()
    _mark_idle(engine)
    engine.register("short_cooldown", lambda: "ping", cooldown=1)

    assert engine.check() == "ping"

    # Fake that the cooldown has elapsed
    engine._last_triggered["short_cooldown"] = time.time() - 10
    _mark_idle(engine)
    assert engine.check() == "ping"


def test_check_swallows_trigger_exceptions_and_continues():
    engine = _fresh_engine()
    _mark_idle(engine)

    def broken():
        raise RuntimeError("boom")

    engine.register("broken", broken)
    engine.register("fallback", lambda: "still works")
    assert engine.check() == "still works"


def test_check_returns_none_when_no_triggers_fire():
    engine = _fresh_engine()
    _mark_idle(engine)
    engine.register("a", lambda: None)
    engine.register("b", lambda: None)
    assert engine.check() is None


def test_start_and_stop_schedule_background_timer():
    engine = _fresh_engine()
    engine.start(interval=1000)  # long interval so it never actually fires in test
    assert engine._running is True
    assert engine._timer is not None

    engine.stop()
    assert engine._running is False


# ---------------------------------------------------------------------------
# Built-in trigger functions
# ---------------------------------------------------------------------------

def test_time_based_suggestion_evening_winddown():
    from zeno.core.proactive import _time_based_suggestion

    class FakeDatetime:
        @staticmethod
        def now():
            class D:
                hour = 22
            return D()

    with patch("zeno.core.proactive.datetime", FakeDatetime):
        result = _time_based_suggestion()
    assert result is not None
    assert "sleep" in result.lower() or "alarm" in result.lower()


def test_time_based_suggestion_none_midday_without_routine():
    from zeno.core.proactive import _time_based_suggestion

    class FakeDatetime:
        @staticmethod
        def now():
            class D:
                hour = 14
            return D()

    with patch("zeno.core.proactive.datetime", FakeDatetime):
        result = _time_based_suggestion()
    assert result is None


def test_idle_suggestion_for_unknown_user():
    from zeno.core.proactive import _idle_suggestion
    from zeno.core.profile import Profile

    with patch("zeno.core.proactive.load_profile", return_value=Profile(name=None)):
        result = _idle_suggestion()
    assert result is not None
    assert "Zeno" in result


def test_idle_suggestion_none_for_known_user():
    from zeno.core.proactive import _idle_suggestion
    from zeno.core.profile import Profile

    with patch("zeno.core.proactive.load_profile", return_value=Profile(name="Jordan")):
        result = _idle_suggestion()
    assert result is None


def test_usage_based_suggestion_none_without_history():
    from zeno.core.proactive import _usage_based_suggestion
    assert _usage_based_suggestion() is None


def test_get_engine_returns_singleton_with_builtin_triggers():
    from zeno.core.proactive import get_engine
    engine = get_engine()
    names = [name for name, _, _ in engine._triggers]
    assert "time_based" in names
    assert "usage_based" in names
    assert "idle" in names
    assert get_engine() is engine
