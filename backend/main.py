"""ASGI entry point for launching the FastAPI application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def _ensure_project_root_on_path() -> None:
    """Add the project root directory to ``sys.path`` if needed."""

    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


def main() -> None:
    """Run the API using uvicorn."""

    _ensure_project_root_on_path()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("backend.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
