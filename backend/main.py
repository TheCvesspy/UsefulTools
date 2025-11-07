"""ASGI entry point for launching the FastAPI application."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Run the API using uvicorn."""

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("backend.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
