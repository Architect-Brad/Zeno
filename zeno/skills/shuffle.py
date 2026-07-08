"""Zeno Shuffle Skill — shuffles music playback (stub)."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class ShuffleSkill(BaseSkill):
    intents = ["shuffle_music"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(
            "Shuffle mode isn't available yet — "
            "I'd need a music player integration."
        )
