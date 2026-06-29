"""Zeno Clear Notes Skill — deletes all saved notes."""

from pathlib import Path
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_NOTES_PATH = Path.home() / ".zeno" / "notes.json"


class ClearSkill(BaseSkill):
    intents = ["clear_notes"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        try:
            if _NOTES_PATH.exists():
                _NOTES_PATH.unlink()
                return self.say("All notes cleared.")
            return self.say("No notes to clear.")
        except OSError:
            return self.say("Couldn't clear notes.")
