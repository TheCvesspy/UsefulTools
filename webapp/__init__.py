from __future__ import annotations

import reflex as rx

from .core.pages.landing import landing
from .distanceMeasurement.pages.tool import tool
from .distanceMeasurement.state import MeasurementState


app = rx.App(state=MeasurementState)
app.add_page(landing, route="/", title="Useful Tools")
app.add_page(tool, route="/distance-measurement", title="Image Distance Measurement")
