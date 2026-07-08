"""Zeno Currency Skill — currency conversion stub (no live API)."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class CurrencySkill(BaseSkill):
    intents = ["currency_convert"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(
            "Live currency conversion isn't available yet. "
            "I'd need an exchange rate API. "
            "For now, try a search engine for current rates."
        )
