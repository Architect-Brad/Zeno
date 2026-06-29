"""Zeno Quote Skill — gives an inspirational quote."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_QUOTES = [
    "\"The only way to do great work is to love what you do.\" — Steve Jobs",
    "\"In the middle of every difficulty lies opportunity.\" — Albert Einstein",
    "\"Believe you can and you're halfway there.\" — Theodore Roosevelt",
    "\"The future belongs to those who believe in the beauty of their dreams.\" — Eleanor Roosevelt",
    "\"Success is not final, failure is not fatal: it is the courage to continue that counts.\" — Winston Churchill",
    "\"What lies behind us and what lies before us are tiny matters compared to what lies within us.\" — Ralph Waldo Emerson",
    "\"The only impossible journey is the one you never begin.\" — Tony Robbins",
    "\"Everything you've ever wanted is on the other side of fear.\" — George Addair",
    "\"Happiness is not something ready made. It comes from your own actions.\" — Dalai Lama",
    "\"Your time is limited, don't waste it living someone else's life.\" — Steve Jobs",
    "\"It does not matter how slowly you go as long as you do not stop.\" — Confucius",
    "\"The best time to plant a tree was 20 years ago. The second best time is now.\" — Chinese Proverb",
    "\"You miss 100% of the shots you don't take.\" — Wayne Gretzky",
    "\"Whether you think you can or you think you can't, you're right.\" — Henry Ford",
    "\"Life is what happens when you're busy making other plans.\" — John Lennon",
    "\"The purpose of our lives is to be happy.\" — Dalai Lama",
    "\"Get busy living or get busy dying.\" — Stephen King",
    "\"You have within you right now, everything you need to deal with whatever the world can throw at you.\" — Brian Tracy",
    "\"If you want to lift yourself up, lift up someone else.\" — Booker T. Washington",
    "\"The greatest glory in living lies not in never falling, but in rising every time we fall.\" — Nelson Mandela",
]


class QuoteSkill(BaseSkill):
    intents = ["quote"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return self.say(random.choice(_QUOTES))
