"""
Zeno NLU — Entity Extraction
Extracts structured entities from natural language input.
Time, date, duration, numbers, names, locations, and more.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Entities:
    time: str | None = None
    date: str | None = None
    duration: str | None = None
    number: float | None = None
    app_name: str | None = None
    location: str | None = None
    name: str | None = None
    contact_name: str | None = None
    expression: str | None = None
    raw_target: str | None = None
    raw: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Time patterns
# ---------------------------------------------------------------------------

_TIME_PATTERNS = [
    # 7am, 7:30am, 7:30 am, 7:30a.m.
    r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?|am|pm)\b",
    # 14:00, 09:30 (24h)
    r"(\d{2}):(\d{2})\b(?!\s*(?:am|pm|a\.m\.|p\.m\.))",
    # noon, midnight, midday
    r"\b(noon|midnight|midday)\b",
    # o'clock: 7 o'clock, seven o'clock
    r"(\d{1,2})\s*o'?\s*clock\b",
]

_DURATION_PATTERNS = [
    r"(\d+\.?\d*)\s*(minutes?|mins?|seconds?|secs?|hours?|hrs?)",
]

_DATE_PATTERNS = [
    r"\b(today|tomorrow|yesterday)\b",
    r"\b(tonight|this morning|this afternoon|this evening)\b",
    r"\b(next|this|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month|year)\b",
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
]

_NUMBER_PATTERNS = [
    r"\b(\d+\.?\d*)\b",
]

_APP_PATTERNS = [
    r"(?:open|launch|start|run)\s+(.+?)(?:\s+(?:please|now|thanks|thank you))?$",
]

_LOCATION_PATTERNS = [
    r"(?:in|at|for|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
]

_EXPRESSION_PATTERNS = [
    r"(\d+\s*[\+\-\*\/xX]\s*\d+(?:\s*[\+\-\*\/xX]\s*\d+)*)",
    r"(?:what'?s|what is|how much is)\s+(.+?)(?:\?)?$",
    r"(?:calculate|compute)\s+(.+?)(?:\?)?$",
]


def _match_first(text: str, patterns: list[str]) -> str | None:
    """Return the first regex match group 1 (or group 0) found."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            # Return the most specific group
            try:
                return m.group(1) or m.group(0)
            except IndexError:
                return m.group(0)
    return None


def _extract_time(text: str) -> str | None:
    """Extract and normalize time expressions."""
    for pattern in _TIME_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if "noon" in (groups[0] or "").lower():
                return "12:00 PM"
            if "midnight" in (groups[0] or "").lower():
                return "12:00 AM"
            if "midday" in (groups[0] or "").lower():
                return "12:00 PM"

            hour = groups[0]
            minute = groups[1] if len(groups) > 1 and groups[1] else "00"
            meridiem = groups[2].upper().replace(".", "") if len(groups) > 2 and groups[2] else ""

            if meridiem:
                norm_hour = int(hour)
                if meridiem.startswith("P") and norm_hour < 12:
                    norm_hour += 12
                elif meridiem.startswith("A") and norm_hour == 12:
                    norm_hour = 0
                return f"{norm_hour:02d}:{minute} {meridiem[:1]}M"

            # 24h format
            return f"{int(hour):02d}:{minute}"

        # o'clock pattern
        m = re.search(r"(\d{1,2})\s*o'?\s*clock\b", text, re.IGNORECASE)
        if m:
            return f"{int(m.group(1)):02d}:00"

    return None


def _extract_duration(text: str) -> str | None:
    m = re.search(_DURATION_PATTERNS[0], text, re.IGNORECASE)
    if m:
        val = m.group(1)
        unit = m.group(2).lower()
        # Normalize unit
        if unit.startswith("min"):
            unit = "minutes"
        elif unit.startswith("sec"):
            unit = "seconds"
        elif unit.startswith("hr") or unit.startswith("hour"):
            unit = "hours"
        return f"{val} {unit}"
    return None


def _extract_date(text: str) -> str | None:
    now = datetime.now()
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    # Relative dates
    m = re.search(r"\b(today|tomorrow|yesterday)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).lower()

    m = re.search(r"\b(tonight)\b", text, re.IGNORECASE)
    if m:
        return "today"

    # "next monday", "this friday"
    m = re.search(r"\b(next|this|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.IGNORECASE)
    if m:
        modifier = m.group(1).lower()
        target_day = m.group(2).lower()
        target_idx = day_names.index(target_day)
        current_idx = now.weekday()
        diff = target_idx - current_idx
        if modifier == "next":
            diff += 7 if diff <= 0 else 7
        elif modifier == "last":
            diff -= 7 if diff >= 0 else 7
        elif modifier == "this":
            diff = diff if diff >= 0 else diff + 7
        return target_day

    # Just a day name
    m = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).lower()

    return None


def _extract_app_name(text: str, intent_hint: str | None = None) -> str | None:
    """Extract app name after open/launch/start/run."""
    if intent_hint != "open_app":
        return None
    for pattern in _APP_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_location(text: str, intent_hint: str | None = None) -> str | None:
    """Extract location from text for any intent."""
    # Named places: "in London", "at home", "near Paris"
    for pattern in _LOCATION_PATTERNS:
        m = re.search(pattern, text)
        if m:
            candidate = m.group(1).strip()
            if candidate.lower() not in ("the", "my", "your", "this", "that", "it"):
                return candidate
    return None


def _extract_expression(text: str) -> str | None:
    for pattern in _EXPRESSION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            expr = m.group(1) if m.lastindex else m.group(0)
            # Clean up
            expr = expr.strip().rstrip("?").strip()
            if expr.lower().startswith("what's "):
                expr = expr[7:]
            elif expr.lower().startswith("what is "):
                expr = expr[8:]
            elif expr.lower().startswith("how much is "):
                expr = expr[12:]
            elif expr.lower().startswith("calculate "):
                expr = expr[10:]
            elif expr.lower().startswith("compute "):
                expr = expr[8:]
            return expr
    return None


def _extract_reminder_target(text: str) -> str | None:
    """Extract the thing to be reminded about."""
    patterns = [
        r"(?:remind me to|remind me about|remind me that)\s+(.+?)(?:\s*please|\s*thanks|\s*$)",
        r"(?:remind|reminder)\s+(.+?)(?:\s*please|\s*$)",
        r"(?:don't forget to|don't let me forget to)\s+(.+?)(?:\s*please|\s*$)",
        r"set\s+a\s+reminder\s+(?:to|about|for|that)\s+(.+?)(?:\s*please|\s*$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_entities(text: str, intent_hint: str | None = None) -> Entities:
    """Extract all entities from text, optionally scoped to an intent."""
    lower = text.lower()

    entities = Entities(
        time=_extract_time(text),
        date=_extract_date(text),
        duration=_extract_duration(text),
        app_name=_extract_app_name(text, intent_hint),
        location=_extract_location(text, intent_hint),
        expression=_extract_expression(text),
        raw_target=_extract_reminder_target(text),
    )

    # Extract numbers
    m = re.search(r"\b(\d+\.?\d*)\b", text)
    if m and entities.expression is None:
        try:
            val = float(m.group(1))
            if "." in m.group(1) or val > 1000000:
                entities.number = val
            elif entities.time is None:
                entities.number = val
        except ValueError:
            pass

    # Extract name from introduction
    if intent_hint in (None, "introduce"):
        patterns = [
            r"(?:i'?m |i am |call me |my name is |it'?s |its )(.+?)(?:\s*please|\s*$)",
            r"^(.+?)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m and m.group(1).strip():
                candidate = m.group(1).strip().title()
                if candidate.lower() not in ("hey", "hi", "hello", "yes", "no", "ok", "okay", "sure", "bye"):
                    entities.name = candidate
                    break

    # Extract contact name from address book
    if intent_hint in (None, "send_message", "make_call"):
        from zeno.core.contact_store import get_contact_names
        known = get_contact_names()
        lower = text.lower()
        for contact in sorted(known, key=len, reverse=True):
            if contact.lower() in lower:
                entities.contact_name = contact
                break

    entities.raw = {"text": text, "intent_hint": intent_hint or ""}
    return entities
