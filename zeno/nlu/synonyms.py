"""Zeno Synonym Expansion — bridges phrasing gaps without ML dependencies."""

_SYNONYM_GROUPS: list[set[str]] = [
    # Media / entertainment
    {"play", "start", "begin", "resume", "continue"},
    {"pause", "freeze", "hold", "suspend"},
    {"stop", "halt", "cease", "end", "quit", "abort"},
    {"song", "track", "music", "tune", "playlist", "melody"},
    {"next", "skip", "forward", "advance", "following"},
    {"previous", "back", "prior", "last", "rewind"},
    {"joke", "funny", "laugh", "humor", "comedy"},
    {"story", "tale", "narrative"},

    # Smart home
    {"light", "lamp", "illumination", "luminosity"},
    {"on", "active", "enable", "activate", "energize"},
    {"off", "inactive", "disable", "deactivate", "shut"},
    {"brightness", "luminosity", "illumination", "dimness"},
    {"thermostat", "temperature", "climate", "heating", "cooling"},
    {"door", "entrance", "gate", "lock"},
    {"lock", "secure", "bolt", "latch", "fasten"},
    {"security", "safety", "alarm", "surveillance", "monitoring"},

    # Communication
    {"message", "text", "sms", "chat", "dm", "notify", "alert"},
    {"call", "phone", "dial", "ring", "contact"},
    {"email", "mail", "inbox", "gmail", "outlook"},

    # Navigation
    {"directions", "route", "path", "navigation", "way"},
    {"find", "search", "locate", "discover", "hunt", "pin", "drop"},
    {"nearby", "around", "close", "near", "proximate", "surrounding"},
    {"traffic", "congestion", "jam", "delay", "road"},

    # Utilities
    {"define", "definition", "meaning", "dictionary", "glossary"},
    {"translate", "translation", "interpret", "convert"},
    {"battery", "power", "charge", "energy", "juice"},
    {"flashlight", "torch", "light"},
    {"screenshot", "capture", "snapshot", "screen"},

    # Time / scheduling
    {"alarm", "alarm clock", "wake up", "reminder"},
    {"timer", "countdown", "stopwatch"},
    {"remind", "remember", "reminder", "recall", "notification"},

    # System
    {"volume", "sound", "audio", "loudness"},
    {"wifi", "wireless", "internet", "network", "connectivity"},
    {"bluetooth", "bt"},
    {"mute", "silent", "quiet", "silence"},

    # General
    {"help", "assist", "support", "aid"},
    {"weather", "climate", "forecast", "temperature", "rain"},
    {"time", "clock", "hour", "minute"},
    {"date", "day", "calendar", "schedule"},
    {"goodbye", "bye", "farewell", "see you", "later", "adieu"},
    {"hello", "hi", "hey", "greetings", "howdy"},
    {"thanks", "thank you", "appreciate", "gratitude"},

    # Generic verbs
    {"set", "adjust", "change", "configure", "modify", "update"},
    {"show", "display", "show me", "tell me", "give me"},
    {"check", "see", "view", "examine", "verify", "monitor"},
    {"open", "launch", "start", "run", "load"},
    {"close", "exit", "quit", "shut down"},

    # Affirm / deny
    {"yes", "yeah", "yep", "sure", "ok", "okay", "alright", "correct"},
    {"no", "nope", "nah", "never", "negative"},

    # Names / people
    {"mom", "mother", "mama", "ma"},
    {"dad", "father", "papa", "pa"},
    {"brother", "bro", "sibling"},
    {"sister", "sis"},
    {"wife", "spouse", "partner", "husband"},
    {"friend", "buddy", "pal", "mate"},

    # Location
    {"in", "at", "near", "around", "by"},
    {"where", "location", "place", "spot", "position"},
]


def build_synonym_map() -> dict[str, set[str]]:
    """Build a word → set of synonyms lookup."""
    mapping: dict[str, set[str]] = {}
    for group in _SYNONYM_GROUPS:
        for word in group:
            if word not in mapping:
                mapping[word] = set()
            mapping[word].update(group - {word})
    return mapping


_SYNONYM_MAP: dict[str, set[str]] | None = None


def expand_text(text: str) -> list[str]:
    """Expand a phrase into multiple variants using synonyms.
    Returns the original + variants with one word replaced at a time."""
    global _SYNONYM_MAP
    if _SYNONYM_MAP is None:
        _SYNONYM_MAP = build_synonym_map()

    words = text.lower().split()
    variants = {text.lower()}
    for i, word in enumerate(words):
        if word in _SYNONYM_MAP:
            for syn in _SYNONYM_MAP[word]:
                variant = " ".join(words[:i] + [syn] + words[i+1:])
                variants.add(variant)
    return list(variants)


def expand_training_data(data: dict[str, list[str]]) -> dict[str, list[str]]:
    """Expand all training phrases with synonyms."""
    expanded = {}
    for intent, phrases in data.items():
        seen = set()
        result = []
        for phrase in phrases:
            for variant in expand_text(phrase):
                if variant not in seen:
                    seen.add(variant)
                    result.append(variant)
        expanded[intent] = result
    return expanded
