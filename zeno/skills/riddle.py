"""Zeno Riddle Skill — asks random riddles."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_RIDDLES: list[tuple[str, str]] = [
    ("I speak without a mouth and hear without ears. I have no body, but I come alive with the wind. What am I?", "An echo!"),
    ("The more you take, the more you leave behind. What am I?", "Footsteps!"),
    ("I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?", "A map!"),
    ("What has keys but can't open locks?", "A piano!"),
    ("What can travel around the world while staying in a corner?", "A stamp!"),
    ("What has a head and a tail but no body?", "A coin!"),
    ("What gets wetter the more it dries?", "A towel!"),
    ("I can be cracked, made, told, and played. What am I?", "A joke!"),
    ("What belongs to you, but other people use it more than you?", "Your name!"),
    ("What has many teeth but can't bite?", "A comb!"),
    ("What runs all around a backyard yet never moves?", "A fence!"),
    ("What can you break, even if you never pick it up or touch it?", "A promise!"),
    ("I follow you all day long, but when the night falls, I'm gone. What am I?", "Your shadow!"),
    ("What goes up but never comes down?", "Your age!"),
    ("What has a neck but no head?", "A bottle!"),
    ("I am not alive, but I can grow. I don't have lungs, but I need air. What am I?", "Fire!"),
    ("What can fill a room but takes up no space?", "Light!"),
    ("David's parents have three sons: Snap, Crackle, and what's the third?", "David!"),
    ("What invention lets you look right through a wall?", "A window!"),
    ("What starts with E, ends with E, and has one letter in it?", "An envelope!"),
]


class RiddleSkill(BaseSkill):
    intents = ["riddle"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        riddle, answer = random.choice(_RIDDLES)
        return self.say(f"{riddle} ({answer})")
