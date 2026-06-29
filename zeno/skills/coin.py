"""Zeno Coin Flip Skill — flips a coin for heads or tails."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_RESULTS = [
    "It's heads!",
    "It's tails!",
    "Heads!",
    "Tails!",
    "It landed on heads.",
    "It landed on tails.",
    "Heads it is!",
    "Tails it is!",
]


class CoinSkill(BaseSkill):
    intents = ["flip_coin"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(random.choice(_RESULTS))
