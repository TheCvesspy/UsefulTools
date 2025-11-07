from __future__ import annotations

import reflex as rx

from ..state import AppState


def app_header() -> rx.Component:
    """Render the persistent application header."""

    theme_icon = rx.cond(AppState.dark_mode, rx.icon("sun"), rx.icon("moon"))

    return rx.box(
        rx.container(
            rx.hstack(
                rx.button(
                    "Home",
                    left_icon=rx.icon("home"),
                    variant="ghost",
                    on_click=rx.redirect("/"),
                ),
                rx.heading("Useful Tools", size="md"),
                rx.spacer(),
                rx.icon_button(
                    icon=theme_icon,
                    aria_label="Toggle theme",
                    on_click=AppState.toggle_theme,
                    variant="ghost",
                ),
                spacing="4",
                align_items="center",
                width="100%",
            ),
            max_width="6xl",
        ),
        width="100%",
        padding_y="4",
        border_bottom="1px solid",
        border_color=rx.cond(
            AppState.dark_mode,
            "gray.700",
            "gray.200",
        ),
        background=rx.cond(
            AppState.dark_mode,
            "gray.900",
            "white",
        ),
        position="sticky",
        top="0",
        z_index="1000",
    )
