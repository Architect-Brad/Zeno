"""Zeno Notes Skill — save quick notes to ~/.zeno/notes.json."""

import json
import os
from pathlib import Path
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_NOTES_PATH = Path.home() / ".zeno" / "notes.json"


def _load_notes() -> list[str]:
    try:
        if _NOTES_PATH.exists():
            with open(_NOTES_PATH) as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_notes(notes: list[str]):
    _NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_NOTES_PATH, "w") as f:
        json.dump(notes, f)


class NotesSkill(BaseSkill):
    intents = ["take_note"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        raw = entities.raw.get("text", "")
        prefixes = [
            "take a note", "make a note", "write this down", "write a note",
            "save a note", "jot this down", "note this", "remember this",
        ]
        note = raw
        for prefix in prefixes:
            if raw.lower().startswith(prefix):
                note = raw[len(prefix):].strip().lstrip(", ")
                break
        if not note or note.lower() in prefixes:
            return self.say("What should I note down?")
        notes = _load_notes()
        notes.append(note)
        _save_notes(notes)
        return self.say(f"Noted: {note}")
