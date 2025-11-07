from __future__ import annotations

import reflex as rx

from .. import app_shell


_FEATURES: list[dict[str, str]] = [
    {
        "name": "Image Distance Measurement",
        "description": "Measure real-world distances by tracing paths on uploaded images.",
        "href": "/distance-measurement",
        "icon": "ruler",
    },
]


def _feature_tile(feature: dict[str, str]) -> rx.Component:
    """Render a single feature tile."""

    return rx.link(
        rx.card(
            rx.vstack(
                rx.icon(feature.get("icon", "box"), font_size="2xl"),
                rx.heading(feature["name"], size="sm", text_align="left"),
                rx.text(
                    feature["description"],
                    font_size="sm",
                    color="gray.500",
                    text_align="left",
                ),
                spacing="3",
                align_items="flex-start",
            ),
            height="100%",
            padding="4",
            width="100%",
        ),
        href=feature["href"],
        text_decoration="none",
        _hover={"text_decoration": "none"},
    )


def landing() -> rx.Component:
    """Landing dashboard linking to each available feature."""

    grid = rx.grid(
        *[_feature_tile(feature) for feature in _FEATURES],
        template_columns="repeat(5, minmax(0, 1fr))",
        gap="5",
        width="100%",
        align_items="stretch",
        justify_items="stretch",
    )

    return app_shell(
        rx.vstack(
            rx.heading("Useful Tools Dashboard", size="lg", text_align="left"),
            rx.text(
                "Choose a tool to get started.",
                color="gray.500",
                text_align="left",
            ),
            grid,
            spacing="6",
            width="100%",
            align_items="flex-start",
        ),
        max_width="6xl",
    )
