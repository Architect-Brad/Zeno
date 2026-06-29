"""
Zeno Core Loop
Orchestrates NLU → Skills → Response for each user turn.
Handles multi-turn slot-filling, confidence thresholds, and plugin auto-discovery.
"""

import re
from zeno.nlu.pipeline import process as nlu_process, NLUResult
from zeno.nlu.entity import extract_entities
from zeno.core.context import Context
from zeno.core.plugins import load_plugins
from zeno.skills.time_skill import TimeSkill
from zeno.skills.conversation import ConversationSkill
from zeno.skills.reminders import ReminderSkill
from zeno.skills.system import SystemSkill
from zeno.skills.calculator import CalculatorSkill
from zeno.skills.weather import WeatherSkill
from zeno.skills.news import NewsSkill
from zeno.skills.extras import ExtrasSkill
from zeno.skills.home_assistant import HomeAssistantSkill
from zeno.skills.search import SearchSkill, try_ddg_fallback
from zeno.skills.joke import JokeSkill
from zeno.skills.riddle import RiddleSkill
from zeno.skills.coin import CoinSkill
from zeno.skills.dice import DiceSkill
from zeno.skills.notes import NotesSkill
from zeno.skills.notebook import NotebookSkill
from zeno.skills.clear import ClearSkill
from zeno.skills.quote import QuoteSkill
from zeno.skills.fact import FactSkill
from zeno.skills.currency import CurrencySkill
from zeno.skills.converter import ConverterSkill
from zeno.skills.timezone import TimezoneSkill
from zeno.skills.sleep import SleepSkill
from zeno.skills.fan import FanSkill
from zeno.skills.scene import SceneSkill
from zeno.skills.countdown import CountdownSkill
from zeno.skills.shuffle import ShuffleSkill
from zeno.skills.repeat import RepeatSkill
from zeno.skills.playlist import PlaylistSkill
from zeno.skills.lyrics import LyricsSkill
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
    ExtrasSkill(),
    HomeAssistantSkill(),
    SearchSkill(),
    JokeSkill(),
    RiddleSkill(),
    CoinSkill(),
    DiceSkill(),
    NotesSkill(),
    NotebookSkill(),
    ClearSkill(),
    QuoteSkill(),
    FactSkill(),
    CurrencySkill(),
    ConverterSkill(),
    TimezoneSkill(),
    SleepSkill(),
    FanSkill(),
    SceneSkill(),
    CountdownSkill(),
    ShuffleSkill(),
    RepeatSkill(),
    PlaylistSkill(),
    LyricsSkill(),
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


_OVERRIDE_INTENTS = {"cancel", "farewell", "stop_timer", "pause_music"}

# Build on first import
_rebuild()

_FRAGMENT_WORDS = {"in", "at", "near", "for", "about", "on", "to", "how"}


def _is_fragment(text: str) -> bool:
    """Check if text looks like a dialog fragment (not a standalone query)."""
    lower = text.strip().lower()
    words = lower.split()
    if len(words) > 4:
        return False
    # "how about X" / "what about X" are follow-up fragments
    if lower.startswith("how about") or lower.startswith("what about"):
        return True
    # Wh-words start new queries, not fragments
    if any(w in lower for w in ("what", "how", "who", "where", "when", "why")):
        return False
    if len(words) == 1 and words[0] in ("yes", "no", "ok", "okay", "sure", "bye"):
        return False
    # Verb+particle combos are commands, not fragments
    verb_particles = {"turn on", "turn off", "switch on", "switch off", "set"}
    if any(lower.startswith(vp) for vp in verb_particles):
        return False
    # Check for preposition + entity or bare entity
    has_entity = False
    e = extract_entities(text)
    if e.date or e.time or e.duration:
        has_entity = True
    if re.search(r'\b(in|at|near|for|about|on)\b', lower) and len(words) >= 2:
        has_entity = True
    return has_entity and len(words) <= 4


def _process_single(text: str, context: Context, hint_intent: str | None = None) -> str:
    """Process a single utterance — no multi-intent splitting."""
    if not text.strip():
        return ""

    # --- Multi-turn slot-filling ---
    awaiting = context.awaiting()
    if awaiting:
        result: NLUResult = nlu_process(text, context_intent=awaiting.intent)
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

    # --- Same-skill multi-intent hint ---
    if hint_intent and (result.intent == "unknown" or result.confidence < CONFIDENCE_THRESHOLD):
        result = nlu_process(text, context_intent=hint_intent)

    # --- Dialog state machine: fragment carry-over ---
    if (result.intent == "unknown" or result.confidence < CONFIDENCE_THRESHOLD):
        if _is_fragment(text) and context.last_intent():
            fragment_entities = extract_entities(text)
            last_entities = context.last_entities()
            merged = result.entities
            if last_entities:
                if fragment_entities.location and not merged.location:
                    merged.location = fragment_entities.location
                if fragment_entities.date and not merged.date:
                    merged.date = fragment_entities.date
                if fragment_entities.time and not merged.time:
                    merged.time = fragment_entities.time
                if fragment_entities.duration and not merged.duration:
                    merged.duration = fragment_entities.duration
            last_intent = context.last_intent()
            context.push(last_intent, merged, "")
            skill = _INTENT_MAP.get(last_intent)
            if skill:
                response = skill.handle(last_intent, merged, context)
                context.push(last_intent, merged, response)
                return response

    # Unknown intent or too low confidence
    if result.intent == "unknown" or result.confidence < CONFIDENCE_THRESHOLD:
        # DuckDuckGo fallback: try to answer anyway if confidence is marginal
        if 0.15 < result.confidence < CONFIDENCE_THRESHOLD:
            from zeno.skills.search import try_ddg_fallback
            ddg_response = try_ddg_fallback(text)
            if ddg_response:
                context.push("search_result", result.entities, ddg_response)
                return ddg_response
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


def process_input(text: str, context: Context) -> str:
    text = text.strip()
    if not text:
        return ""

    # --- Multi-intent parsing: split on "and" / commas ---
    if not context.awaiting():
        # Split on ", and", ", or", ", " and " and " with simple heuristics
        parts = re.split(r'\s*,?\s+(?:and|or)\s+|\s*,\s*', text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) > 1:
            responses = []
            prev_intent = None
            for i, part in enumerate(parts):
                # For same-skill multi-intent, pass previous intent as hint
                resp = _process_single(part, context, hint_intent=prev_intent)
                responses.append(resp)
                # Track last classified intent for the next part
                li = context.last_intent()
                if li:
                    prev_intent = li
            return "  ".join(responses)

    return _process_single(text, context)
