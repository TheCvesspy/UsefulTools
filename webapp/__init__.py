from __future__ import annotations

import reflex as rx

from .core import AppState
from .core.pages.landing import landing
from .distanceMeasurement.pages.tool import tool
from .distanceMeasurement.state import MeasurementState


def _create_app() -> rx.App:
    """Instantiate the Reflex app with shared and feature states."""

    base_app = rx.App(state=AppState)
    add_state = getattr(base_app, "add_state", None)
    if callable(add_state):
        add_state(MeasurementState)
        return base_app

    fallback_app = rx.App(state=MeasurementState)
    return fallback_app


app = _create_app()

app.add_page(landing, route="/", title="Useful Tools")
app.add_page(tool, route="/distance-measurement", title="Image Distance Measurement")
