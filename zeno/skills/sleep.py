"""Zeno Sleep Timer Skill — sets a timer to pause music/sound."""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities, extract_entities
from zeno.core.context import Context
from zeno.skills.reminders import ReminderSkill


class SleepSkill(BaseSkill):
    intents = ["sleep_timer"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        if entities.duration:
            context.clear_awaiting()
            seconds = ReminderSkill()._parse_duration_seconds(entities.duration)
            if seconds > 0:
                ReminderSkill()._schedule_timer(seconds, "Sleep timer", is_alarm=False)
                return self.say(f"Sleep timer set for {entities.duration}.")
            return self.say("I couldn't work out the duration.")
        context.await_slot("sleep_timer", "duration")
        return self.say("How long until sleep mode? Try '30 minutes' or '1 hour'.")

    def fill_slot(self, slot: str, raw_text: str, context: Context) -> str:
        if slot == "duration":
            entities = extract_entities(raw_text, "sleep_timer")
            if entities.duration:
                context.clear_awaiting()
                seconds = ReminderSkill()._parse_duration_seconds(entities.duration)
                if seconds > 0:
                    ReminderSkill()._schedule_timer(seconds, "Sleep timer", is_alarm=False)
                    return self.say(f"Sleep timer set for {entities.duration}.")
            return self.say("How long, exactly? Try '30 minutes'.")
        context.clear_awaiting()
        return self.pick("unknown")
