"""
Zeno Base Skill — abstract interface all skills inherit from.
Provides response helpers and the slot-filling contract.
"""

from zeno.nlu.entity import Entities
from zeno.core.context import Context


class BaseSkill:
    """Abstract base for all Zeno skills."""

    intents: list[str] = []

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        raise NotImplementedError

    def fill_slot(self, slot: str, raw_text: str, context: Context) -> str:
        """Handle a slot-filling response when the user answers a question."""
        context.clear_awaiting()
        return self.pick("unknown")

    def say(self, message: str) -> str:
        return message

    def pick(self, phrase_key: str, **kwargs) -> str:
        # Delegates to response.engine, which has the same phrase keys
        # with richer variant pools (this used to have its own smaller,
        # disconnected copy of the same categories — two phrase pools
        # that could drift apart, with most skills stuck on the smaller
        # one purely because of which import they happened to use).
        from zeno.response.engine import pick as engine_pick
        return engine_pick(phrase_key, **kwargs)

    def choice_no_repeat(self, pool_key: str, pool: list):
        """Pick a random item from `pool`, avoiding items already shown
        this cycle. Once every item in the pool has been shown, the
        cycle resets. Persisted in the local store, so it holds across
        turns and even across restarts — a small fix for a pattern that
        makes a small joke/fact/quote pool feel repetitive fast (with
        plain random.choice, a 25-item pool has better-than-even odds of
        a repeat within about 6 picks).

        `pool` can be any indexable sequence (list of strings, list of
        tuples, etc.) — the item itself is returned, not its index.
        """
        from zeno.core.no_repeat import pick_no_repeat
        return pick_no_repeat(pool_key, pool)
