"""
Zeno FastAPI application factory.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from zeno.web.routes import router as api_router
from zeno.web.handler import router as ws_router
from zeno.core.sync import Discovery, SyncClient
from zeno.core.context import Context

# Module-level singleton for web routes
_discovery: Discovery | None = None

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app(web_port: int = 8080, enable_sync: bool = True) -> FastAPI:
    app = FastAPI(title="Zeno", version="1.0.0")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(api_router)
    app.include_router(ws_router)

    # --- Sync startup ---
    if enable_sync:
        _start_sync(web_port)

    @app.get("/")
    async def index():
        from fastapi.responses import FileResponse
        index_path = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index_path)

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

    # Start sync client with a shared context
    ctx = Context()
    client = SyncClient(d, ctx, interval=30)
    client.start()
