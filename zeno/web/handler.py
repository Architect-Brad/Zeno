"""
Zeno WebSocket handler — real-time interaction endpoint.
Supports text messages now; audio streaming ready for future expansion.
"""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from zeno.core.context import Context
from zeno.core.loop import process_input

router = APIRouter()

_ws_sessions: dict[str, Context] = {}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())
    ctx = Context()
    _ws_sessions[session_id] = ctx

    try:
        while True:
            data = await ws.receive()

            if data.get("type") == "websocket.receive":
                raw = data.get("text") or data.get("bytes")

                # Binary audio chunk — acknowledge but can't transcribe server-side yet
                if isinstance(raw, bytes):
                    await ws.send_json({"type": "ack", "size": len(raw)})
                    continue

                # Text messages
                if isinstance(raw, str):
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    msg_type = msg.get("type", "")

                    if msg_type == "text":
                        text = msg.get("text", "").strip()
                        if text:
                            response = process_input(text, ctx)
                            await ws.send_json({"type": "response", "text": response})

                    elif msg_type == "end":
                        # Audio stream ended — no server-side STT yet
                        await ws.send_json({
                            "type": "info",
                            "text": "Audio received. Server-side transcription not yet available. Please use text input or your browser's voice recognition.",
                        })

            elif data.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    finally:
        _ws_sessions.pop(session_id, None)
