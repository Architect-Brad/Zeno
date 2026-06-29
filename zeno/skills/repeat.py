"""Zeno Repeat Skill — toggles repeat mode (stub)."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class RepeatSkill(BaseSkill):
    intents = ["repeat_mode"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(
            "Repeat mode isn't available yet — "
            "I'd need a music player integration."
        )
