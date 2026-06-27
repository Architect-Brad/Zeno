"""
Zeno Search Skill
Multi-backend knowledge retrieval:
  - Free Dictionary API (dictionaryapi.dev) for word definitions
  - DuckDuckGo Instant Answer API for general queries, news, places
  - DDG RelatedTopics as fallback
All free, no API keys required.
"""

import json
import re
import urllib.parse
import urllib.request
import urllib.error
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.response.engine import pick as response_pick

_DDG_URL = "https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
_DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


def _fetch_json(url: str, timeout: int = 6) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Zeno/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None


def _ddg_query(query: str) -> dict | None:
    data = _fetch_json(_DDG_URL.format(q=urllib.parse.quote(query)))
    return data if isinstance(data, dict) else None


def _dict_definition(word: str) -> str | None:
    """Fetch word definition from Free Dictionary API."""
    data = _fetch_json(_DICT_URL.format(word=urllib.parse.quote(word)))
    if not data or not isinstance(data, list) or not data:
        return None
    entry = data[0]
    meanings = entry.get("meanings", [])
    if not meanings:
        return None
    parts = []
    for m in meanings[:2]:
        part_of_speech = m.get("partOfSpeech", "")
        defs = m.get("definitions", [])
        if defs:
            d = defs[0].get("definition", "")
            if d:
                parts.append(f"({part_of_speech}) {d}" if part_of_speech else d)
    return "  ".join(parts[:2]) if parts else None


def _extract_ddg_answer(data: dict) -> str | None:
    if data.get("AbstractText"):
        return data["AbstractText"][:400]
    if data.get("Answer"):
        return data["Answer"]
    if data.get("Definition") and data["Definition"] not in ("", " "):
        return data["Definition"]
    # Infobox as fallback
    infobox = data.get("Infobox", {})
    if isinstance(infobox, dict):
        content = infobox.get("content", [])
        if content:
            parts = []
            for item in content[:3]:
                label = item.get("label", "")
                val = item.get("value", "")
                if label and val:
                    parts.append(f"{label}: {val}")
            if parts:
                return "; ".join(parts)
    # RelatedTopics as last resort
    topics = data.get("RelatedTopics", [])
    if topics and isinstance(topics, list):
        for t in topics[:3]:
            if isinstance(t, dict) and t.get("Text"):
                return t["Text"][:300]
    return None


def try_ddg_fallback(text: str) -> str | None:
    """Called from loop.py when confidence is 0.20-0.30. Returns answer or None."""
    data = _ddg_query(text)
    if not data:
        return None
    answer = _extract_ddg_answer(data)
    if answer:
        return response_pick("ddg_answer", answer=answer)
    return None


class SearchSkill(BaseSkill):
    intents = ["define_word", "translate_phrase", "news_query", "find_place"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        if intent == "define_word":
            return self._define(entities)
        if intent == "translate_phrase":
            return self._translate(entities)
        if intent == "news_query":
            return self._news(entities)
        if intent == "find_place":
            return self._find_place(entities)
        return self.pick("unknown")

    def _define(self, entities: Entities) -> str:
        raw = entities.raw.get("text", "")
        word = re.sub(r"^(define|definition of|what does|what is|what's|meaning of)\s+", "", raw, flags=re.IGNORECASE).strip()
        word = entities.expression or word
        if not word:
            return response_pick("ddg_no_result")
        # Try Free Dictionary API first
        definition = _dict_definition(word)
        if definition:
            return response_pick("definition", word=word.capitalize(), definition=definition)
        # Fallback: DuckDuckGo
        data = _ddg_query(f"define {word}")
        if data:
            answer = _extract_ddg_answer(data)
            if answer:
                return response_pick("definition", word=word.capitalize(), definition=answer)
        return response_pick("ddg_no_result")

    def _translate(self, entities: Entities) -> str:
        text = entities.raw.get("text", "").strip()
        text = re.sub(r"^(translate|how do you say|how to say|what is)\s+", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s+(in|to|into)\s+\w+$", "", text, flags=re.IGNORECASE).strip()
        if not text:
            return response_pick("ddg_no_result")
        data = _ddg_query(f"translate {text}")
        if data:
            answer = _extract_ddg_answer(data)
            if answer:
                return response_pick("translation", translation=answer)
        return response_pick("ddg_no_result")

    def _news(self, entities: Entities) -> str:
        topic = entities.raw.get("text", "").strip()
        topic = re.sub(r"^(news|what'?s the news|what is the news|news about)\s+", "", topic, flags=re.IGNORECASE).strip()
        if not topic or topic in ("news",):
            topic = "top headlines"
        data = _ddg_query(topic)
        if data:
            answer = _extract_ddg_answer(data)
            if answer:
                return response_pick("news_headline", headline=answer[:200])
        return self.say("No news found about that.")

    def _find_place(self, entities: Entities) -> str:
        query = entities.raw.get("text", "").strip()
        if not query:
            return response_pick("ddg_no_result")
        data = _ddg_query(query)
        if data:
            answer = _extract_ddg_answer(data)
            if answer:
                return response_pick("place_result", name=query, description=answer[:200])
        return response_pick("ddg_no_result")
