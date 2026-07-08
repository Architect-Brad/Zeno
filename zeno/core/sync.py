"""
Zeno Sync — cross-device LAN context synchronization.
Discovery via UDP broadcast, sync via REST API.
"""

import hmac
import json
import logging
import secrets
import socket
import struct
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from uuid import uuid4

from zeno.core.context import Context
from zeno.core.profile import Profile, load_profile
from zeno.memory.store import get_store
from zeno.skills.reminders import ReminderSkill

logger = logging.getLogger("zeno.sync")

# UDP discovery
_DISCOVERY_PORT = 49880
_DISCOVERY_INTERVAL = 30
_BROADCAST_ADDR = "255.255.255.255"

# HTTP sync
_SYNC_TIMEOUT = 5

# Merge limits
_MAX_TURNS_PER_PEER = 20

# Header used to authenticate sync requests between paired Zeno instances
SYNC_TOKEN_HEADER = "X-Zeno-Sync-Token"


# ---------------------------------------------------------------------------
# Instance identity
# ---------------------------------------------------------------------------

def instance_id() -> str:
    store = get_store()
    iid = store.get("sync.instance_id")
    if not iid:
        iid = str(uuid4())
        store.set("sync.instance_id", iid)
    return iid


def device_name() -> str:
    import platform
    store = get_store()
    name = store.get("sync.device_name")
    if not name:
        name = platform.node() or f"zeno-{instance_id()[:8]}"
        store.set("sync.device_name", name)
    return name


# ---------------------------------------------------------------------------
# Pairing token — shared secret required to push/pull sync data.
#
# Without this, any device that can reach the web port on the LAN (or
# beyond, if the port is forwarded) could silently pull conversation
# history and profile data, or push fabricated data that gets merged in.
# The token is generated once per install and must match on both sides;
# devices are "paired" by copying the token from one instance's
# `~/.zeno` data dir (or the `ZENO_SYNC_TOKEN` env var) to the other.
# ---------------------------------------------------------------------------

def sync_token() -> str:
    """Return this instance's pairing token, generating one on first use."""
    import os
    env_token = os.environ.get("ZENO_SYNC_TOKEN")
    if env_token:
        return env_token
    store = get_store()
    token = store.get("sync.pairing_token")
    if not token:
        token = secrets.token_hex(24)
        store.set("sync.pairing_token", token)
    return token


def verify_token(provided: Optional[str]) -> bool:
    """Constant-time check that `provided` matches this instance's token."""
    if not provided:
        return False
    return hmac.compare_digest(provided, sync_token())


# ---------------------------------------------------------------------------
# Peer discovery (UDP broadcast)
# ---------------------------------------------------------------------------

@dataclass
class Peer:
    instance_id: str
    host: str
    port: int
    name: str
    last_seen: float = 0.0
    version: str = "1.0"


class Discovery:
    """UDP broadcast-based peer discovery. Sends pings, collects pongs."""

    def __init__(self, web_port: int = 8080):
        self.web_port = web_port
        self.peers: dict[str, Peer] = {}
        self._running = False
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind(("", _DISCOVERY_PORT))
        except OSError:
            logger.warning("Sync discovery: port %d in use, binding any", _DISCOVERY_PORT)
            self._sock.bind(("", 0))
        self._sock.settimeout(1)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Sync discovery started on port %d", _DISCOVERY_PORT)

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()
        logger.info("Sync discovery stopped")

    def _loop(self):
        last_ping = 0.0
        while self._running:
            now = time.time()

            # Broadcast ping periodically
            if now - last_ping > _DISCOVERY_INTERVAL:
                self._send_ping()
                last_ping = now

            # Listen for pings / pongs
            try:
                data, addr = self._sock.recvfrom(2048)
                self._handle_message(data, addr)
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(1)

            # Expire stale peers (3 missed pings = 90s)
            stale = [iid for iid, p in self.peers.items() if now - p.last_seen > 90]
            for iid in stale:
                logger.debug("Sync peer expired: %s", self.peers[iid].name)
                del self.peers[iid]

    def _send_ping(self):
        if not self._sock:
            return
        msg = json.dumps({
            "type": "zeno-ping",
            "instance_id": instance_id(),
            "host": self._local_ip(),
            "port": self.web_port,
            "name": device_name(),
            "version": "1.0",
        })
        try:
            self._sock.sendto(msg.encode(), (_BROADCAST_ADDR, _DISCOVERY_PORT))
        except OSError:
            pass

    def _handle_message(self, data: bytes, addr: tuple):
        try:
            msg = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        msg_type = msg.get("type")
        peer_id = msg.get("instance_id")
        if not peer_id or peer_id == instance_id():
            return

        host = msg.get("host", addr[0])
        port = msg.get("port", 8080)

        if msg_type == "zeno-ping":
            # Respond with pong
            pong = json.dumps({
                "type": "zeno-pong",
                "instance_id": instance_id(),
                "host": self._local_ip(),
                "port": self.web_port,
                "name": device_name(),
                "version": "1.0",
            })
            try:
                self._sock.sendto(pong.encode(), (addr[0], _DISCOVERY_PORT))
            except OSError:
                pass

            # Record peer
            self.peers[peer_id] = Peer(
                instance_id=peer_id,
                host=host,
                port=port,
                name=msg.get("name", peer_id[:8]),
                last_seen=time.time(),
                version=msg.get("version", "1.0"),
            )

        elif msg_type == "zeno-pong":
            self.peers[peer_id] = Peer(
                instance_id=peer_id,
                host=host,
                port=port,
                name=msg.get("name", peer_id[:8]),
                last_seen=time.time(),
                version=msg.get("version", "1.0"),
            )

    def _local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except OSError:
            return "127.0.0.1"


# ---------------------------------------------------------------------------
# Context serialization / deserialization
# ---------------------------------------------------------------------------

def context_to_dict(ctx: Context) -> dict:
    return {
        "turns": [
            {
                "intent": t.intent,
                "response": t.response,
                "ts": getattr(t, "_ts", 0.0),
            }
            for t in ctx._turns
        ],
    }


def profile_to_dict() -> dict:
    p = load_profile()
    return {
        "name": p.name,
        "timezone": p.timezone,
        "language": p.calibration.language,
        "speech_rate": p.calibration.speech_rate,
    }


def timers_to_dict() -> list[dict]:
    now = time.time()
    result = []
    for meta in ReminderSkill._timer_meta:
        elapsed = now - meta["started"]
        remaining = max(0, meta["seconds"] - elapsed)
        if remaining > 0:
            result.append({
                "label": meta["label"],
                "seconds": meta["seconds"],
                "started": meta["started"],
                "is_alarm": meta["is_alarm"],
            })
    return result


# ---------------------------------------------------------------------------
# Context merger
# ---------------------------------------------------------------------------

class ContextMerger:
    """Merges remote context into local state."""

    @staticmethod
    def merge_turns(local: Context, remote_turns: list[dict]):
        """Merge remote turns into local context (newest wins, dedup by response)."""
        local_responses = {t.response for t in local._turns}
        merged = 0
        for turn in remote_turns:
            if turn.get("response") and turn["response"] not in local_responses:
                local._turns.append(TurnStub(
                    intent=turn.get("intent", "unknown"),
                    response=turn["response"],
                ))
                local_responses.add(turn["response"])
                merged += 1

        # Keep only last N
        if len(local._turns) > _MAX_TURNS_PER_PEER:
            local._turns = local._turns[-_MAX_TURNS_PER_PEER:]

        return merged

    @staticmethod
    def merge_profile(remote_profile: dict):
        """Last-writer-wins for profile fields."""
        store = get_store()
        if remote_profile.get("name"):
            store.set("profile.name", remote_profile["name"])
        if remote_profile.get("timezone"):
            store.set("profile.timezone", remote_profile["timezone"])
        if remote_profile.get("language"):
            store.set("cal.language", remote_profile["language"])

    @staticmethod
    def merge_timers(remote_timers: list[dict]):
        """Import timers from remote. Only import ones we don't already have."""
        existing_labels = {m["label"] for m in ReminderSkill._timer_meta}
        for t in remote_timers:
            label = t.get("label", "Timer")
            if label not in existing_labels:
                remaining = t["seconds"] - (time.time() - t["started"])
                if remaining > 0:
                    ReminderSkill.import_timer(
                        int(remaining),
                        label,
                        t.get("is_alarm", False),
                    )
                    existing_labels.add(label)


class TurnStub:
    """Minimal turn for synced conversations."""
    def __init__(self, intent="unknown", response=""):
        self.intent = intent
        self.entities = None
        self.response = response


# ---------------------------------------------------------------------------
# Sync runner — pushes/pulls context from peers periodically
# ---------------------------------------------------------------------------

class SyncClient:
    """Periodically syncs context with discovered peers."""

    def __init__(self, discovery: Discovery, context: Context, interval: int = 30):
        self.discovery = discovery
        self.context = context
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Sync client started (interval=%ds)", self.interval)

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(self.interval)
            for peer in list(self.discovery.peers.values()):
                try:
                    self._sync_with(peer)
                except Exception as e:
                    logger.debug("Sync to %s failed: %s", peer.name, e)

    def _sync_with(self, peer: Peer):
        """Push local context to peer, then pull theirs."""
        import urllib.request
        import urllib.error

        base = f"http://{peer.host}:{peer.port}"

        # Push local context
        push_data = json.dumps({
            "instance_id": instance_id(),
            "turns": context_to_dict(self.context).get("turns", []),
            "profile": profile_to_dict(),
            "timers": timers_to_dict(),
        }).encode()

        try:
            req = urllib.request.Request(
                f"{base}/api/sync/push",
                data=push_data,
                headers={
                    "Content-Type": "application/json",
                    SYNC_TOKEN_HEADER: sync_token(),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_SYNC_TIMEOUT) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.warning(
                    "Sync to %s rejected: pairing token mismatch. "
                    "Copy this device's token to the peer to pair them.",
                    peer.name,
                )
            return
        except urllib.error.URLError:
            return  # peer offline

        # Pull remote context
        try:
            req = urllib.request.Request(
                f"{base}/api/sync/pull",
                headers={SYNC_TOKEN_HEADER: sync_token()},
            )
            with urllib.request.urlopen(req, timeout=_SYNC_TIMEOUT) as resp:
                pull_data = json.loads(resp.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError):
            return

        # Merge remote data into local
        merger = ContextMerger()
        merger.merge_turns(self.context, pull_data.get("turns", []))
        merger.merge_profile(pull_data.get("profile", {}))
        merger.merge_timers(pull_data.get("timers", []))
