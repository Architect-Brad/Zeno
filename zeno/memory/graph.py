"""
Zeno Knowledge Graph — local triple store for entities and relationships.
SQLite-backed. Stores (subject, predicate, object) triples with
optional weights and timestamps. Supports fuzzy entity lookup and
basic inference through transitive relationships.
"""

import json
import sqlite3
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from platformdirs import user_data_dir


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    weight: float = 1.0
    source: str = "manual"
    created_at: str | None = None


@dataclass
class Entity:
    name: str
    type: str = "unknown"          # person / place / thing / concept / event
    aliases: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


def _db_path() -> Path:
    data_dir = Path(user_data_dir("zeno", "zeno-assistant"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "knowledge.db"


class KnowledgeGraph:
    def __init__(self, path: Path | None = None):
        self.path = path or _db_path()
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._seed_defaults()

    def _init_schema(self):
        c = self._conn
        c.execute("""
            CREATE TABLE IF NOT EXISTS triples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                source TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_triples_subject
            ON triples(subject)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_triples_predicate
            ON triples(predicate)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_triples_object
            ON triples(object)
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                type TEXT DEFAULT 'unknown',
                aliases TEXT DEFAULT '[]',
                properties TEXT DEFAULT '{}'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                intent TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_used TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (intent)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.commit()

    def _seed_defaults(self):
        count = self._conn.execute(
            "SELECT COUNT(*) FROM triples"
        ).fetchone()[0]
        if count > 0:
            return

        defaults = [
            ("zeno", "is_a", "voice assistant"),
            ("zeno", "created_by", "Architect-Brad"),
            ("zeno", "runs_on", "device"),
            ("zeno", "supports", "74 intents"),
            ("zeno", "supports", "9 languages"),
            ("zeno", "is", "privacy-first"),
            ("zeno", "is", "offline-capable"),
            ("wake_word", "is", "hey zeno"),
            ("home_assistant", "integrates_with", "zeno"),
        ]
        for s, p, o in defaults:
            self.add_triple(s, p, o, source="builtin")

        default_entities = [
            Entity("zeno", "ai", ["Zeno", "assistant", "helper"], {"version": "1.0.0"}),
            Entity("home_assistant", "service", ["HA", "home-assistant"], {}),
        ]
        for e in default_entities:
            self.add_entity(e)

    def add_triple(self, subject: str, predicate: str, object: str,
                   weight: float = 1.0, source: str = "manual"):
        self._conn.execute(
            "INSERT INTO triples (subject, predicate, object, weight, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject.lower(), predicate.lower(), object.lower(), weight, source),
        )
        self._conn.commit()

    def add_entity(self, entity: Entity):
        self._conn.execute(
            "INSERT OR REPLACE INTO entities (name, type, aliases, properties) "
            "VALUES (?, ?, ?, ?)",
            (
                entity.name.lower(),
                entity.type,
                json.dumps(entity.aliases),
                json.dumps(entity.properties),
            ),
        )
        self._conn.commit()

    def query(self, subject: str | None = None,
              predicate: str | None = None,
              object: str | None = None,
              limit: int = 50) -> list[Triple]:
        clauses = []
        params = []
        if subject:
            clauses.append("subject = ?")
            params.append(subject.lower())
        if predicate:
            clauses.append("predicate = ?")
            params.append(predicate.lower())
        if object:
            clauses.append("object = ?")
            params.append(object.lower())

        where = " AND ".join(clauses) if clauses else "1=1"
        rows = self._conn.execute(
            f"SELECT * FROM triples WHERE {where} ORDER BY weight DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [
            Triple(r["subject"], r["predicate"], r["object"],
                   r["weight"], r["source"], r["created_at"])
            for r in rows
        ]

    def query_related(self, entity: str, max_depth: int = 2) -> list[Triple]:
        """Find all triples related to an entity, with transitive expansion."""
        seen: set[int] = set()
        results: list[Triple] = []
        frontier = {entity.lower()}
        for _ in range(max_depth):
            if not frontier:
                break
            placeholders = ",".join("?" for _ in frontier)
            rows = self._conn.execute(
                f"SELECT * FROM triples WHERE "
                f"subject IN ({placeholders}) OR object IN ({placeholders})",
                list(frontier) * 2,
            ).fetchall()
            new_frontier: set[str] = set()
            for r in rows:
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                results.append(Triple(
                    r["subject"], r["predicate"], r["object"],
                    r["weight"], r["source"], r["created_at"],
                ))
                new_frontier.add(r["subject"])
                new_frontier.add(r["object"])
            frontier = new_frontier - {entity.lower()}
        return results

    def get_entity(self, name: str) -> Entity | None:
        row = self._conn.execute(
            "SELECT * FROM entities WHERE name = ?", (name.lower(),)
        ).fetchone()
        if not row:
            return None
        return Entity(
            name=row["name"],
            type=row["type"],
            aliases=json.loads(row["aliases"]),
            properties=json.loads(row["properties"]),
        )

    def find_entity(self, text: str) -> Entity | None:
        """Fuzzy entity lookup by name or alias."""
        lower = text.lower()
        row = self._conn.execute(
            "SELECT * FROM entities WHERE name = ?", (lower,)
        ).fetchone()
        if row:
            return Entity(
                name=row["name"], type=row["type"],
                aliases=json.loads(row["aliases"]),
                properties=json.loads(row["properties"]),
            )
        rows = self._conn.execute("SELECT * FROM entities").fetchall()
        for r in rows:
            aliases = json.loads(r["aliases"])
            if any(a.lower() == lower for a in aliases):
                return Entity(
                    name=r["name"], type=r["type"],
                    aliases=aliases,
                    properties=json.loads(r["properties"]),
                )
        return None

    def get_facts(self, subject: str) -> list[str]:
        """Get human-readable facts about a subject."""
        triples = self.query(subject=subject)
        return [f"{t.subject} {t.predicate} {t.object}" for t in triples]

    def log_usage(self, intent: str):
        self._conn.execute("""
            INSERT INTO usage_stats (intent, count, last_used)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(intent) DO UPDATE SET
                count = count + 1,
                last_used = CURRENT_TIMESTAMP
        """, (intent,))
        self._conn.commit()

    def get_usage_stats(self, top_n: int = 20) -> list[tuple[str, int, str]]:
        rows = self._conn.execute(
            "SELECT intent, count, last_used FROM usage_stats "
            "ORDER BY count DESC LIMIT ?", (top_n,)
        ).fetchall()
        return [(r["intent"], r["count"], r["last_used"]) for r in rows]

    def set_preference(self, key: str, value: Any):
        self._conn.execute("""
            INSERT INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, json.dumps(value)))
        self._conn.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM user_preferences WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def get_all_preferences(self) -> dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value FROM user_preferences"
        ).fetchall()
        result: dict[str, Any] = {}
        for r in rows:
            try:
                result[r["key"]] = json.loads(r["value"])
            except (json.JSONDecodeError, TypeError):
                result[r["key"]] = r["value"]
        return result

    def close(self):
        self._conn.close()


_graph: KnowledgeGraph | None = None


def get_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph
