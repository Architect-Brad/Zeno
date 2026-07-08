"""
Zeno NLU Pipeline
Orchestrates preprocessing, intent classification, and entity extraction.
"""

import re
from dataclasses import dataclass

from zeno.nlu.intent import classify_intent, IntentResult
from zeno.nlu.entity import extract_entities, Entities


@dataclass
class NLUResult:
    intent: str
    confidence: float
    entities: Entities
    raw_text: str
    is_multi: bool = False
    secondary_intent: str | None = None
    secondary_confidence: float = 0.0


_WAKE_WORDS = ["hey zeno", "hey zen", "zeno", "ok zeno"]


def _preprocess(text: str) -> tuple[str, bool]:
    """Strip wake word, normalize whitespace. Returns (text, was_woken)."""
    lower = text.lower().strip()
    woken = False

    # Detect bare wake words
    if lower in _WAKE_WORDS:
        return "", True

    for ww in _WAKE_WORDS:
        if lower.startswith(ww + ",") or lower.startswith(ww + " ") or lower == ww:
            text = text[len(ww):].strip().lstrip(",").strip()
            woken = True
            break

    return text, woken


def process(text: str, context_intent: str | None = None) -> NLUResult:
    """
    Full NLU pipeline: preprocess → classify → extract entities.
    """
    cleaned, woken = _preprocess(text)

    if not cleaned and woken:
        # Bare wake word → greeting
        return NLUResult(
            intent="greeting",
            confidence=1.0,
            entities=Entities(),
            raw_text=text,
        )

    if not cleaned:
        return NLUResult(
            intent="unknown",
            confidence=0.0,
            entities=Entities(),
            raw_text=text,
        )

    # Intent classification
    intent_result: IntentResult = classify_intent(cleaned, context_intent=context_intent)

    # Entity extraction (scoped by intent for better accuracy)
    entities = extract_entities(cleaned, intent_hint=intent_result.intent)

    return NLUResult(
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        entities=entities,
        raw_text=cleaned,
        is_multi=intent_result.is_multi,
        secondary_intent=intent_result.secondary_intent,
        secondary_confidence=intent_result.secondary_confidence,
    )
