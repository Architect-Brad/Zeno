"""Tests for the web dashboard API: sync auth, rate limiting, health endpoint."""

import os
import tempfile

import pytest

import zeno.memory.store as store_mod
from zeno.memory.store import Store


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)
    os.environ.pop("ZENO_SYNC_TOKEN", None)

    # Reset per-process web state so tests don't leak sessions/rate-limit
    # counters into each other.
    import zeno.web.routes as routes
    routes._sessions.clear()
    routes._history.clear()

    import zeno.web.app as app_mod
    app_mod._request_log.clear()


def _client():
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from zeno.web.app import create_app
    app = create_app(web_port=8099, enable_sync=False)
    return fastapi_testclient.TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint (previously crashed: PlatformCaps has no `notifications`)
# ---------------------------------------------------------------------------

def test_health_endpoint_returns_200():
    client = _client()
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "caps" in body
    assert "notifications" in body["caps"]


def test_health_endpoint_requires_no_auth():
    client = _client()
    r = client.get("/api/health")
    assert r.status_code != 401


# ---------------------------------------------------------------------------
# Sync endpoints require the pairing token
# ---------------------------------------------------------------------------

def test_sync_pull_rejects_missing_token():
    client = _client()
    r = client.get("/api/sync/pull")
    assert r.status_code == 401


def test_sync_pull_rejects_wrong_token():
    from zeno.core.sync import SYNC_TOKEN_HEADER
    client = _client()
    r = client.get("/api/sync/pull", headers={SYNC_TOKEN_HEADER: "wrong"})
    assert r.status_code == 401


def test_sync_pull_accepts_correct_token():
    from zeno.core.sync import sync_token, SYNC_TOKEN_HEADER
    client = _client()
    r = client.get("/api/sync/pull", headers={SYNC_TOKEN_HEADER: sync_token()})
    assert r.status_code == 200
    body = r.json()
    assert "instance_id" in body
    assert "turns" in body


def test_sync_push_rejects_missing_token():
    client = _client()
    r = client.post("/api/sync/push", json={"instance_id": "x", "turns": []})
    assert r.status_code == 401


def test_sync_push_accepts_correct_token_and_merges():
    from zeno.core.sync import sync_token, SYNC_TOKEN_HEADER
    client = _client()
    r = client.post(
        "/api/sync/push",
        headers={SYNC_TOKEN_HEADER: sync_token()},
        json={
            "instance_id": "peer-42",
            "turns": [{"intent": "thanks", "response": "You're welcome!"}],
            "profile": {},
            "timers": [],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["merged"] == 1


def test_sync_peers_rejects_missing_token():
    client = _client()
    r = client.get("/api/sync/peers")
    assert r.status_code == 401


def test_sync_peers_accepts_correct_token():
    from zeno.core.sync import sync_token, SYNC_TOKEN_HEADER
    client = _client()
    r = client.get("/api/sync/peers", headers={SYNC_TOKEN_HEADER: sync_token()})
    assert r.status_code == 200
    assert "peers" in r.json()


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_allows_requests_under_the_cap():
    client = _client()
    for _ in range(10):
        r = client.get("/api/health")
        assert r.status_code == 200


def test_rate_limit_blocks_after_cap_exceeded():
    import zeno.web.app as app_mod
    client = _client()

    # Lower the cap for this test so we don't need 120 real requests
    original = app_mod._RATE_LIMIT_REQUESTS
    app_mod._RATE_LIMIT_REQUESTS = 5
    try:
        statuses = [client.get("/api/health").status_code for _ in range(8)]
    finally:
        app_mod._RATE_LIMIT_REQUESTS = original

    assert statuses.count(200) == 5
    assert statuses.count(429) == 3


def test_rate_limit_is_per_client_ip():
    import zeno.web.app as app_mod

    app_mod._request_log.clear()
    assert app_mod._rate_limited("1.2.3.4") is False
    # Exhaust the cap for one IP...
    for _ in range(app_mod._RATE_LIMIT_REQUESTS):
        app_mod._rate_limited("1.2.3.4")
    assert app_mod._rate_limited("1.2.3.4") is True
    # ...a different IP should be unaffected
    assert app_mod._rate_limited("5.6.7.8") is False


# ---------------------------------------------------------------------------
# Chat/history sanity (not the focus of this pass, but cheap to confirm
# they still work after the middleware/auth changes above)
# ---------------------------------------------------------------------------

def test_chat_endpoint_basic_round_trip():
    client = _client()
    r = client.post("/api/chat", json={"text": "what time is it"})
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
