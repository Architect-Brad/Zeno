"""Zeno Playlist Skill — plays a specific playlist (stub)."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class PlaylistSkill(BaseSkill):
    intents = ["play_playlist"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(
            "Playlist playback isn't available yet — "
            "I'd need a music player integration."
        )
