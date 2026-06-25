"""
Zeno System Skill — real device controls via Termux API.
Controls volume, brightness, screen lock, and app launching.
Gracefully falls back to text when APIs aren't available.
"""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.platform import (
    caps, set_volume, set_brightness, show_toast,
    vibrate, lock_screen, open_app,
)


class SystemSkill(BaseSkill):
    intents = [
        "system_lock", "volume_up", "volume_down",
        "volume_mute", "open_app",
    ]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        if intent == "system_lock":
            return self._lock_screen()

        if intent == "volume_up":
            return self._adjust_volume(+3)

        if intent == "volume_down":
            return self._adjust_volume(-3)

        if intent == "volume_mute":
            return self._mute_volume()

        if intent == "open_app":
            return self._open_app(entities.app_name)

        return self.pick("unknown")

    def _lock_screen(self) -> str:
        if lock_screen():
            return self.say("Locking the screen.")
        return self.say("Screen lock isn't available on this platform.")

    def _adjust_volume(self, delta: int) -> str:
        if not caps().volume:
            return self.say("Volume control isn't available here.")
        # Default to mid-range (50%) and adjust
        new_vol = max(0, min(100, 50 + delta * 10))
        set_volume("music", new_vol)
        direction = "up" if delta > 0 else "down"
        return self.say(f"Volume {direction}.")

    def _mute_volume(self) -> str:
        if not caps().volume:
            return self.say("Volume control isn't available here.")
        set_volume("music", 0)
        return self.say("Muted.")

    def _open_app(self, app_name: str | None) -> str:
        if not app_name:
            return self.say("What app should I open?")
        if open_app(app_name):
            return self.say(f"Opening {app_name}.")
        return self.say(f"Couldn't open {app_name} on this platform.")
