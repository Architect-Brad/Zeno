"""Tests for LAN sync: identity, pairing-token auth, and context merging."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import zeno.memory.store as store_mod
from zeno.memory.store import Store


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store_mod._store = Store(path=path)
    os.environ.pop("ZENO_SYNC_TOKEN", None)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def test_instance_id_is_stable_and_persisted():
    from zeno.core.sync import instance_id

    first = instance_id()
    second = instance_id()
    assert first == second
    assert len(first) > 0


def test_device_name_defaults_and_persists():
    from zeno.core.sync import device_name

    first = device_name()
    second = device_name()
    assert first == second
    assert first  # non-empty


# ---------------------------------------------------------------------------
# Pairing token
# ---------------------------------------------------------------------------

def test_sync_token_generated_once_and_persisted():
    from zeno.core.sync import sync_token

    first = sync_token()
    second = sync_token()
    assert first == second
    assert len(first) >= 32  # secrets.token_hex(24) -> 48 hex chars


def test_sync_token_env_override():
    from zeno.core.sync import sync_token

    os.environ["ZENO_SYNC_TOKEN"] = "my-custom-token"
    try:
        assert sync_token() == "my-custom-token"
    finally:
        os.environ.pop("ZENO_SYNC_TOKEN", None)


def test_verify_token_accepts_correct_token():
    from zeno.core.sync import sync_token, verify_token

    tok = sync_token()
    assert verify_token(tok) is True


def test_verify_token_rejects_wrong_or_missing_token():
    from zeno.core.sync import verify_token

    assert verify_token("definitely-wrong") is False
    assert verify_token(None) is False
    assert verify_token("") is False


# ---------------------------------------------------------------------------
# Context / profile / timer serialization
# ---------------------------------------------------------------------------

def test_context_to_dict_round_trips_turns():
    from zeno.core.context import Context
    from zeno.core.sync import context_to_dict

    ctx = Context()
    ctx.push("time_query", None, "It's 5 PM")
    d = context_to_dict(ctx)
    assert d["turns"][0]["intent"] == "time_query"
    assert d["turns"][0]["response"] == "It's 5 PM"


def test_profile_to_dict_reflects_saved_profile():
    from zeno.core.profile import save_name
    from zeno.core.sync import profile_to_dict

    save_name("Robin")
    d = profile_to_dict()
    assert d["name"] == "Robin"


# ---------------------------------------------------------------------------
# ContextMerger
# ---------------------------------------------------------------------------

def test_merge_turns_deduplicates_by_response():
    from zeno.core.context import Context
    from zeno.core.sync import ContextMerger

    local = Context()
    local.push("thanks", None, "You're welcome!")

    remote_turns = [
        {"intent": "thanks", "response": "You're welcome!"},  # duplicate, skipped
        {"intent": "time_query", "response": "It's noon"},     # new, merged
    ]
    merged = ContextMerger.merge_turns(local, remote_turns)
    assert merged == 1
    assert len(local._turns) == 2


def test_merge_turns_caps_history_length():
    from zeno.core.context import Context
    from zeno.core.sync import ContextMerger, _MAX_TURNS_PER_PEER

    local = Context()
    remote_turns = [
        {"intent": "x", "response": f"response {i}"}
        for i in range(_MAX_TURNS_PER_PEER + 10)
    ]
    ContextMerger.merge_turns(local, remote_turns)
    assert len(local._turns) == _MAX_TURNS_PER_PEER


def test_merge_profile_last_writer_wins():
    from zeno.core.profile import load_profile
    from zeno.core.sync import ContextMerger

    ContextMerger.merge_profile({"name": "Alex", "timezone": "UTC"})
    profile = load_profile()
    assert profile.name == "Alex"
    assert profile.timezone == "UTC"


def test_merge_profile_ignores_empty_fields():
    from zeno.core.profile import save_name, load_profile
    from zeno.core.sync import ContextMerger

    save_name("KeepMe")
    ContextMerger.merge_profile({"name": "", "timezone": None})
    assert load_profile().name == "KeepMe"


def test_merge_timers_imports_new_timers_only():
    import time
    from zeno.skills.reminders import ReminderSkill
    from zeno.core.sync import ContextMerger

    ReminderSkill._active_timers.clear()
    ReminderSkill._timer_meta.clear()

    remote_timers = [
        {"label": "Wake up", "seconds": 60, "started": time.time(), "is_alarm": True},
    ]
    ContextMerger.merge_timers(remote_timers)
    labels = {m["label"] for m in ReminderSkill._timer_meta}
    assert "Wake up" in labels

    # Importing the same label again should not duplicate it
    ContextMerger.merge_timers(remote_timers)
    count = sum(1 for m in ReminderSkill._timer_meta if m["label"] == "Wake up")
    assert count == 1

    ReminderSkill._active_timers.clear()
    ReminderSkill._timer_meta.clear()


def test_merge_timers_skips_already_expired():
    import time
    from zeno.skills.reminders import ReminderSkill
    from zeno.core.sync import ContextMerger

    ReminderSkill._active_timers.clear()
    ReminderSkill._timer_meta.clear()

    remote_timers = [
        {"label": "Long gone", "seconds": 5, "started": time.time() - 100, "is_alarm": False},
    ]
    ContextMerger.merge_timers(remote_timers)
    labels = {m["label"] for m in ReminderSkill._timer_meta}
    assert "Long gone" not in labels


# ---------------------------------------------------------------------------
# Discovery (peer bookkeeping only — no real sockets)
# ---------------------------------------------------------------------------

def test_discovery_records_peer_on_pong_without_opening_socket():
    from zeno.core.sync import Discovery
    import json

    d = Discovery(web_port=8080)
    assert d.peers == {}

    msg = {
        "type": "zeno-pong",
        "instance_id": "peer-123",
        "host": "192.168.1.50",
        "port": 8080,
        "name": "kitchen-pi",
        "version": "1.0",
    }
    d._handle_message(json.dumps(msg).encode(), ("192.168.1.50", 49880))

    assert "peer-123" in d.peers
    assert d.peers["peer-123"].name == "kitchen-pi"


def test_discovery_ignores_own_messages():
    from zeno.core.sync import Discovery, instance_id
    import json

    d = Discovery(web_port=8080)
    msg = {
        "type": "zeno-pong",
        "instance_id": instance_id(),  # our own id
        "host": "127.0.0.1",
        "port": 8080,
        "name": "self",
    }
    d._handle_message(json.dumps(msg).encode(), ("127.0.0.1", 49880))
    assert d.peers == {}


def test_discovery_ignores_malformed_messages():
    from zeno.core.sync import Discovery

    d = Discovery(web_port=8080)
    d._handle_message(b"not json", ("127.0.0.1", 49880))
    assert d.peers == {}


# ---------------------------------------------------------------------------
# SyncClient — verify the pairing token header is sent on push/pull
# ---------------------------------------------------------------------------

def test_sync_client_sends_pairing_token_header():
    from zeno.core.sync import SyncClient, Discovery, Peer, sync_token, SYNC_TOKEN_HEADER
    from zeno.core.context import Context

    discovery = Discovery(web_port=8080)
    peer = Peer(instance_id="peer-1", host="10.0.0.5", port=8080, name="peer", last_seen=0.0)
    discovery.peers["peer-1"] = peer

    client = SyncClient(discovery, Context())

    sent_requests = []

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return b'{"turns": [], "profile": {}, "timers": []}'

    def fake_urlopen(req, timeout=None):
        sent_requests.append(req)
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client._sync_with(peer)

    assert len(sent_requests) == 2  # push, then pull
    push_req, pull_req = sent_requests
    assert push_req.get_header(SYNC_TOKEN_HEADER.capitalize()) == sync_token()
    assert pull_req.get_header(SYNC_TOKEN_HEADER.capitalize()) == sync_token()
