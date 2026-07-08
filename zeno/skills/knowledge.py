"""
Zeno Knowledge Skill
Answers "what is X" / "tell me about X" / "who is X" questions.

Tries the local knowledge graph first (facts you or a plugin have
explicitly stored). When that comes up empty, falls back to a
Wikipedia lookup — pure retrieval, not generation: it searches for the
best-matching article title and reads back its existing summary
sentence(s) verbatim, the same way NewsSkill falls back to DuckDuckGo
when its RSS feed has nothing. Nothing here composes new text; it only
finds and reads existing text, which is what keeps this honest about
not hallucinating.

Successful Wikipedia lookups are cached into the local knowledge graph
so a repeat question doesn't need the network again.
"""

import re
import urllib.parse

from zeno.skills.base import BaseSkill
from zeno.skills.search import _fetch_json
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.memory.graph import get_graph, Entity

_WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json&srlimit=1"
_WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def _trim_summary(text: str, max_sentences: int = 2, max_chars: int = 400) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    trimmed = " ".join(sentences[:max_sentences]).strip()
    if len(trimmed) > max_chars:
        trimmed = trimmed[:max_chars].rsplit(" ", 1)[0] + "…"
    return trimmed


def _wikipedia_lookup(query: str) -> tuple[str, str] | None:
    """Search Wikipedia for the best-matching title, then fetch its
    summary. Returns (title, trimmed_summary), or None if nothing
    matched or the network/API failed."""
    search_data = _fetch_json(_WIKI_SEARCH_URL.format(q=urllib.parse.quote(query)))
    if not search_data:
        return None
    hits = search_data.get("query", {}).get("search", [])
    if not hits:
        return None
    title = hits[0].get("title")
    if not title:
        return None

    summary_url = _WIKI_SUMMARY_URL.format(title=urllib.parse.quote(title.replace(" ", "_")))
    summary_data = _fetch_json(summary_url)
    if not summary_data:
        return None
    extract = summary_data.get("extract")
    if not extract:
        return None
    return title, _trim_summary(extract)


class KnowledgeSkill(BaseSkill):
    intents = ["knowledge_query"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        graph = get_graph()
        text = (entities.raw.get("text", "") if entities.raw else "")

        about = self._extract_subject(text, entities)
        if not about:
            return self.say(
                "I can tell you about things in my knowledge base, and I'll "
                "look things up online if I don't already know them. Try "
                "'what is zeno' or 'who was napoleon'."
            )

        # 1. Local knowledge graph — hand-stored facts, or a cached
        #    Wikipedia summary from a previous lookup.
        entity = graph.find_entity(about)
        if entity:
            facts = graph.get_facts(entity.name)
            if facts:
                return self.say(f"About {entity.name.title()} ({entity.type}): " + "; ".join(facts))
            cached_summary = (entity.properties or {}).get("summary")
            if cached_summary:
                return self.say(cached_summary)

        triples = graph.query(subject=about) or graph.query(object=about)
        if triples:
            facts = [f"{t.subject} {t.predicate} {t.object}" for t in triples[:5]]
            return self.say(f"About {about.title()}: " + "; ".join(facts))

        # 2. Nothing local — try Wikipedia as a last resort. This reads
        #    back an existing sentence rather than composing one, so it
        #    can be wrong or outdated, but it isn't inventing anything.
        result = _wikipedia_lookup(about)
        if result:
            title, summary = result
            self._cache_summary(title, summary)
            return self.say(summary)

        return self.say(
            f"I don't know about '{about}' yet, and I couldn't find anything "
            f"about it online just now either."
        )

    @staticmethod
    def _extract_subject(text: str, entities: Entities) -> str | None:
        prefixes = ["tell me about", "what is", "what's", "who is", "who was",
                    "describe", "what do you know about", "facts about"]
        lower = text.lower()
        for p in prefixes:
            if lower.startswith(p):
                subject = text[len(p):].strip().strip("?").strip()
                if subject:
                    return subject
        return entities.name or entities.raw_target

    @staticmethod
    def _cache_summary(title: str, summary: str):
        graph = get_graph()
        graph.add_entity(Entity(
            name=title.lower(),
            type="topic",
            aliases=[],
            properties={"summary": summary, "source": "wikipedia"},
        ))
