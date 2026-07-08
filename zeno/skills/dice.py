"""Zeno Dice Roll Skill — rolls a standard six-sided die."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_OUTCOMES: list[tuple[int, str]] = [
    (1, "You rolled a one! Better luck next time."),
    (2, "You rolled a two. Not bad!"),
    (3, "You rolled a three. Solid roll."),
    (4, "You rolled a four. Getting warm!"),
    (5, "You rolled a five! Almost perfect."),
    (6, "You rolled a six — lucky! 🎉"),
]


class DiceSkill(BaseSkill):
    intents = ["roll_dice"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        result, message = random.choice(_OUTCOMES)
        return self.say(message)
