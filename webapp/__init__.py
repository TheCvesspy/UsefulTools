from __future__ import annotations

import reflex as rx

from .core.pages.landing import landing
from .distanceMeasurement.pages.tool import tool
from .distanceMeasurement.state import MeasurementState


app = rx.App(state=MeasurementState)
# Register the feature routes before the landing page so the explicit home
# route is the last page added. Reflex uses the most recently added page when
# multiple registrations target the same path, so adding the landing page last
# guarantees it is served from the root URL.
app.add_page(tool, route="/distance-measurement", title="Image Distance Measurement")
app.add_page(landing, route="/", title="Useful Tools")
