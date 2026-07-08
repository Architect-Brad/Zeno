"""
Zeno Personalisation Engine
Learns user preferences from usage patterns, adapts responses,
and builds a persistent conversation memory.
Powered by the knowledge graph backend.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any

from zeno.memory.graph import get_graph, KnowledgeGraph
from zeno.memory.store import get_store
from zeno.core.profile import load_profile, Profile


class Personaliser:
    def __init__(self):
        self.graph = get_graph()
        self.store = get_store()

    def log_interaction(self, intent: str, entities: Any, response: str):
        """Log every user interaction for pattern learning."""
        self.graph.log_usage(intent)
        self.graph.add_triple("user", "asked_for", intent, source="interaction")
        self._update_session()

    def _update_session(self):
        now = time.time()
        last_active = self.store.get("personal.last_active", 0.0)
        self.store.set("personal.last_active", now)
        if last_active and (now - last_active) > 3600:
            sessions = self.store.get("personal.sessions", 0)
            self.store.set("personal.sessions", sessions + 1)

    def get_frequent_intents(self, top_n: int = 5) -> list[tuple[str, int]]:
        """Return the user's most-used intents."""
        stats = self.graph.get_usage_stats(top_n=top_n)
        return [(s[0], s[1]) for s in stats]

    def get_favourite_time(self) -> str | None:
        """Detect when the user most often interacts."""
        rows = self.graph.query_raw(
            "SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt "
            "FROM usage_stats us "
            "JOIN triples t ON t.object = us.intent "
            "WHERE t.predicate = 'asked_for' "
            "GROUP BY hour ORDER BY cnt DESC LIMIT 1"
        )
        if rows:
            return f"{rows[0]['hour']}:00"
        return None

    def time_of_day_greeting(self, profile: Profile) -> str | None:
        """Return a personalised greeting based on time and usage."""
        hour = datetime.now().hour
        name = profile.name or "there"

        if hour < 5:
            base = f"Up late, {name}"
        elif hour < 12:
            base = f"Good morning, {name}"
        elif hour < 17:
            base = f"Good afternoon, {name}"
        else:
            base = f"Good evening, {name}"

        # Check if user has a morning routine
        morning_intents = self.graph.query(
            predicate="asked_for",
            object="weather_query",
        )
        if morning_intents and 7 <= hour <= 9:
            return f"{base}. Would you like the weather forecast?"
        return base

    def learn_preference(self, key: str, value: Any):
        """Persist a learned preference."""
        self.graph.set_preference(f"pref.{key}", value)

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.graph.get_preference(f"pref.{key}", default)

    def learn_location(self, location: str):
        """Remember a frequently-queried location."""
        locations = self.get_preference("frequent_locations", [])
        locations = [l for l in locations if l.lower() != location.lower()]
        locations.insert(0, location)
        self.learn_preference("frequent_locations", locations[:10])

    def learn_volume_preference(self, level: int):
        """Remember preferred volume level."""
        levels = self.get_preference("volume_history", [])
        levels.append({"level": level, "time": time.time()})
        self.learn_preference("volume_history", levels[-50:])

    def get_suggested_volume(self) -> int | None:
        """Return the most common volume level."""
        levels = self.get_preference("volume_history", [])
        if not levels:
            return None
        # Mode of recent levels
        buckets: dict[int, int] = {}
        for entry in levels[-20:]:
            l = entry["level"]
            buckets[l] = buckets.get(l, 0) + 1
        if not buckets:
            return None
        return max(buckets, key=buckets.get)

    def get_conversation_memory(self, n: int = 5) -> list[dict]:
        """Return recent conversation turns from the timeline."""
        rows = self.store.query(
            "SELECT payload FROM events WHERE kind = 'conversation' "
            "ORDER BY created_at DESC, id DESC LIMIT ?", (n,)
        )
        return [json.loads(r[0]) for r in rows]

    def log_conversation(self, user_text: str, response: str, intent: str):
        self.store.log_event("conversation", {
            "user": user_text,
            "response": response,
            "intent": intent,
            "timestamp": time.time(),
        })

    def get_routine(self) -> dict[str, list[str]]:
        """Detect daily routines from usage patterns."""
        rows = self.graph.query_raw("""
            SELECT strftime('%H', created_at) as hour, object as intent,
                   COUNT(*) as cnt
            FROM triples
            WHERE predicate = 'asked_for'
            GROUP BY hour, intent
            HAVING cnt > 1
            ORDER BY hour, cnt DESC
        """)
        routines: dict[str, list[str]] = {}
        for r in rows:
            h = r["hour"]
            if h not in routines:
                routines[h] = []
            routines[h].append(r["intent"])
        return routines

    def should_proactive(self) -> bool:
        """Check if it's appropriate to make a proactive suggestion."""
        last_active = self.store.get("personal.last_active", 0.0)
        if not last_active:
            return False
        now = time.time()
        # Only proactive if user has been idle 10+ minutes
        return (now - last_active) > 600


_personaliser: Personaliser | None = None


def get_personaliser() -> Personaliser:
    global _personaliser
    if _personaliser is None:
        _personaliser = Personaliser()
    return _personaliser
