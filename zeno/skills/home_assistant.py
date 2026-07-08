"""Zeno Home Assistant Skill — control smart home devices via HA REST API."""

import json
import os
import random
import urllib.request
import urllib.error
from pathlib import Path
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_CONFIG_PATH = Path.home() / ".zeno" / "home_assistant.json"

_INTENTS = [
    "lights_on", "lights_off", "set_thermostat",
    "lock_door", "security_check",
]

_SERVICE_MAP = {
    "lights_on": ("light", "turn_on"),
    "lights_off": ("light", "turn_off"),
    "set_thermostat": ("climate", "set_temperature"),
    "lock_door": ("lock", "lock"),
    "security_check": ("alarm_control_panel", "alarm_arm_away"),
}

_ENTITY_HINTS = {
    "lights_on": "light",
    "lights_off": "light",
    "set_thermostat": "climate",
    "lock_door": "lock",
    "security_check": "alarm_control_panel",
}

_HINT_PROMPTS = {
    "lights_on": "I don't know which light to turn on. Configure entities in home_assistant.json.",
    "lights_off": "I don't know which light to turn off. Configure entities in home_assistant.json.",
    "set_thermostat": "I don't know which thermostat to adjust. Configure entities in home_assistant.json.",
    "lock_door": "I don't know which lock to use. Configure entities in home_assistant.json.",
    "security_check": "I don't know which alarm panel to check. Configure entities in home_assistant.json.",
}

_SUCCESS_PROMPTS = {
    "lights_on": ["Lights on.", "Turning on the lights.", "Lights activated."],
    "lights_off": ["Lights off.", "Turning off the lights.", "Lights deactivated."],
    "set_thermostat": ["Thermostat adjusted.", "Temperature set.", "Done."],
    "lock_door": ["Door locked.", "Locking the door.", "Door secured."],
    "security_check": ["Security system armed.", "System is now armed.", "Security activated."],
}

_ERROR_PROMPTS = {
    "lights_on": ["Couldn't turn on the lights.", "Failed to activate lights."],
    "lights_off": ["Couldn't turn off the lights.", "Failed to deactivate lights."],
    "set_thermostat": ["Couldn't adjust the thermostat.", "Failed to set temperature."],
    "lock_door": ["Couldn't lock the door.", "Failed to lock."],
    "security_check": ["Couldn't arm security.", "Failed to check security."],
}


def _load_config() -> dict | None:
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH) as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _ha_call(url: str, token: str, domain: str, service: str, data: dict) -> bool:
    try:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/api/services/{domain}/{service}",
            data=json.dumps(data).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


def _ha_get(url: str, token: str, path: str) -> dict | None:
    try:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/api/{path.lstrip('/')}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None


class HomeAssistantSkill(BaseSkill):
    """Controls smart home devices via a Home Assistant instance."""

    intents = list(_INTENTS)

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        config = _load_config()
        if not config:
            return self.say(
                "Home Assistant is not configured. "
                f"Create {_CONFIG_PATH} with {{\"url\": \"http://homeassistant:8123\", \"token\": \"...\"}} "
                "and optionally an \"entities\" list."
            )

        url = config.get("url", "http://homeassistant.local:8123")
        token = config.get("token", "")
        if not token:
            return self.say("Home Assistant token is missing in the config file.")

        domain, service = _SERVICE_MAP.get(intent, ("", ""))
        if not domain:
            return self.pick("unknown")

        target_entities = config.get("entities", {}).get(intent, config.get("entities", {}).get(_ENTITY_HINTS.get(intent)))
        if not target_entities:
            prompt = _HINT_PROMPTS.get(intent, "Entity not configured.")
            return self.say(prompt)

        if isinstance(target_entities, str):
            target_entities = [target_entities]

        if intent == "set_thermostat":
            temperature = entities.number or 22
            data = {"entity_id": target_entities, "temperature": temperature}
        elif intent == "security_check":
            data = {"entity_id": target_entities}
        else:
            data = {"entity_id": target_entities}

        ok = _ha_call(url, token, domain, service, data)
        if ok:
            return self.say(random.choice(_SUCCESS_PROMPTS.get(intent, ["Done."])))
        return self.say(random.choice(_ERROR_PROMPTS.get(intent, ["Failed."])))
