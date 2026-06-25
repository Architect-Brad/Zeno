"""
Zeno Core Loop
Orchestrates NLU → Skills → Response for each user turn.
Handles multi-turn slot-filling, confidence thresholds, and plugin auto-discovery.
"""

from zeno.nlu.pipeline import process as nlu_process, NLUResult
from zeno.core.context import Context
from zeno.core.plugins import load_plugins
from zeno.skills.time_skill import TimeSkill
from zeno.skills.conversation import ConversationSkill
from zeno.skills.reminders import ReminderSkill
from zeno.skills.system import SystemSkill
from zeno.skills.calculator import CalculatorSkill
from zeno.skills.weather import WeatherSkill
from zeno.skills.news import NewsSkill
from zeno.response.engine import pick

CONFIDENCE_THRESHOLD = 0.30

_conversation_skill = ConversationSkill()
_reminder_skill = ReminderSkill()

_BUILTIN_SKILLS = [
    TimeSkill(),
    _conversation_skill,
    _reminder_skill,
    SystemSkill(),
    CalculatorSkill(),
    WeatherSkill(),
    NewsSkill(),
]

_PLUGIN_SKILLS: list = []


def _rebuild():
    global _INTENT_MAP, _SLOT_OWNERS, _SKILLS, _PLUGIN_SKILLS
    _PLUGIN_SKILLS = load_plugins()
    _SKILLS = _BUILTIN_SKILLS + _PLUGIN_SKILLS
    _INTENT_MAP = {}
    for skill in _SKILLS:
        for intent in skill.intents:
            _INTENT_MAP[intent] = skill
    _SLOT_OWNERS = {
        "set_alarm": _reminder_skill,
        "set_timer": _reminder_skill,
        "set_reminder": _reminder_skill,
        "introduce": _conversation_skill,
    }


_OVERRIDE_INTENTS = {"cancel", "farewell"}

# Build on first import
_rebuild()


def process_input(text: str, context: Context) -> str:
    if not text.strip():
        return ""

    # --- Multi-turn slot-filling ---
    awaiting = context.awaiting()
    if awaiting:
        result: NLUResult = nlu_process(text, context_intent=awaiting.intent)
        # Only respect override intents if the match is very clear AND
        # the text doesn't look like a direct answer (single word / short phrase)
        should_override = (
            result.intent in _OVERRIDE_INTENTS
            and result.confidence > 0.6
            and len(text.split()) < 3
        )
        if should_override:
            context.clear_awaiting()
        else:
            owner = _SLOT_OWNERS.get(awaiting.intent, _reminder_skill)
            response = owner.fill_slot(awaiting.slot, text, context)
            context.push(awaiting.intent, result.entities, response)
            return response

    result: NLUResult = nlu_process(text)

    # Unknown intent or too low confidence
    if result.intent == "unknown" or result.confidence < CONFIDENCE_THRESHOLD:
        if result.confidence > 0.0:
            response = pick("low_confidence", intent=result.intent.replace("_", " "))
        else:
            response = pick("unknown")
        context.push(result.intent, result.entities, response)
        return response

    # Handle multi-intent: route the primary intent, log the secondary
    if result.is_multi and result.secondary_intent:
        context.set_pending("secondary_intent", result.secondary_intent)

    # Resolve pronoun references from context
    resolved = context.resolve(result.entities)

    skill = _INTENT_MAP.get(result.intent)

    if skill:
        response = skill.handle(result.intent, resolved, context)
    else:
        response = pick("unknown")

    context.push(result.intent, resolved, response)
    return response
