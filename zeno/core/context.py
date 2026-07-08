"""
Zeno Context Manager
Tracks conversation state within a session.
Resolves references like "it", "that", "the same one".
Handles multi-turn slot-filling (Zeno asks a question, expects a direct answer next).
"""

from dataclasses import dataclass, field
from zeno.nlu.entity import Entities


@dataclass
class Turn:
    intent: str
    entities: Entities
    response: str


@dataclass
class AwaitingSlot:
    intent: str
    slot: str


class Context:
    def __init__(self):
        self._turns: list[Turn] = []
        self._pending: dict = {}
        self._awaiting: AwaitingSlot | None = None

    def push(self, intent: str, entities: Entities, response: str):
        self._turns.append(Turn(intent, entities, response))

    def last(self) -> Turn | None:
        return self._turns[-1] if self._turns else None

    def last_intent(self) -> str | None:
        return self._turns[-1].intent if self._turns else None

    def last_entities(self) -> Entities | None:
        return self._turns[-1].entities if self._turns else None

    def set_pending(self, key: str, value):
        self._pending[key] = value

    def get_pending(self, key: str):
        return self._pending.get(key)

    def clear_pending(self):
        self._pending.clear()

    def await_slot(self, intent: str, slot: str):
        self._awaiting = AwaitingSlot(intent=intent, slot=slot)

    def awaiting(self) -> AwaitingSlot | None:
        return self._awaiting

    def clear_awaiting(self):
        self._awaiting = None

    def resolve(self, entities: Entities) -> Entities:
        prev = self.last_entities()
        if not prev:
            return entities

        if entities.time is None and prev.time:
            entities.time = prev.time
        if entities.app_name is None and prev.app_name:
            entities.app_name = prev.app_name
        if entities.duration is None and prev.duration:
            entities.duration = prev.duration
        if entities.location is None and prev.location:
            entities.location = prev.location
        if entities.raw_target is None and prev.raw_target:
            entities.raw_target = prev.raw_target

        return entities

    def turn_count(self) -> int:
        return len(self._turns)
