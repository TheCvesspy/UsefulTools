from __future__ import annotations

import reflex as rx

from ...core.layout import app_shell
from ..components import measurement_canvas, status_bar, upload_panel


def distance_measurement() -> rx.Component:
    """Distance measurement feature page."""

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

    return app_shell(content)
