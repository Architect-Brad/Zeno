"""
Zeno Reminders Skill — real alarms, timers, reminders via Termux notifications.
Uses threading timers for scheduling and Termux notifications for alerts.
"""

import threading
import time
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.platform import show_notification, caps, vibrate


class ReminderSkill(BaseSkill):
    intents = ["set_alarm", "set_timer", "set_reminder"]
    _active_timers: list[threading.Timer] = []
    _timer_meta: list[dict] = []  # metadata for web UI

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        if intent == "set_alarm":
            return self._set_alarm(entities, context)
        if intent == "set_timer":
            return self._set_timer(entities, context)
        if intent == "set_reminder":
            return self._set_reminder(entities, context)
        return self.pick("unknown")

    def _set_alarm(self, entities: Entities, context: Context) -> str:
        if entities.time:
            context.clear_awaiting()
            alarm_info = self._schedule_alarm(entities.time)
            return self.say(f"Alarm set for {entities.time.upper()}.")
        context.await_slot("set_alarm", "time")
        return self.say("What time should I set the alarm for?")

    def _set_timer(self, entities: Entities, context: Context) -> str:
        if entities.duration:
            context.clear_awaiting()
            seconds = self._parse_duration_seconds(entities.duration)
            if seconds > 0:
                self._schedule_timer(seconds, entities.duration)
                return self.say(f"Timer set for {entities.duration}.")
            return self.say("I couldn't work out the duration.")
        context.await_slot("set_timer", "duration")
        return self.say("How long should the timer be?")

    def _set_reminder(self, entities: Entities, context: Context) -> str:
        if entities.raw_target:
            context.clear_awaiting()
            self._schedule_reminder(entities.raw_target)
            return self.say(f"I'll remind you about {entities.raw_target}.")
        context.await_slot("set_reminder", "subject")
        return self.say("What should I remind you about?")

    def fill_slot(self, slot: str, raw_text: str, context: Context) -> str:
        if slot == "time":
            from zeno.nlu.entity import extract_entities
            entities = extract_entities(raw_text, "set_alarm")
            if entities.time:
                context.clear_awaiting()
                return self.say(f"Alarm set for {entities.time.upper()}.")
            return self.say("I didn't catch a time — try something like '7am'.")

        if slot == "duration":
            from zeno.nlu.entity import extract_entities
            entities = extract_entities(raw_text, "set_timer")
            if entities.duration:
                context.clear_awaiting()
                seconds = self._parse_duration_seconds(entities.duration)
                if seconds > 0:
                    self._schedule_timer(seconds, entities.duration)
                    return self.say(f"Timer set for {entities.duration}.")
                return self.say("I couldn't work out the duration.")
            return self.say("How long, exactly? Try '5 minutes' or '1 hour'.")

        if slot == "subject":
            subject = raw_text.strip()
            for prefix in ("to ", "about ", "that "):
                if subject.lower().startswith(prefix):
                    subject = subject[len(prefix):].strip()
                    break
            context.clear_awaiting()
            self._schedule_reminder(subject)
            return self.say(f"I'll remind you to {subject}.")

        context.clear_awaiting()
        return self.pick("unknown")

    def _parse_duration_seconds(self, duration: str) -> int:
        import re
        m = re.match(r"(\d+\.?\d*)\s*(minutes?|mins?|seconds?|secs?|hours?|hrs?)", duration, re.IGNORECASE)
        if not m:
            return 0
        val = float(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith("min"):
            return int(val * 60)
        if unit.startswith("sec"):
            return int(val)
        if unit.startswith("hr") or unit.startswith("hour"):
            return int(val * 3600)
        return int(val)

    def _schedule_alarm(self, time_str: str):
        """Parse time and schedule alarm notification."""
        import re
        import datetime
        m = re.match(r"(\d{2}):(\d{2})\s*(AM|PM)", time_str.upper())
        if not m:
            show_notification("Zeno Alarm", f"Alarm set for {time_str}")
            return

        hour = int(m.group(1))
        minute = int(m.group(2))
        meridiem = m.group(3)

        if meridiem == "PM" and hour < 12:
            hour += 12
        elif meridiem == "AM" and hour == 12:
            hour = 0

        now = datetime.datetime.now()
        alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if alarm_time <= now:
            alarm_time += datetime.timedelta(days=1)

        seconds_until = (alarm_time - now).total_seconds()
        self._schedule_timer(
            int(seconds_until),
            f"Alarm for {time_str}",
            is_alarm=True,
        )

    def _schedule_timer(self, seconds: int, label: str, is_alarm: bool = False):
        started = time.time()

        def fire():
            if is_alarm:
                show_notification("Zeno Alarm", f"⏰ {label}", alert_once=False)
            else:
                show_notification("Zeno Timer", f"⏱ {label} is up!", alert_once=False)
            vibrate(1000)

        timer = threading.Timer(seconds, fire)
        timer.daemon = True
        timer.start()
        self._active_timers.append(timer)
        self._timer_meta.append({
            "label": label,
            "seconds": seconds,
            "started": started,
            "is_alarm": is_alarm,
        })

    def _schedule_reminder(self, subject: str):
        show_notification("Zeno Reminder", f"📌 Don't forget: {subject}")

    @staticmethod
    def list_timers() -> list[dict]:
        import datetime
        now = datetime.datetime.now()
        result = []
        for t in ReminderSkill._active_timers:
            remaining = max(0, t.interval - (time.time() - (t.finished_at if hasattr(t, 'finished_at') else 0)))
            if hasattr(t, 'func') and t.is_alive():
                result.append({
                    "remaining": remaining,
                    "interval": t.interval,
                    "alive": t.is_alive(),
                })
        return result
