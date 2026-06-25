"""
Zeno Web Server — FastAPI entry point.
Run with: python -m zeno.web.server [--host 0.0.0.0] [--port 8080]
"""

import argparse
import uvicorn

from zeno.web.app import create_app

app = create_app()

def main():
    parser = argparse.ArgumentParser(description="Zeno Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8080, help="Port")
    args = parser.parse_args()

    uvicorn.run(
        "zeno.web.server:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )

if __name__ == "__main__":
    main()
