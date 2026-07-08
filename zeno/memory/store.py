"""
Zeno Persistent Memory Store
SQLite-backed key-value store. Everything stays local — no network calls.
"""

import json
import sqlite3
import threading
from pathlib import Path
from platformdirs import user_data_dir


def _db_path() -> Path:
    data_dir = Path(user_data_dir("zeno", "zeno-assistant"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "zeno.db"


class Store:
    """
    Note on threading: daemon mode runs the web server, LAN Discovery,
    SyncClient, and ProactiveEngine each on their own thread, all sharing
    this one singleton. sqlite3 connections aren't safe for concurrent
    use from multiple threads by default, so we open with
    check_same_thread=False and serialize access with a lock.
    """

    def __init__(self, path: Path | None = None):
        self.path = path or _db_path()
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._conn.commit()

    def get(self, key: str, default=None):
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return row[0]

    def set(self, key: str, value):
        serialized = json.dumps(value)
        with self._lock:
            self._conn.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, serialized),
            )
            self._conn.commit()

    def delete(self, key: str):
        with self._lock:
            self._conn.execute("DELETE FROM kv WHERE key = ?", (key,))
            self._conn.commit()

    def log_event(self, kind: str, payload: dict):
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (kind, payload) VALUES (?, ?)",
                (kind, json.dumps(payload)),
            )
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()):
        """Run a read-only ad-hoc query under the connection lock.
        Prefer get/set/log_event for normal use; this exists for callers
        (like the personalisation engine) that need custom aggregation
        SQL without reaching into `_conn` directly and skipping the lock.
        """
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self):
        with self._lock:
            self._conn.close()


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
