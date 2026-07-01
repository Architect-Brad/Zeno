"""
Zeno Knowledge Skill
Answers questions from the local knowledge graph.
Handles "what is X", "tell me about X", facts about known entities.
"""

from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.memory.graph import get_graph


class KnowledgeSkill(BaseSkill):
    intents = ["knowledge_query"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        graph = get_graph()
        text = (entities.raw.get("text", "") if entities.raw else "")

        # Try to find the subject
        about = None
        prefixes = ["tell me about", "what is", "what's", "who is",
                     "describe", "what do you know about", "facts about"]
        lower = text.lower()
        for p in prefixes:
            if lower.startswith(p):
                about = text[len(p):].strip().strip("?").strip()
                break

        if not about:
            # Try entity extraction
            about = entities.name or entities.raw_target

        if not about:
            return self.say(
                "I can tell you about things in my knowledge base. "
                "Try 'what is zeno' or 'tell me about home assistant'."
            )

        # Look up in graph
        entity = graph.find_entity(about)
        if entity:
            facts = graph.get_facts(entity.name)
            if facts:
                return self.say(
                    f"About {entity.name.title()} ({entity.type}): "
                    + "; ".join(facts)
                )
            return self.say(
                f"I know about {entity.name.title()} but I don't have "
                f"many facts stored yet."
            )

        # Try as a general query — check if it's someone/something in the triples
        triples = graph.query(subject=about)
        if not triples:
            triples = graph.query(object=about)
        if triples:
            facts = [f"{t.subject} {t.predicate} {t.object}" for t in triples[:5]]
            return self.say(
                f"About {about.title()}: " + "; ".join(facts)
            )

        return self.say(
            f"I don't know about '{about}' yet. "
            "You can teach me by setting facts in the knowledge graph."
        )
