"""Zeno Lyrics Skill — searches for song lyrics (stub)."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class LyricsSkill(BaseSkill):
    intents = ["lyrics_search"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(
            "Lyrics search isn't available yet — "
            "I'd need a lyrics API integration."
        )
