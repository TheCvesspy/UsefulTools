from __future__ import annotations

import reflex as rx

from ..state import MeasurementState


def status_bar() -> rx.Component:
    """Display measurement instructions and totals."""

    mode_icon = rx.cond(
        MeasurementState.mode == "scale",
        rx.icon("ruler"),
        rx.cond(
            MeasurementState.mode == "path",
            rx.icon("route"),
            rx.icon("info"),
        ),
    )

    theme_icon = rx.cond(
        MeasurementState.dark_mode,
        rx.icon("sun"),
        rx.icon("moon"),
    )

    return rx.hstack(
        rx.hstack(
            mode_icon,
            rx.text(
                MeasurementState.instructions,
                font_size="sm",
            ),
            spacing="2",
        ),
        rx.spacer(),
        rx.badge(MeasurementState.formatted_total, color_scheme="green"),
        rx.icon_button(
            icon=theme_icon,
            aria_label="Toggle theme",
            on_click=MeasurementState.toggle_theme,
            variant="ghost",
        ),
        spacing="4",
        width="100%",
        padding_y="2",
    )
