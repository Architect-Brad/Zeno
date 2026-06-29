"""Zeno Fact Skill — shares a random interesting fact."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_FACTS = [
    "A group of flamingos is called a 'flamboyance'.",
    "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still edible.",
    "Octopuses have three hearts, nine brains, and blue blood.",
    "Bananas are berries, but strawberries are not.",
    "A day on Venus is longer than a year on Venus.",
    "The Eiffel Tower can be 15 cm taller during the summer due to thermal expansion.",
    "Wombat poop is cube-shaped to prevent it from rolling away.",
    "A jiffy is an actual unit of time: 1/100th of a second.",
    "Cleopatra lived closer in time to the moon landing than to the construction of the Great Pyramid of Giza.",
    "A single cloud can weigh over a million pounds.",
    "The shortest war in history lasted only 38 minutes between Britain and Zanzibar in 1896.",
    "A snail can sleep for three years.",
    "The world's oldest known recipe is for beer.",
    "A bolt of lightning contains enough energy to toast 100,000 slices of bread.",
    "Penguins propose to their mates with a pebble.",
    "There are more trees on Earth than stars in the Milky Way galaxy.",
    "Your stomach gets a new lining every 3-4 days to avoid digesting itself.",
    "The dot over the letters 'i' and 'j' is called a tittle.",
    "The longest hiccuping spree lasted 68 years.",
    "A small child could theoretically pass through a black hole due to spaghettification.",
]


class FactSkill(BaseSkill):
    intents = ["random_fact"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say("Did you know? " + random.choice(_FACTS))
