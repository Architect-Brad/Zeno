"""Zeno Timezone Skill — timezone lookup stub (no timezone DB)."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class TimezoneSkill(BaseSkill):
    intents = ["timezone_info"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(
            "Timezone conversion isn't available without a timezone database. "
            "I can tell you the current local time — just ask 'what time is it'!"
        )
