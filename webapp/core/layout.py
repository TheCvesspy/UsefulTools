from __future__ import annotations

import reflex as rx

from .components.header import app_header
from .state import AppState


def app_shell(*children: rx.Component, max_width: str = "6xl") -> rx.Component:
    """Wrap feature content with the shared application chrome."""

    return rx.box(
        app_header(),
        rx.box(
            rx.container(
                *children,
                max_width=max_width,
                width="100%",
                padding_y="8",
            ),
            width="100%",
            flex="1",
        ),
        width="100%",
        min_height="100vh",
        background=rx.cond(
            AppState.dark_mode,
            "gray.900",
            "gray.100",
        ),
        color=rx.cond(
            AppState.dark_mode,
            "gray.100",
            "gray.800",
        ),
        display="flex",
        flex_direction="column",
    )
