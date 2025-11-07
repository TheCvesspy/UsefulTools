from __future__ import annotations

import reflex as rx

from .pages.index import index
from .state import MeasurementState


app = rx.App(state=MeasurementState)
app.add_page(index, route="/")
