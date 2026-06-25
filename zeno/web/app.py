"""
Zeno FastAPI application factory.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from zeno.web.routes import router as api_router
from zeno.web.handler import router as ws_router


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> FastAPI:
    app = FastAPI(title="Zeno", version="1.0.0")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/")
    async def index():
        from fastapi.responses import FileResponse
        index_path = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index_path)

    return app
