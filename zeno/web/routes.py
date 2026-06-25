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
            "notifications": pc.notifications,
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


# ---------- Responses ----------

@router.get("/api/responses")
async def list_response_keys():
    from zeno.response.engine import _PHRASES
    return {"keys": list(_PHRASES.keys())}


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
