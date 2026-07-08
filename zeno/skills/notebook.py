"""Zeno Notebook Skill — read saved notes from ~/.zeno/notes.json."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.skills.notes import _load_notes


class NotebookSkill(BaseSkill):
    intents = ["read_notes"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        notes = _load_notes()
        if not notes:
            return self.say("You don't have any saved notes.")
        lines = [f"{i+1}. {n}" for i, n in enumerate(notes)]
        return self.say("Your notes:\n" + "\n".join(lines))
