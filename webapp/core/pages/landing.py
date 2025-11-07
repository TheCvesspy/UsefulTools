from __future__ import annotations

import reflex as rx

from ..layout import app_shell


FEATURES = [
    {
        "title": "Distance Measurement",
        "description": "Measure distances and perimeters directly on uploaded images.",
        "href": "/distance-measurement",
    },
]


def _feature_tile(feature: dict[str, str]) -> rx.Component:
    return rx.link(
        rx.card(
            rx.vstack(
                rx.heading(feature["title"], size="md"),
                rx.text(feature["description"], color="gray.500", font_size="sm"),
                spacing="2",
                align_items="flex-start",
            ),
            height="100%",
            padding="6",
            variant="outline",
            _hover={"boxShadow": "lg", "transform": "translateY(-4px)"},
            transition="all 0.2s ease-in-out",
        ),
        href=feature["href"],
        width="100%",
    )


def landing() -> rx.Component:
    """Dashboard landing page with navigation tiles."""

    grid = rx.grid(
        *(_feature_tile(feature) for feature in FEATURES),
        template_columns="repeat(5, minmax(0, 1fr))",
        gap="6",
        width="100%",
    )

    return app_shell(
        rx.vstack(
            rx.heading("Useful Tools Dashboard", size="lg"),
            rx.text(
                "Choose a tool to get started. More features will appear here as they are added.",
                color="gray.500",
            ),
            grid,
            spacing="6",
            width="100%",
        )
    )
