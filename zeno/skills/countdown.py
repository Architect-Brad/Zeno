"""Zeno Countdown Skill — calculates days until a given date."""

import re
from datetime import datetime, date
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _parse_date(text: str) -> date | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
    if m:
        day, month_str, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = _MONTH_NAMES.get(month_str)
        if month:
            return date(year, month, day)

    m = re.search(r"(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?", text, re.IGNORECASE)
    if m:
        month_str, day = m.group(1).lower(), int(m.group(2))
        year_str = m.group(3)
        month = _MONTH_NAMES.get(month_str)
        if month:
            year = int(year_str) if year_str else datetime.now().year
            return date(year, month, day)

    today = datetime.now().date()
    for name, idx in _DAY_NAMES.items():
        if name in text.lower():
            target = today
            days_ahead = idx - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return target.__class__(today.year, today.month, today.day + days_ahead)

    return None


class CountdownSkill(BaseSkill):
    intents = ["countdown_event"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        text = entities.raw.get("text", "")
        target = _parse_date(text)
        if not target:
            return self.say(
                "Tell me a date to count down to. "
                "Try 'countdown to December 25' or 'how many days until March 15 2026'."
            )
        today = datetime.now().date()
        delta = (target - today).days
        if delta < 0:
            return self.say(f"{target} was {abs(delta)} days ago.")
        if delta == 0:
            return self.say(f"{target} is today!")
        return self.say(f"{delta} days until {target}.")
