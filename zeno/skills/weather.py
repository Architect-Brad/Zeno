"""
Zeno Weather Skill
Uses wttr.in — a free, keyless weather service. Falls back gracefully if offline
or if no location is configured.
"""

import httpx
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.memory.store import get_store


class WeatherSkill(BaseSkill):
    intents = ["weather_query"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        store = get_store()
        location = store.get("profile.location", "")

        try:
            url = f"https://wttr.in/{location}?format=%C+%t+(feels+like+%f)"
            resp = httpx.get(url, timeout=4.0)
            resp.raise_for_status()
            report = resp.text.strip()
            if report and "Unknown location" not in report:
                return self.say(f"It's {report.lower()}.")
            return self.say(
                "I don't know your location yet. Tell me your city and I'll remember it."
            )
        except (httpx.HTTPError, httpx.TimeoutException):
            return self.say(
                "Can't reach the weather service right now — check your connection."
            )

    def set_location(self, city: str):
        get_store().set("profile.location", city)
