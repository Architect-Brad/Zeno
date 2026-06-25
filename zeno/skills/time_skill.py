"""
Zeno Time Skill — current time and date queries.
"""

from datetime import datetime

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


class TimeSkill(BaseSkill):
    intents = ["time_query", "date_query"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        now = datetime.now()

        if intent == "time_query":
            hour = now.hour
            minute = now.minute
            meridiem = "AM" if hour < 12 else "PM"
            hour12 = hour % 12
            if hour12 == 0:
                hour12 = 12
            time_str = f"{hour12}:{minute:02d} {meridiem}"
            return self.say(f"It's {time_str}.")

        if intent == "date_query":
            day_name = _DAYS[now.weekday()]
            month = _MONTHS[now.month - 1]
            date_str = f"{day_name}, {month} {now.day}, {now.year}"
            return self.say(f"Today is {date_str}.")

        return self.pick("unknown")
