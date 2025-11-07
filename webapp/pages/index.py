from __future__ import annotations

import reflex as rx

from ..components import measurement_canvas, status_bar, upload_panel
from ..state import MeasurementState


def index() -> rx.Component:
    """Main application page."""

    content = rx.vstack(
        rx.heading("Image Distance Measurement", size="lg"),
        rx.text(
            "Upload an image, define a scale, and trace paths to compute real-world distances.",
            color="gray.500",
        ),
        rx.responsive_grid(
            upload_panel(),
            measurement_canvas(),
            columns=[1, 1, 2],
            spacing="6",
            width="100%",
        ),
        status_bar(),
        spacing="6",
        width="100%",
    )

    return rx.box(
        rx.container(content, max_width="6xl"),
        width="100%",
        min_height="100vh",
        padding_y="8",
        background=rx.cond(
            MeasurementState.dark_mode,
            "gray.900",
            "gray.100",
        ),
        color=rx.cond(
            MeasurementState.dark_mode,
            "gray.100",
            "gray.800",
        ),
    )
