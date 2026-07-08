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
    # Relative: "in X minutes/hours" → stored as raw, resolved by caller
    r"\b(in|after)\s+(an?\s+hour|an?\s+minute|\d+\s*(?:minutes?|mins?|hours?|hrs?))\b",
    # Relative: "X minutes from now"
    r"(\d+\s*(?:minutes?|mins?|hours?|hrs?))\s+(?:from now|later|from now on)\b",
]

_DURATION_PATTERNS = [
    r"(\d+\.?\d*)\s*(minutes?|mins?|seconds?|secs?|hours?|hrs?)",
    r"(?<!\d)(?:an?\s+|a\s+)(hour(?!s)|minute(?!s)|second(?!s))(?:\s+and\s+(?:a\s+)?(half|quarter))?",
    r"(half\s+(?:an?\s+)?|quarter\s+of\s+an?\s+)(hour|minute)",
    r"(?:a\s+)?(?:couple\s+of\s+)?(hours?|minutes?|seconds?)(?:\s+or\s+(?:so|two|three))?",
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
    r"(?:open|launch|start|run)\s+['\"](.+?)['\"]",
    r"(?:open|launch|start|run)\s+(.+?)(?:\s+(?:please|now|thanks|thank you|app|application))?\s*$",
]

_LOCATION_PATTERNS = [
    r"(?:in|at|for|near|around)\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)",
    r"(?:in|at|for|near|around)\s+(the\s+)?([a-z]+(?:\s+[a-z]+)*)",
]

_EXPRESSION_PATTERNS = [
    r"(\d+\s*[\+\-\*\/xX]\s*\d+(?:\s*[\+\-\*\/xX]\s*\d+(?:\s*[\+\-\*\/xX]\s*\d+)*)*)",
    r"(\d+\s*percent\s+of\s+\d+)",
    r"(\d+\s*%\s+of\s+\d+)",
    r"(?:what'?s|what is|how much is)\s+(.+?)(?:\?)?$",
    r"(?:calculate|compute|what does|whats)\s+(.+?)(?:\?)?$",
    r"(?:add|subtract|multiply|divide)\s+(.+?)(?:\s+and\s+|\s+by\s+)(.+?)$",
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
        if not m:
            continue
        groups = m.groups()

        # Relative time: "in 5 minutes", "5 minutes from now"
        if groups[0] and groups[0].lower() in ("in", "after"):
            target = groups[1] or ""
            m2 = re.match(r"(\d+)\s*(minutes?|mins?|hours?|hrs?)", target, re.IGNORECASE)
            if m2:
                return f"in {m2.group(1)} {m2.group(2).lower()}"
            if re.match(r"an?\s+hour", target, re.IGNORECASE):
                return "in 1 hour"
            if re.match(r"an?\s+minute", target, re.IGNORECASE):
                return "in 1 minute"
            return f"in {target}"

        groups = list(groups)
        while len(groups) < 4:
            groups.append(None)

        if groups[0] and groups[0].lower() in ("noon", "midnight", "midday"):
            if groups[0].lower() == "noon":
                return "12:00 PM"
            if groups[0].lower() == "midnight":
                return "12:00 AM"
            if groups[0].lower() == "midday":
                return "12:00 PM"

        # o'clock pattern
        if groups[0] and groups[3]:
            return f"{int(groups[0]):02d}:00"

        hour = groups[0] if groups[0] else ""
        minute = groups[1] if len(groups) > 1 and groups[1] else "00"
        meridiem = groups[2].upper().replace(".", "") if len(groups) > 2 and groups[2] else ""

        # Relative: "5 minutes from now"
        if meridiem.lower() in ("from now", "later", "from now on"):
            val = hour
            unit = minute or "minutes"
            if unit.startswith("min") or unit.startswith("sec"):
                return f"in {val} {unit}"
            elif unit.startswith("hou"):
                return f"in {val} {unit}"

        if meridiem and len(meridiem) <= 3:
            # Keep the human-readable 12-hour form here (e.g. "5:00 PM").
            # Converting to 24-hour and still appending "PM" produced
            # nonsensical strings like "17:00 PM" — the one place that
            # actually needs 24-hour form for scheduling is
            # ReminderSkill._schedule_alarm, which already does its own
            # (correct) 12h->24h conversion from this same format.
            display_hour = int(hour)
            return f"{display_hour:02d}:{minute} {meridiem[:1]}M"

        # 24h format
        if hour and minute:
            try:
                return f"{int(hour):02d}:{minute}"
            except ValueError:
                pass

    return None


def _extract_duration(text: str) -> str | None:
    lower = text.lower()
    # Pattern 2: "half an hour", "quarter of an hour", "half hour"
    m = re.search(_DURATION_PATTERNS[2], lower, re.IGNORECASE)
    if m:
        frac = (m.group(1) or "").lower()
        unit = (m.group(m.lastindex) or "hour").lower()
        if "half" in frac:
            val = 0.5
        elif "quarter" in frac:
            val = 0.25
        else:
            val = 1.0
        return f"{val} {unit}s"
    # Pattern 1: "an hour and a half", "an hour and a quarter", "a minute"
    # Groups: (1)=unit, (2)=half|quarter
    m = re.search(_DURATION_PATTERNS[1], lower, re.IGNORECASE)
    if m:
        whole = m.group(0)
        if "and" in whole and m.lastindex >= 2:
            unit = m.group(1)
            frac = m.group(2)
            if unit and frac:
                val = "1.5" if frac == "half" else "1.25"
                return f"{val} {unit}s"
        # "an hour" / "a minute"
        if not re.search(r'\b(?:half|quarter)\b', lower):
            unit = (m.group(1) or "hour").lower()
            if unit.startswith("hour"):
                return "1 hours"
            elif unit.startswith("min"):
                return "1 minutes"
            elif unit.startswith("sec"):
                return "1 seconds"
    # Pattern 0: "5 minutes", "3 hours"
    m = re.search(_DURATION_PATTERNS[0], lower, re.IGNORECASE)
    if m:
        val = m.group(1)
        unit = m.group(2).lower()
        if unit.startswith("min"):
            unit = "minutes"
        elif unit.startswith("sec"):
            unit = "seconds"
        elif unit.startswith("hr") or unit.startswith("hour"):
            unit = "hours"
        return f"{val} {unit}"
    # Pattern 3: "a couple hours", "a few minutes", "couple of hours"
    m = re.search(_DURATION_PATTERNS[3], lower, re.IGNORECASE)
    if m:
        unit = (m.group(m.lastindex) or "minutes").lower()
        if unit.startswith("hour"):
            return "2 hours"
        elif unit.startswith("min"):
            return "2 minutes"
        elif unit.startswith("sec"):
            return "2 seconds"
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
    FILLER = {
        "the", "my", "your", "this", "that", "it", "a", "an",
        "an hour", "a minute", "a second", "half an hour",
        "a while", "a bit", "a moment", "a few",
        "today", "tomorrow", "yesterday", "tonight",
    }
    _TIME_UNITS = {"hour", "hours", "minute", "minutes", "second", "seconds", "day", "days"}
    for pattern in _LOCATION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = m.lastindex and m.group(m.lastindex) or m.group(1)
            candidate = candidate.strip()
            words = set(candidate.lower().split())
            if (candidate.lower() not in FILLER
                    and len(candidate) > 1
                    and not words & _TIME_UNITS):
                return candidate
    return None


def _extract_expression(text: str) -> str | None:
    for pattern in _EXPRESSION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            if pattern.startswith(r"(?:add|subtract|multiply|divide)"):
                op = m.group(1).lower()
                arg1 = m.group(2).strip()
                arg2 = m.group(3).strip() if m.lastindex >= 3 else ""
                return f"{op} {arg1} {arg2}"
            expr = m.group(1) if m.lastindex else m.group(0)
            expr = expr.strip().rstrip("?").strip()
            prefixes = ["what's ", "what is ", "how much is ", "calculate ",
                        "compute ", "what does ", "whats "]
            for p in prefixes:
                if expr.lower().startswith(p):
                    expr = expr[len(p):]
                    break
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
