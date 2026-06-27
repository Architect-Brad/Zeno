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
    "weather_report": [
        "It's {temp}{unit} and {conditions} in {location}.",
        "Currently {temp}{unit} with {conditions} in {location}.",
        "The weather in {location} is {temp}{unit} and {conditions}.",
    ],
    "weather_no_location": [
        "I don't know where. Tell me a city or set your location in settings.",
        "Where should I check the weather for?",
    ],
    "weather_unavailable": [
        "Couldn't fetch the weather right now.",
        "Weather data is not available at the moment.",
    ],
    "definition": [
        "{word}: {definition}",
        "Here's what I found: {word} means {definition}",
        "According to DuckDuckGo, {word} is {definition}",
    ],
    "ddg_answer": [
        "{answer}",
        "Here's what I found: {answer}",
    ],
    "ddg_no_result": [
        "I couldn't find anything on that.",
        "DuckDuckGo didn't return any results for that.",
    ],
    "translation": [
        "{translation}",
        "That translates to: {translation}",
    ],
    "news_headline": [
        "{headline}",
        "Here's a headline: {headline}",
    ],
    "place_result": [
        "I found {name} — {description}",
    ],
}


def pick(phrase_key: str, **kwargs) -> str:
    phrases = _PHRASES.get(phrase_key, ["I'm not sure about that"])
    phrase = random.choice(phrases)
    if kwargs:
        phrase = phrase.format(**kwargs)
    return phrase
