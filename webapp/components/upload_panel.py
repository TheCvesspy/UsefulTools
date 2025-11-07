from __future__ import annotations

import reflex as rx

from ..state import MeasurementState


UNIT_CHOICES = [
    ("px", "Pixels"),
    ("mm", "Millimetres"),
    ("cm", "Centimetres"),
    ("km", "Kilometres"),
    ("mi", "Miles"),
]


def upload_panel() -> rx.Component:
    """Panel containing image upload and measurement controls."""

    uploader = rx.upload(  # type: ignore[no-untyped-call]
        rx.vstack(
            rx.icon("cloud-upload", font_size="2em"),
            rx.text("Drag and drop an image or click to browse."),
            spacing="1",
        ),
        multiple=False,
        accept="image/*",
        max_files=1,
        on_drop=MeasurementState.handle_upload,  # type: ignore[arg-type]
        width="100%",
        border="1px dashed",
        padding="1.5em",
        border_radius="md",
        disabled=MeasurementState.uploading,
    )

    unit_options = [choice[0] for choice in UNIT_CHOICES]

    setup_card = rx.card(
        rx.vstack(
            rx.heading("Setup", size="md"),
            uploader,
            rx.button(
                "Upload image",
                on_click=MeasurementState.handle_upload(uploader.files),  # type: ignore[arg-type]
                width="100%",
                is_loading=MeasurementState.uploading,
                loading_text="Uploading...",
                is_disabled=MeasurementState.uploading,
            ),
            rx.cond(
                MeasurementState.uploading,
                rx.hstack(
                    rx.spinner(size="sm"),
                    rx.text("Uploading image...", font_size="sm"),
                    spacing="2",
                    align_items="center",
                ),
            ),
            rx.cond(
                MeasurementState.upload_error,
                rx.alert(
                    rx.alert_icon(),
                    rx.alert_title("Upload failed"),
                    rx.alert_description(MeasurementState.upload_error),
                    status="error",
                ),
            ),
            rx.form_control(
                rx.form_label("Units"),
                rx.select(
                    unit_options,
                    placeholder="Select units",
                    value=MeasurementState.unit_name,
                    on_change=MeasurementState.set_unit_name,  # type: ignore[arg-type]
                    width="100%",
                ),
            ),
            rx.cond(
                MeasurementState.scale_label != "",
                rx.text(
                    MeasurementState.scale_label,
                    font_size="sm",
                    color="gray.500",
                ),
            ),
            rx.form_control(
                rx.form_label("Scale measurement"),
                rx.number_input(
                    placeholder="Real-world distance",
                    min_=0,
                    step=0.1,
                    on_change=MeasurementState.provide_scale_measurement,  # type: ignore[arg-type]
                ),
                rx.form_helper_text("Enter the real-world distance between the two scale points."),
            ),
            rx.form_control(
                rx.form_label("Units per pixel"),
                rx.number_input(
                    placeholder="Units per pixel",
                    min_=0,
                    step=0.01,
                    value=MeasurementState.units_per_pixel,
                    on_change=MeasurementState.update_units_per_pixel,  # type: ignore[arg-type]
                ),
                rx.form_helper_text("Adjust this value to fine-tune measurements."),
            ),
            rx.button(
                "Reset", on_click=MeasurementState.reset_measurements, variant="outline"
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
    )

    results_card = rx.card(
        rx.vstack(
            rx.heading("Results", size="md"),
            rx.cond(
                MeasurementState.measuring,
                rx.hstack(
                    rx.spinner(size="sm"),
                    rx.text("Calculating measurement...", font_size="sm"),
                    spacing="2",
                    align_items="center",
                ),
            ),
            rx.cond(
                MeasurementState.measurement_error,
                rx.alert(
                    rx.alert_icon(),
                    rx.alert_title("Measurement error"),
                    rx.alert_description(MeasurementState.measurement_error),
                    status="error",
                ),
            ),
            rx.form_control(
                rx.form_label("Measured distance"),
                rx.input(
                    value=MeasurementState.formatted_total,
                    is_read_only=True,
                    width="100%",
                ),
            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )

    return rx.responsive_grid(
        setup_card,
        results_card,
        columns=[1, 2, 2],
        spacing="4",
        width="100%",
    )
