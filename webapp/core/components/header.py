from __future__ import annotations

import reflex as rx

from ..state import AppState


def app_header() -> rx.Component:
    """Application header containing the home navigation button."""

    home_button = rx.link(
        rx.button(
            rx.hstack(
                rx.icon("home"),
                rx.text("Home", font_weight="medium"),
                spacing="2",
                align_items="center",
            ),
            variant="solid",
            color_scheme="gray",
        ),
        href="/",
        text_decoration="none",
        _hover={"text_decoration": "none"},
    )

    return rx.hstack(
        home_button,
        rx.heading("Useful Tools", size="md"),
        rx.spacer(),
        width="100%",
        padding_x="6",
        padding_y="4",
        align_items="center",
        background=rx.cond(
            AppState.dark_mode,
            "gray.800",
            "gray.900",
        ),
        color=rx.cond(
            AppState.dark_mode,
            "gray.100",
            "white",
        ),
        box_shadow="sm",
    )
