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

    measurement_badge = rx.cond(
        MeasurementState.measurement_error,
        rx.badge(
            MeasurementState.measurement_error,
            color_scheme="red",
        ),
        rx.cond(
            MeasurementState.measuring,
            rx.hstack(
                rx.spinner(size="xs"),
                rx.text("Calculating…", font_size="sm"),
                spacing="2",
                align_items="center",
            ),
            rx.badge(MeasurementState.formatted_total, color_scheme="green"),
        ),
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
        measurement_badge,
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
