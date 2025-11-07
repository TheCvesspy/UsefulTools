from __future__ import annotations

import reflex as rx

from ..state import MeasurementState


def _scale_markers() -> rx.Component:
    return rx.foreach(
        MeasurementState.scale_values,
        lambda point, _: rx.el.circle(
            cx=point["x"],
            cy=point["y"],
            r=6,
            fill="var(--chakra-colors-red-400)",
            stroke="white",
            stroke_width="1",
        ),
    )


def _path_markers() -> rx.Component:
    return rx.foreach(
        MeasurementState.path_values,
        lambda point, _: rx.el.circle(
            cx=point["x"],
            cy=point["y"],
            r=5,
            fill="var(--chakra-colors-green-400)",
            stroke="white",
            stroke_width="1",
        ),
    )


def _overlay() -> rx.Component:
    return rx.el.svg(
        rx.cond(
            MeasurementState.scale_polyline != "",
            rx.el.polyline(
                points=MeasurementState.scale_polyline,
                stroke="var(--chakra-colors-red-400)",
                stroke_width="2",
                fill="none",
                stroke_dasharray="6 4",
            ),
        ),
        rx.cond(
            MeasurementState.path_polyline != "",
            rx.el.polyline(
                points=MeasurementState.path_polyline,
                stroke="var(--chakra-colors-green-400)",
                stroke_width="2",
                fill=rx.cond(
                    MeasurementState.path_closed,
                    "rgba(72, 187, 120, 0.25)",
                    "none",
                ),
            ),
        ),
        _scale_markers(),
        _path_markers(),
        width="100%",
        height="100%",
        pointer_events="none",
        style={"position": "absolute", "top": 0, "left": 0},
    )


def measurement_canvas() -> rx.Component:
    """Interactive area used to add and manage measurement points."""

    canvas_box = rx.box(
        rx.cond(
            MeasurementState.image_url,
            rx.box(
                rx.image(
                    src=MeasurementState.image_url,  # type: ignore[arg-type]
                    width="100%",
                    height="100%",
                    object_fit="contain",
                ),
                _overlay(),
                position="relative",
                width="100%",
                height="100%",
            ),
            rx.center(
                rx.text(
                    "Upload an image to start measuring.",
                    color="gray.500",
                )
            ),
        ),
        background="gray.900" if MeasurementState.dark_mode else "gray.50",
        border_radius="lg",
        overflow="hidden",
        height="100%",
        min_height="500px",
        width="100%",
        on_click=MeasurementState.handle_canvas_click(
            rx.event_arg("offsetX"),
            rx.event_arg("offsetY"),
        ),
        on_context_menu=rx.event_chain(
            rx.prevent_default(),
            MeasurementState.handle_canvas_click(
                rx.event_arg("offsetX"),
                rx.event_arg("offsetY"),
                "right",
            ),
        ),
    )

    controls = rx.hstack(
        rx.button(
            "Set Scale",
            on_click=MeasurementState.start_scale_mode,
            variant=rx.cond(
                MeasurementState.mode == "scale",
                "solid",
                "outline",
            ),
        ),
        rx.button(
            "Trace Path",
            on_click=MeasurementState.start_path_mode,
            variant=rx.cond(
                MeasurementState.mode == "path",
                "solid",
                "outline",
            ),
        ),
        rx.button(
            "Close Path",
            on_click=MeasurementState.close_path_loop,
            is_disabled=MeasurementState.path_closed,
        ),
        rx.button(
            "End Mode",
            on_click=MeasurementState.end_active_mode,
            variant="ghost",
        ),
        spacing="3",
        wrap="wrap",
    )

    return rx.vstack(
        controls,
        canvas_box,
        spacing="4",
        align_items="stretch",
        height="100%",
        width="100%",
    )
