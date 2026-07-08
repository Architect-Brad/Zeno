"""Tests for the personalisation engine: usage learning, preferences, routines."""

import os
import tempfile

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


def _fresh_personaliser():
    from zeno.core.personalise import Personaliser
    return Personaliser()


def test_log_interaction_updates_usage_stats():
    p = _fresh_personaliser()
    p.log_interaction("weather_query", None, "It's sunny")
    p.log_interaction("weather_query", None, "It's sunny")
    p.log_interaction("time_query", None, "It's noon")

    frequent = p.get_frequent_intents(top_n=5)
    stats = dict((name, count) for name, count in frequent)
    assert stats.get("weather_query") == 2
    assert stats.get("time_query") == 1


def test_session_counter_increments_after_gap():
    p = _fresh_personaliser()
    store = p.store

    # First interaction establishes a baseline, no gap yet
    store.set("personal.last_active", 0.0)
    p._update_session()
    assert store.get("personal.sessions", 0) == 0

    # Simulate a session more than an hour old, then a new interaction
    store.set("personal.last_active", 1.0)
    p._update_session()
    assert store.get("personal.sessions", 0) == 1


def test_learn_and_get_preference_round_trip():
    p = _fresh_personaliser()
    p.learn_preference("favorite_color", "blue")
    assert p.get_preference("favorite_color") == "blue"
    assert p.get_preference("nonexistent", "default") == "default"


def test_learn_location_dedupes_and_orders_most_recent_first():
    p = _fresh_personaliser()
    p.learn_location("Boston")
    p.learn_location("Seattle")
    p.learn_location("boston")  # case-insensitive dupe of Boston, should move to front

    locations = p.get_preference("frequent_locations", [])
    assert locations[0].lower() == "boston"
    assert len(locations) == 2  # Boston/boston collapsed into one entry


def test_learn_location_caps_at_ten():
    p = _fresh_personaliser()
    for i in range(15):
        p.learn_location(f"City{i}")
    locations = p.get_preference("frequent_locations", [])
    assert len(locations) == 10


def test_volume_preference_suggests_most_common_level():
    p = _fresh_personaliser()
    for level in [5, 5, 5, 8, 8]:
        p.learn_volume_preference(level)
    assert p.get_suggested_volume() == 5


def test_suggested_volume_none_when_no_history():
    p = _fresh_personaliser()
    assert p.get_suggested_volume() is None


def test_time_of_day_greeting_uses_profile_name():
    from zeno.core.profile import Profile
    p = _fresh_personaliser()
    profile = Profile(name="Sam")
    greeting = p.time_of_day_greeting(profile)
    assert "Sam" in greeting


def test_time_of_day_greeting_falls_back_when_unnamed():
    from zeno.core.profile import Profile
    p = _fresh_personaliser()
    profile = Profile(name=None)
    greeting = p.time_of_day_greeting(profile)
    assert "there" in greeting


def test_conversation_memory_round_trip():
    p = _fresh_personaliser()
    p.log_conversation("what's the weather", "It's sunny", "weather_query")
    p.log_conversation("thanks", "you're welcome", "thanks")

    memory = p.get_conversation_memory(n=5)
    assert len(memory) == 2
    # Most recent first
    assert memory[0]["user"] == "thanks"
    assert memory[1]["intent"] == "weather_query"


def test_should_proactive_false_when_never_active():
    p = _fresh_personaliser()
    p.store.delete("personal.last_active")
    assert p.should_proactive() is False


def test_should_proactive_true_after_long_idle():
    import time
    p = _fresh_personaliser()
    p.store.set("personal.last_active", time.time() - 700)
    assert p.should_proactive() is True


def test_should_proactive_false_when_recently_active():
    import time
    p = _fresh_personaliser()
    p.store.set("personal.last_active", time.time() - 5)
    assert p.should_proactive() is False


def test_get_personaliser_returns_singleton():
    from zeno.core.personalise import get_personaliser
    first = get_personaliser()
    second = get_personaliser()
    assert first is second
