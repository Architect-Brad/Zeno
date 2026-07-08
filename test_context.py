"""Tests for multi-turn slot-filling and context resolution."""

import os
import tempfile
from zeno.memory.store import Store
import zeno.memory.store as store_mod


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)


def test_alarm_slot_filling():
    from zeno.core.loop import process_input
    from zeno.core.context import Context

    ctx = Context()
    process_input("hey zeno", ctx)
    process_input("Marcus", ctx)

    r1 = process_input("set an alarm", ctx)
    assert "time" in r1.lower()
    assert ctx.awaiting() is not None

    r2 = process_input("7am", ctx)
    assert "07:00" in r2 or "7am" in r2.lower()
    assert ctx.awaiting() is None


def test_cancel_mid_slot_fill():
    from zeno.core.loop import process_input
    from zeno.core.context import Context

    ctx = Context()
    process_input("hey zeno", ctx)
    process_input("Sam", ctx)

    process_input("set a timer", ctx)
    assert ctx.awaiting() is not None

    process_input("never mind", ctx)
    assert ctx.awaiting() is None


def test_first_run_name_capture():
    from zeno.core.loop import process_input
    from zeno.core.context import Context
    from zeno.core.profile import load_profile

    ctx = Context()
    process_input("hey zeno", ctx)
    assert ctx.awaiting() is not None

    process_input("I'm Jordan", ctx)
    profile = load_profile()
    assert profile.name == "Jordan"


def test_semantic_intent_classification():
    from zeno.nlu.intent import classify_intent

    tests = [
        ("what time is it", "time_query"),
        ("what's the weather like", "weather_query"),
        ("set an alarm for 6am", "set_alarm"),
        ("remind me to buy groceries", "set_reminder"),
        ("thank you", "thanks"),
        ("goodbye", "farewell"),
        ("who are you", "identity_query"),
        ("i feel lonely", "emotional_distress"),
    ]

    for text, expected in tests:
        result = classify_intent(text)
        assert result.intent == expected, (
            f"'{text}' → {result.intent} (expected {expected}, conf={result.confidence:.2f})"
        )
        assert result.confidence >= 0.25, (
            f"'{text}' confidence too low: {result.confidence:.2f}"
        )


def test_entity_extraction_time():
    from zeno.nlu.entity import extract_entities

    e = extract_entities("set alarm for 7am", "set_alarm")
    assert e.time is not None
    assert "7" in e.time

    e = extract_entities("wake me at 6:30 am", "set_alarm")
    assert e.time is not None
    assert "06:30" in e.time or "6:30" in e.time


def test_entity_extraction_duration():
    from zeno.nlu.entity import extract_entities

    e = extract_entities("set a timer for 5 minutes", "set_timer")
    assert e.duration is not None
    assert "5" in e.duration


def test_intent_unknown():
    from zeno.nlu.intent import classify_intent

    result = classify_intent("purple monkey dishwasher")
    assert result.intent == "unknown", f"Should be unknown, got {result.intent}"
