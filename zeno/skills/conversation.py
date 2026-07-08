"""Zeno Conversation Skill — greetings, identity, distress, unknowns."""

from datetime import datetime
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities, extract_entities
from zeno.core.context import Context
from zeno.core.profile import load_profile


class ConversationSkill(BaseSkill):
    intents = [
        "greeting", "farewell", "thanks", "affirm",
        "deny", "identity_query", "emotional_distress",
        "cancel", "unknown", "fun_request",
    ]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        hour = datetime.now().hour
        profile = load_profile()

        if intent == "greeting":
            if not profile.is_known:
                context.await_slot("introduce", "name")
                return self.say("Hey — I'm Zeno. What should I call you?")

            base = (
                self.pick("greeting_morning") if hour < 12
                else self.pick("greeting") if hour < 18
                else self.pick("greeting_evening")
            )
            base = base.rstrip(".?!")
            return self.say(f"{base}, {profile.name}.")

        if intent == "farewell":
            return self.pick("farewell")

        if intent == "thanks":
            return self.pick("thanks")

        if intent == "affirm":
            return self.pick("affirm_received")

        if intent == "deny":
            return self.pick("deny_received")

        if intent == "cancel":
            context.clear_awaiting()
            return self.pick("cancel")

        if intent == "identity_query":
            return self.pick("identity")

        if intent == "emotional_distress":
            return self.pick("distress_response")

        if intent == "fun_request":
            return self.say("I'm not much of an entertainer yet — but I can set timers, check the weather, and control your device. What do you need?")

        return self.pick("unknown")

    # Utterances that mean the person didn't actually answer "what's
    # your name" — they said something else while the slot happened to
    # be open. Treating these as names was a real bug: saying "thanks"
    # right after being asked your name would save "Thanks" as your name.
    _NON_NAME_WORDS = {
        "hey", "hi", "hello", "yes", "no", "thanks", "thank you", "ok",
        "okay", "sure", "bye", "goodbye", "stop", "nothing", "nevermind",
        "never mind", "sorry", "please", "cancel", "whatever",
    }
    _NON_NAME_INTENTS = {
        "thanks", "farewell", "greeting", "affirm", "deny", "cancel",
        "unknown", "emotional_distress",
    }

    def fill_slot(self, slot: str, raw_text: str, context: Context) -> str:
        if slot == "name":
            from zeno.core.profile import save_name
            from zeno.nlu.intent import classify_intent

            # If this reads as a recognized command/response rather than
            # a name, don't capture it as one.
            classified = classify_intent(raw_text)
            if classified.confidence > 0.6 and classified.intent in self._NON_NAME_INTENTS:
                context.clear_awaiting()
                return self.say("No worries — what can I help you with?")

            # Try entity extraction first
            entities = extract_entities(raw_text, "introduce")
            name = entities.name
            if name and name.lower() not in self._NON_NAME_WORDS:
                save_name(name)
                context.clear_awaiting()
                return self.say(f"Good to meet you, {name}. What do you need?")

            # Fallback: strip common filler
            name = raw_text.strip().title()
            for prefix in ("i'm ", "im ", "i am ", "call me ", "it's ", "its ", "my name is "):
                if name.lower().startswith(prefix):
                    name = name[len(prefix):].strip().title()
                    break

            if not name or name.lower() in self._NON_NAME_WORDS:
                context.clear_awaiting()
                return self.say("No worries — what can I help you with?")

            save_name(name)
            context.clear_awaiting()
            return self.say(f"Good to meet you, {name}. What do you need?")
        context.clear_awaiting()
        return self.pick("unknown")
