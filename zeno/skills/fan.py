"""Zeno Fan Speed Skill — controls fan speed via Home Assistant."""

from zeno.skills.home_assistant import _load_config, _ha_call
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class FanSkill(BaseSkill):
    intents = ["fan_speed"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        config = _load_config()
        if not config:
            return self.say(
                "Fan control requires Home Assistant. "
                "Create ~/.zeno/home_assistant.json with your server details."
            )
        url = config.get("url", "http://homeassistant.local:8123")
        token = config.get("token", "")
        if not token:
            return self.say("Home Assistant token is missing.")

        fan_entities = config.get("entities", {}).get("fan_speed", config.get("entities", {}).get("fan"))
        if not fan_entities:
            return self.say("No fan configured in home_assistant.json entities.")

        if isinstance(fan_entities, str):
            fan_entities = [fan_entities]

        speed = entities.number
        if speed is not None:
            speed = max(1, min(100, int(speed)))
            percentage = speed
        else:
            percentage = 50

        ok = _ha_call(url, token, "fan", "set_percentage", {
            "entity_id": fan_entities,
            "percentage": percentage,
        })
        if ok:
            return self.say(f"Fan set to {percentage}%.")
        return self.say("Couldn't adjust the fan.")
