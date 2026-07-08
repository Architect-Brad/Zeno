"""Zeno Scene Skill — activates Home Assistant scenes."""

from zeno.skills.home_assistant import _load_config, _ha_call
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


class SceneSkill(BaseSkill):
    intents = ["scene_activate"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        config = _load_config()
        if not config:
            return self.say(
                "Scene activation requires Home Assistant. "
                "Create ~/.zeno/home_assistant.json with your server details."
            )
        url = config.get("url", "http://homeassistant.local:8123")
        token = config.get("token", "")
        if not token:
            return self.say("Home Assistant token is missing.")

        scene_entities = config.get("entities", {}).get("scene_activate", config.get("entities", {}).get("scene"))
        if not scene_entities:
            return self.say("No scene configured in home_assistant.json entities.")

        if isinstance(scene_entities, str):
            scene_entities = [scene_entities]

        ok = _ha_call(url, token, "scene", "turn_on", {
            "entity_id": scene_entities,
        })
        if ok:
            return self.say("Scene activated.")
        return self.say("Couldn't activate the scene.")
