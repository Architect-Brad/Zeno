"""Tests for ConversationSkill's name-capture flow.

Regression context: fill_slot("name", ...) used to save almost anything
the person said as their name, including no-op replies like "thanks" or
"hey" — the entity-extraction path had a small denylist, but the raw-text
fallback path (used when entity extraction found nothing) had none at
all, so saying "thanks" right after being asked your name would save
"Thanks" as your name.
"""

import os
import tempfile

import zeno.memory.store as store_mod
from zeno.memory.store import Store
from zeno.skills.conversation import ConversationSkill
from zeno.core.context import Context


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)


def _fresh_context_awaiting_name() -> Context:
    ctx = Context()
    ctx.await_slot("introduce", "name")
    return ctx


def test_common_conversational_words_are_not_captured_as_names():
    skill = ConversationSkill()
    for word in ("thanks", "hey", "bye", "ok", "sorry", "nevermind"):
        ctx = _fresh_context_awaiting_name()
        result = skill.fill_slot("name", word, ctx)
        assert "worries" in result.lower() or "what can i help" in result.lower(), \
            f"{word!r} should not have been treated as a name reply, got: {result!r}"


def test_conversational_words_do_not_get_saved_to_profile():
    from zeno.core.profile import load_profile
    skill = ConversationSkill()
    for word in ("thanks", "hey", "stop"):
        ctx = _fresh_context_awaiting_name()
        skill.fill_slot("name", word, ctx)
        assert load_profile().name != word.title()


def test_real_name_is_still_captured():
    from zeno.core.profile import load_profile
    skill = ConversationSkill()
    ctx = _fresh_context_awaiting_name()
    result = skill.fill_slot("name", "Alex", ctx)
    assert "Alex" in result
    assert load_profile().name == "Alex"


def test_real_name_with_filler_prefix_is_captured():
    from zeno.core.profile import load_profile
    skill = ConversationSkill()
    ctx = _fresh_context_awaiting_name()
    skill.fill_slot("name", "call me Jordan", ctx)
    assert load_profile().name == "Jordan"


def test_name_capture_clears_awaiting_either_way():
    ctx = _fresh_context_awaiting_name()
    skill = ConversationSkill()
    skill.fill_slot("name", "thanks", ctx)
    assert ctx.awaiting() is None


def test_end_to_end_thanks_after_greeting_does_not_become_name():
    """Full path through the real conversation loop, matching the
    original bug report: greet, then say 'thanks' while the name slot
    is open."""
    from zeno.core.loop import process_input
    from zeno.core.profile import load_profile

    ctx = Context()
    process_input("hey", ctx)  # triggers the "what should I call you?" prompt
    process_input("thanks", ctx)
    assert load_profile().name is None


def test_end_to_end_real_name_after_greeting_still_works():
    from zeno.core.loop import process_input
    from zeno.core.profile import load_profile

    ctx = Context()
    process_input("hey", ctx)
    process_input("Sam", ctx)
    assert load_profile().name == "Sam"
