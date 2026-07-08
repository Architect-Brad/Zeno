"""
Zeno FastAPI application factory.
"""

import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from zeno.web.routes import router as api_router
from zeno.web.handler import router as ws_router
from zeno.core.sync import Discovery, SyncClient, sync_token
from zeno.core.context import Context

# Module-level singleton for web routes
_discovery: Discovery | None = None

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# --- Simple per-IP rate limiting for the REST API ---
# This is a single-process, in-memory limiter — good enough for a
# LAN-facing personal assistant, not meant to withstand a distributed
# attack. It exists to stop one misbehaving client (buggy script,
# accidental loop, or a stranger poking the port) from hammering the
# NLU pipeline or SQLite store.
_RATE_LIMIT_REQUESTS = 120     # requests
_RATE_LIMIT_WINDOW = 60.0      # seconds
_request_log: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    log = _request_log[ip]
    while log and now - log[0] > _RATE_LIMIT_WINDOW:
        log.popleft()
    if len(log) >= _RATE_LIMIT_REQUESTS:
        return True
    log.append(now)
    return False


def create_app(web_port: int = 8080, enable_sync: bool = True) -> FastAPI:
    app = FastAPI(title="Zeno", version="1.0.0")

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            ip = _client_ip(request)
            if _rate_limited(ip):
                return JSONResponse(
                    {"error": "rate limit exceeded, slow down"},
                    status_code=429,
                )
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(api_router)
    app.include_router(ws_router)

    # --- Sync startup ---
    if enable_sync:
        _start_sync(web_port)

    @app.get("/")
    async def index():
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/chat")
    async def chat():
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(STATIC_DIR, "chat.html"))

    @app.on_event("shutdown")
    async def shutdown():
        if _discovery:
            _discovery.stop()

    return app


def _start_sync(web_port: int):
    global _discovery
    d = Discovery(web_port=web_port)
    d.start()
    _discovery = d

    # Print the pairing token once per process start so the user can
    # copy it to a second device (or set ZENO_SYNC_TOKEN there) to pair.
    print(
        f"[zeno] LAN sync enabled. Pairing token for this device: {sync_token()}\n"
        f"[zeno] To pair another device, set ZENO_SYNC_TOKEN={sync_token()} "
        f"in its environment before starting it."
    )

    # Start sync client with a shared context
    ctx = Context()
    client = SyncClient(d, ctx, interval=30)
    client.start()
