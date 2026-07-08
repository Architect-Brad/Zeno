"""Registration-integrity checks for the skill/intent wiring.

These exist because of a real bug found in review: SearchSkill and
NewsSkill both claimed 'news_query', and because SearchSkill was
registered later in _BUILTIN_SKILLS, its weaker DuckDuckGo fallback
silently won every time — NewsSkill's real RSS-based implementation
was completely unreachable. Nothing failed loudly; it just quietly
gave worse answers forever. These tests make that class of bug fail
a test run instead of hiding in registration order.
"""

from collections import defaultdict


def test_no_intent_is_claimed_by_more_than_one_builtin_skill():
    from zeno.core.loop import _BUILTIN_SKILLS

    owners: dict[str, list[str]] = defaultdict(list)
    for skill in _BUILTIN_SKILLS:
        for intent in skill.intents:
            owners[intent].append(type(skill).__name__)

    conflicts = {intent: names for intent, names in owners.items() if len(names) > 1}
    assert not conflicts, (
        f"These intents are claimed by more than one skill, so the skill "
        f"registered later silently wins and the other is dead code: {conflicts}"
    )


def test_every_trained_intent_has_a_registered_handler():
    from zeno.nlu.intent import TRAINING_DATA
    from zeno.core.loop import _BUILTIN_SKILLS

    handled = set()
    for skill in _BUILTIN_SKILLS:
        handled.update(skill.intents)

    trained = set(TRAINING_DATA.keys())
    unhandled = trained - handled
    assert not unhandled, (
        f"These intents have training data (so the classifier can return "
        f"them) but no skill handles them, so they'd fall through to the "
        f"generic 'unknown' response: {sorted(unhandled)}"
    )


def test_intent_map_actually_resolves_every_trained_intent():
    """End-to-end version of the above: rebuild the real intent map and
    confirm every trained intent resolves to a skill instance."""
    from zeno.nlu.intent import TRAINING_DATA
    from zeno.core import loop

    loop._rebuild()
    missing = [i for i in TRAINING_DATA if i not in loop._INTENT_MAP]
    assert not missing, f"No skill registered for: {missing}"
