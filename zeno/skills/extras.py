"""Zeno Extras Skill — media, communications, navigation, utilities."""

import random
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.core.contact_store import find_contact, get_contact_names
from zeno.platform import (
    caps, set_volume, set_brightness, show_toast,
    vibrate, lock_screen, open_app, show_notification,
    send_sms, make_call,
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
    "traffic_check": [
        "I can't check traffic conditions right now.",
        "Traffic data isn't available on this device.",
    ],
}

_UTILITY_RESPONSES = {
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
            return self._send_message(entities, context)
        if intent == "make_call":
            return self._make_call(entities, context)

        phrases = _ALL_RESPONSES.get(intent)
        if phrases:
            return self.say(random.choice(phrases))
        return self.pick("unknown")

    def fill_slot(self, slot: str, raw_text: str, context: Context) -> str:
        if slot == "confirm_call":
            return self._confirm_call(raw_text, context)
        if slot == "confirm_message":
            return self._confirm_message(raw_text, context)
        context.clear_awaiting()
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

    def _send_message(self, entities: Entities, context: Context) -> str:
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
        if not phone:
            return self.say(f"I have {contact_name} saved but no phone number.")
        if not caps().sms:
            return self.say(
                f"I can't actually send texts on this platform — "
                f"SMS sending isn't available here."
            )
        # Sending a real text has a real-world effect (cost, reaches an
        # actual person), so confirm before doing it rather than acting
        # on a possibly-misheard voice command.
        context.set_pending("message_target", {"name": contact_name, "phone": phone})
        context.await_slot("send_message", "confirm_message")
        return self.say(f"Send a text to {contact_name}? Say yes to confirm.")

    def _confirm_message(self, raw_text: str, context: Context) -> str:
        target = context.get_pending("message_target")
        context.clear_awaiting()
        context.clear_pending()
        if not target:
            return self.say("I lost track of who to message — try again.")
        if not self._is_affirmative(raw_text):
            return self.say("Okay, not sending anything.")
        ok = send_sms(target["phone"], f"Message from {target['name']} via Zeno")
        if ok:
            return self.say(f"Text sent to {target['name']}.")
        return self.say(f"That didn't go through — couldn't send a text to {target['name']}.")

    def _make_call(self, entities: Entities, context: Context) -> str:
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
        if not phone:
            return self.say(f"I have {contact_name} saved but no phone number.")
        if not caps().call:
            return self.say(
                f"I can't actually place calls on this platform — "
                f"calling isn't available here."
            )
        # Placing a real call is immediate and hard to undo, so confirm
        # first rather than dialing on a possibly-misheard command.
        context.set_pending("call_target", {"name": contact_name, "phone": phone})
        context.await_slot("make_call", "confirm_call")
        return self.say(f"Call {contact_name}? Say yes to confirm.")

    def _confirm_call(self, raw_text: str, context: Context) -> str:
        target = context.get_pending("call_target")
        context.clear_awaiting()
        context.clear_pending()
        if not target:
            return self.say("I lost track of who to call — try again.")
        if not self._is_affirmative(raw_text):
            return self.say("Okay, not calling.")
        ok = make_call(target["phone"])
        if ok:
            return self.say(f"Calling {target['name']}.")
        return self.say(f"That didn't go through — couldn't call {target['name']}.")

    @staticmethod
    def _is_affirmative(raw_text: str) -> bool:
        from zeno.nlu.intent import classify_intent
        result = classify_intent(raw_text)
        if result.intent == "affirm":
            return True
        if result.intent == "deny":
            return False
        # Fall back to a plain keyword check for short, ungrammatical replies
        return raw_text.strip().lower() in {"yes", "yeah", "yep", "sure", "confirm", "do it"}
