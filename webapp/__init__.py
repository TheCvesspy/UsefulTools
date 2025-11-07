from __future__ import annotations

import reflex as rx

from .core import AppState
from .core.pages import landing
from .distanceMeasurement.pages import distance_measurement
from .distanceMeasurement.state import MeasurementState


app = rx.App(state=AppState)
app.add_page(landing, route="/")
app.add_page(distance_measurement, route="/distance-measurement", state=MeasurementState)
