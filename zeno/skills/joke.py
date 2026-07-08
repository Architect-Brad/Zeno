"""Zeno Joke Skill — tells random jokes."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "What do you call a fake noodle? An impasta!",
    "Why did the scarecrow win an award? Because he was outstanding in his field!",
    "What do you call a bear with no teeth? A gummy bear!",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "What did the ocean say to the beach? Nothing, it just waved.",
    "Why did the bicycle fall over? Because it was two-tired!",
    "What do you call a fish wearing a bowtie? Sofishticated!",
    "Why did the math book look so sad? Because it had too many problems.",
    "What do you get when you cross a snowman and a vampire? Frostbite.",
    "How does a penguin build its house? Igloos it together!",
    "Why was the computer cold? It left its Windows open.",
    "What do you call a pig that does karate? A pork chop!",
    "Why did the golfer wear two pairs of pants? In case he got a hole in one.",
    "What did the zero say to the eight? Nice belt!",
    "Why did the tomato turn red? Because it saw the salad dressing!",
    "What do you call a lazy kangaroo? A pouch potato!",
    "Why did the coffee file a police report? It got mugged!",
    "What do you call a cow with no legs? Ground beef!",
    "How do you organize a space party? You planet!",
    "What did the grape do when it got stepped on? Nothing — it just let out a little wine.",
    "Why can't your nose be 12 inches long? Because then it would be a foot!",
    "What do you call a factory that sells generally okay products? A satis-factory.",
    "What do you call a snowman with a six-pack? An abdominal snowman!",
    "How does a scientist freshen their breath? With experi-mints!",
]


class JokeSkill(BaseSkill):
    intents = ["joke"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(self.choice_no_repeat("joke", _JOKES))
