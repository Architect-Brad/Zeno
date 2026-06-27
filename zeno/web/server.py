"""
Zeno Web Server — FastAPI entry point.
Run with: python -m zeno.web.server [--host 0.0.0.0] [--port 8080] [--no-sync]
"""

import argparse
import uvicorn

from zeno.web.app import create_app

_app = None


def get_app(port: int = 8080, sync: bool = True):
    global _app
    if _app is None:
        _app = create_app(web_port=port, enable_sync=sync)
    return _app


def main():
    parser = argparse.ArgumentParser(description="Zeno Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8080, help="Port")
    parser.add_argument("--no-sync", action="store_true", help="Disable LAN sync")
    args = parser.parse_args()

    app = get_app(port=args.port, sync=not args.no_sync)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
