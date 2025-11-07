from __future__ import annotations

import reflex as rx

from .components.header import app_header
from .state import AppState


def app_shell(*children: rx.Component, max_width: str | None = "6xl") -> rx.Component:
    """Wrap pages in the common application shell."""

    content = rx.box(
        *children,
        width="100%",
        padding="6",
    )

    if max_width is not None:
        content = rx.container(content, max_width=max_width)

    return rx.box(
        app_header(),
        rx.box(
            content,
            width="100%",
            padding_y="6",
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
    )
