from __future__ import annotations

import os

import reflex as rx


class UsefulToolsConfig(rx.Config):
    pass


config = UsefulToolsConfig(
    app_name="webapp",
    api_url=os.environ.get("BACKEND_API_URL", "http://localhost:8000"),
)

# Ensure the Reflex runtime knows how to reach the FastAPI backend when
# developing locally. This allows the front-end to issue relative requests
# (e.g. ``/upload``) which are automatically proxied to the FastAPI server.
rx.config.set(api_url=config.api_url)

# The front-end relies on ``httpx`` to communicate with the FastAPI backend.
# Register it as an extra dependency so ``reflex`` includes it during builds.
extra_deps = list(dict.fromkeys([*getattr(config, "extra_dependencies", []), "httpx>=0.25.0"]))
config.extra_dependencies = extra_deps
