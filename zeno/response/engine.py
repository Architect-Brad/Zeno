"""
Zeno Response Engine — response selection utilities.
"""

import random


_PHRASES: dict[str, list[str]] = {
    "greeting": [
        "Hey", "Hello", "Hi", "Hey there", "Hi there",
    ],
    "greeting_morning": [
        "Good morning", "Morning", "Hey, good morning",
    ],
    "greeting_evening": [
        "Good evening", "Evening", "Hey, good evening",
    ],
    "farewell": [
        "Bye", "See you", "Take care", "Later", "Goodbye",
    ],
    "thanks": [
        "You're welcome", "No problem", "Happy to help", "Anytime",
    ],
    "affirm_received": [
        "Got it", "Okay", "Sure", "Alright", "On it",
    ],
    "deny_received": [
        "Okay, no problem", "Alright", "Fair enough", "Got it",
    ],
    "cancel": [
        "Cancelled", "Alright, forget it", "Consider it done — or not done",
    ],
    "identity": [
        "I'm Zeno, your local voice assistant. I can handle timers, alarms, reminders, weather, calculations, and system controls. Everything stays on your device.",
    ],
    "distress_response": [
        "I hear you. You're not alone. Please reach out to someone you trust. You can also contact a crisis helpline — they're free, confidential, and available 24/7.",
    ],
    "unknown": [
        "I'm not sure about that one", "I don't understand",
        "Could you rephrase that", "Not sure what you mean",
    ],
    "low_confidence": [
        "Did you mean '{intent}'?", "Not sure I caught that — were you asking about {intent}?",
        "I'm a bit fuzzy on that — are you looking for {intent}?",
    ],
}


def pick(phrase_key: str, **kwargs) -> str:
    phrases = _PHRASES.get(phrase_key, ["I'm not sure about that"])
    phrase = random.choice(phrases)
    if kwargs:
        phrase = phrase.format(**kwargs)
    return phrase
