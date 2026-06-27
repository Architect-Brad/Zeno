"""Zeno Extras Skill — media, communications, navigation, utilities."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.core.contact_store import find_contact, get_contact_names
from zeno.platform import (
    caps, set_volume, set_brightness, show_toast,
    vibrate, lock_screen, open_app, show_notification,
)


_MEDIA_RESPONSES = {
    "play_music": [
        "Playing music is not yet available on this device.",
        "I'd love to play some tunes, but media playback isn't implemented yet.",
    ],
    "next_track": ["Skipping to the next track — if I had a playlist.", "Can't skip tracks without a music player yet."],
    "previous_track": ["Going back to the previous track — in theory.", "No previous track to go back to right now."],
    "pause_music": ["Pausing the music — hypothetically.", "Can't pause what isn't playing."],
    "resume_music": ["Resuming playback — if there was any.", "Nothing to resume right now."],
}

_COMMS_RESPONSES = {
    "check_email": [
        "I can't check email yet — no email integration.",
        "Email checking isn't implemented.",
    ],
    "read_notifications": [
        "Reading notifications isn't available on this device.",
        "I can't access your notifications from here.",
    ],
}

_NAV_RESPONSES = {
    "get_directions": [
        "I can't give directions yet — navigation isn't implemented.",
        "Directions aren't available on this platform.",
    ],
    "find_place": [
        "I can't search for nearby places yet.",
        "Place search isn't available on this device.",
    ],
    "traffic_check": [
        "I can't check traffic conditions right now.",
        "Traffic data isn't available on this device.",
    ],
}

_UTILITY_RESPONSES = {
    "define_word": [
        "I don't have a dictionary built in yet.",
        "Word definitions aren't available — I'd need a dictionary module.",
    ],
    "translate_phrase": [
        "Translation isn't implemented yet.",
        "I can't translate phrases right now.",
    ],
    "check_battery": [
        "Checking the battery isn't available on this platform.",
        "I can't access the battery level from here.",
    ],
    "flashlight_on": [
        "Turning on the flashlight isn't available on this device.",
        "I can't control the flashlight from here.",
    ],
    "flashlight_off": [
        "Turning off the flashlight isn't available on this device.",
        "I can't control the flashlight from here.",
    ],
    "screenshot": [
        "Taking a screenshot isn't available on this platform.",
        "I can't capture the screen from here.",
    ],
    "wifi_on": [
        "I can't control WiFi from this device.",
        "WiFi control isn't available on this platform.",
    ],
    "wifi_off": [
        "I can't control WiFi from this device.",
        "WiFi control isn't available on this platform.",
    ],
}

_ALL_RESPONSES: dict[str, list[str]] = {}
for d in (_MEDIA_RESPONSES, _COMMS_RESPONSES,
          _NAV_RESPONSES, _UTILITY_RESPONSES):
    _ALL_RESPONSES.update(d)


class ExtrasSkill(BaseSkill):
    intents = list(_ALL_RESPONSES.keys()) + [
        "check_timer_status", "stop_timer",
        "set_volume_exact", "brightness_up", "brightness_down",
        "send_message", "make_call",
    ]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        if intent == "check_timer_status":
            return self._timer_status()
        if intent == "stop_timer":
            return self._stop_timer()
        if intent == "set_volume_exact":
            return self._set_volume_exact(entities)
        if intent == "brightness_up":
            return self._brightness(10)
        if intent == "brightness_down":
            return self._brightness(-10)
        if intent == "send_message":
            return self._send_message(entities)
        if intent == "make_call":
            return self._make_call(entities)

        phrases = _ALL_RESPONSES.get(intent)
        if phrases:
            return self.say(random.choice(phrases))
        return self.pick("unknown")

    def _timer_status(self) -> str:
        from zeno.skills.reminders import ReminderSkill
        meta = ReminderSkill._timer_meta
        if not meta:
            return self.say("No active timers.")
        now = __import__("time").time()
        parts = []
        for t in meta:
            remaining = int(t["seconds"] - (now - t["started"]))
            if remaining <= 0:
                continue
            tag = "⏰" if t["is_alarm"] else "⏱"
            parts.append(f"{tag} {t['label']}: {remaining // 60}m {remaining % 60}s")
        if not parts:
            return self.say("No active timers.")
        return self.say("Active timers: " + "; ".join(parts))

    def _stop_timer(self) -> str:
        from zeno.skills.reminders import ReminderSkill
        if not ReminderSkill._active_timers:
            return self.say("No timers to stop.")
        timer = ReminderSkill._active_timers[-1]
        timer.cancel()
        ReminderSkill._active_timers.pop()
        if ReminderSkill._timer_meta:
            ReminderSkill._timer_meta.pop()
        show_notification("Zeno Timer", "Timer cancelled.")
        return self.say("Timer stopped.")

    def _set_volume_exact(self, entities: Entities) -> str:
        if not caps().volume:
            return self.say("Volume control isn't available here.")
        level = None
        if entities.expression:
            try:
                level = int(entities.expression)
            except (ValueError, TypeError):
                pass
        if level is None and entities.number is not None:
            level = int(entities.number)
        if level is None:
            level = 50
        level = max(0, min(100, level))
        set_volume("music", level)
        return self.say(f"Volume set to {level}.")

    def _brightness(self, delta: int) -> str:
        if not caps().brightness:
            return self.say("Brightness control isn't available here.")
        if delta > 0:
            set_brightness(min(100, 50 + delta))
            return self.say("Brightness up.")
        else:
            set_brightness(max(0, 50 + delta))
            return self.say("Brightness down.")

    def _send_message(self, entities: Entities) -> str:
        contact_name = entities.contact_name
        if not contact_name:
            known = ", ".join(get_contact_names())
            if known:
                return self.say(f"I don't know who to message. Your contacts: {known}.")
            return self.say("No contacts saved. Add contacts to ~/.zeno/contacts.json.")
        info = find_contact(contact_name)
        if not info:
            return self.say(f"I don't have contact info for {contact_name}.")
        phone = info.get("phone") or info.get("number", "")
        if phone:
            from zeno.platform import show_notification
            show_notification("Zeno Message", f"Message sent to {contact_name}.")
            return self.say(f"Messaging {contact_name}.")
        return self.say(f"I have {contact_name} saved but no phone number.")

    def _make_call(self, entities: Entities) -> str:
        contact_name = entities.contact_name
        if not contact_name:
            known = ", ".join(get_contact_names())
            if known:
                return self.say(f"I don't know who to call. Your contacts: {known}.")
            return self.say("No contacts saved. Add contacts to ~/.zeno/contacts.json.")
        info = find_contact(contact_name)
        if not info:
            return self.say(f"I don't have contact info for {contact_name}.")
        phone = info.get("phone") or info.get("number", "")
        if phone:
            from zeno.platform import show_notification
            show_notification("Zeno Call", f"Calling {contact_name}...")
            return self.say(f"Calling {contact_name}.")
        return self.say(f"I have {contact_name} saved but no phone number.")
