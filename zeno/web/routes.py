"""
Zeno Web API Routes — REST endpoints for the web UI.
"""

import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Cookie, Request, Response
from fastapi.responses import JSONResponse

from zeno.core.context import Context
from zeno.core.loop import process_input
from zeno.platform import caps, detect_platform
from zeno.skills.reminders import ReminderSkill

router = APIRouter()

# --- Session storage ---
_sessions: dict[str, Context] = {}
_history: dict[str, list[dict]] = {}
_max_history = 200


def _get_or_create(session_id: str) -> Context:
    if session_id not in _sessions:
        _sessions[session_id] = Context()
    return _sessions[session_id]


def _ensure_session(sid: Optional[str] = None) -> tuple[str, Context]:
    session_id = sid or str(uuid4())
    ctx = _get_or_create(session_id)
    return session_id, ctx


# ---------- Health ----------

@router.get("/api/health")
async def health():
    pc = caps()
    return {
        "status": "ok",
        "platform": detect_platform(),
        "caps": {
            "tts": pc.tts,
            "stt": pc.stt,
            "notifications": pc.notification,
            "volume": pc.volume,
            "brightness": pc.brightness,
            "lock_screen": pc.lock_screen,
            "open_app": pc.open_app,
        },
        "version": "1.0.0",
    }


# ---------- Chat ----------

@router.post("/api/chat")
async def chat(
    request: Request,
    response: Response,
    x_session_id: Optional[str] = Cookie(None),
):
    session_id, ctx = _ensure_session(x_session_id)

    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"response": "", "intent": "", "confidence": 0.0, "session_id": session_id})

    result = process_input(text, ctx)

    _record_history(session_id, text, result)

    resp = JSONResponse({
        "response": result,
        "intent": ctx.last_intent() or "",
        "confidence": 0.0,
        "session_id": session_id,
    })
    resp.set_cookie(key="x_session_id", value=session_id, max_age=86400 * 30)
    return resp


# ---------- History ----------

@router.get("/api/history")
async def get_history(x_session_id: Optional[str] = Cookie(None)):
    sid = x_session_id or ""
    return {"history": _history.get(sid, [])}


@router.delete("/api/history")
async def clear_history(x_session_id: Optional[str] = Cookie(None)):
    sid = x_session_id or ""
    _history.pop(sid, None)
    _sessions.pop(sid, None)
    return {"status": "cleared"}


# ---------- Timers / Alarms ----------

@router.get("/api/timers")
async def list_timers():
    timers = []
    now = time.time()
    to_remove = []
    for i, meta in enumerate(ReminderSkill._timer_meta):
        elapsed = now - meta["started"]
        remaining = max(0, meta["seconds"] - elapsed)
        alive = i < len(ReminderSkill._active_timers) and ReminderSkill._active_timers[i].is_alive()
        if not alive and remaining <= 0:
            to_remove.append(i)
            continue
        timers.append({
            "id": i,
            "label": meta["label"],
            "remaining": round(remaining),
            "total": meta["seconds"],
            "is_alarm": meta["is_alarm"],
        })
    for i in reversed(to_remove):
        if i < len(ReminderSkill._timer_meta):
            ReminderSkill._timer_meta.pop(i)
        if i < len(ReminderSkill._active_timers):
            ReminderSkill._active_timers.pop(i)
    return {"timers": timers}


@router.post("/api/timers/{timer_id}/cancel")
async def cancel_timer(timer_id: int):
    if timer_id < len(ReminderSkill._active_timers):
        t = ReminderSkill._active_timers[timer_id]
        t.cancel()
        if timer_id < len(ReminderSkill._timer_meta):
            ReminderSkill._timer_meta.pop(timer_id)
        return {"status": "cancelled"}
    return JSONResponse({"error": "not found"}, status_code=404)


# ---------- Responses ----------

@router.get("/api/responses")
async def list_response_keys():
    from zeno.response.engine import _PHRASES
    return {"keys": list(_PHRASES.keys())}


# ---------- Sync ----------

from zeno.core.sync import (
    instance_id, context_to_dict, profile_to_dict, timers_to_dict,
    ContextMerger, verify_token, SYNC_TOKEN_HEADER,
)


def _check_sync_auth(request: Request) -> Optional[JSONResponse]:
    """Return a 401 response if the sync pairing token is missing/wrong."""
    provided = request.headers.get(SYNC_TOKEN_HEADER)
    if not verify_token(provided):
        return JSONResponse(
            {"error": "invalid or missing sync pairing token"},
            status_code=401,
        )
    return None


@router.post("/api/sync/push")
async def sync_push(request: Request):
    unauthorized = _check_sync_auth(request)
    if unauthorized:
        return unauthorized

    body = await request.json()
    remote_iid = body.get("instance_id", "unknown")
    turns = body.get("turns", [])
    profile = body.get("profile", {})
    timers = body.get("timers", [])

    # Merge into default session
    _, ctx = _ensure_session(None)
    merger = ContextMerger()
    n = merger.merge_turns(ctx, turns)
    merger.merge_profile(profile)
    merger.merge_timers(timers)

    return {"status": "ok", "merged": n, "peer": remote_iid}


@router.get("/api/sync/pull")
async def sync_pull(request: Request):
    unauthorized = _check_sync_auth(request)
    if unauthorized:
        return unauthorized

    _, ctx = _ensure_session(None)
    return {
        "instance_id": instance_id(),
        "turns": context_to_dict(ctx).get("turns", []),
        "profile": profile_to_dict(),
        "timers": timers_to_dict(),
    }


@router.get("/api/sync/peers")
async def sync_peers(request: Request):
    unauthorized = _check_sync_auth(request)
    if unauthorized:
        return unauthorized

    from zeno.web.app import _discovery
    if _discovery is None:
        return {"peers": []}
    return {
        "peers": [
            {
                "id": p.instance_id,
                "name": p.name,
                "host": p.host,
                "port": p.port,
                "last_seen": p.last_seen,
            }
            for p in _discovery.peers.values()
        ]
    }


# ---------- Profile ----------

from zeno.core.profile import load_profile, save_location, save_owm_key, save_units, save_name, save_timezone


@router.get("/api/profile")
async def get_profile():
    p = load_profile()
    return {
        "name": p.name or "",
        "timezone": p.timezone or "",
        "location": p.location or "",
        "owm_api_key": "****" if p.owm_api_key else "",
        "units": p.units,
    }


@router.post("/api/profile")
async def update_profile(request: Request):
    body = await request.json()
    for key, saver in [
        ("name", save_name),
        ("timezone", save_timezone),
        ("location", save_location),
        ("owm_api_key", lambda v: save_owm_key(v)),
        ("units", save_units),
    ]:
        val = body.get(key)
        if val is not None:
            saver(val)
    return {"status": "ok"}


# ---------- Contacts ----------

from zeno.core.contact_store import load_contacts, save_contacts, find_contact, get_contact_names


@router.get("/api/contacts")
async def list_contacts():
    return {"contacts": load_contacts()}


@router.post("/api/contacts")
async def add_or_update_contact(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    contacts = load_contacts()
    contacts[name] = {
        "phone": body.get("phone", ""),
        "email": body.get("email", ""),
    }
    save_contacts(contacts)
    return {"status": "ok", "name": name}


@router.delete("/api/contacts/{contact_name}")
async def delete_contact(contact_name: str):
    contacts = load_contacts()
    if contact_name in contacts:
        del contacts[contact_name]
        save_contacts(contacts)
    return {"status": "deleted"}


# ---------- Internal ----------

def _record_history(session_id: str, text: str, response: str):
    entries = _history.setdefault(session_id, [])
    entries.append({
        "user": text,
        "zeno": response,
        "ts": time.time(),
    })
    if len(entries) > _max_history:
        _history[session_id] = entries[-_max_history:]
