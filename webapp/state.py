from __future__ import annotations

import math
from typing import Any, List, Optional

import httpx
import reflex as rx

from rxconfig import config as app_config


class Point(rx.Base):
    """Serializable point representation used across the UI."""

    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


def _normalise_base_url(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.rstrip("/")


def _normalise_image_url(base_url: str, url: str) -> str:
    if not url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if not base_url:
        return url
    if not url.startswith("/"):
        url = f"/{url}"
    return f"{base_url}{url}"


def _extract_error_message(response: Optional[httpx.Response], fallback: str) -> str:
    if response is None:
        return fallback
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                msg = first.get("msg")
                if isinstance(msg, str):
                    return msg
        message = payload.get("message")
        if isinstance(message, str):
            return message
    return f"{response.status_code} {response.reason_phrase}"


class MeasurementState(rx.State):
    """Global application state mirroring the PyQt behaviour."""

    api_base_url: str = _normalise_base_url(getattr(app_config, "api_url", ""))
    image_url: Optional[str] = None
    mode: str = "idle"
    unit_name: str = "px"
    units_per_pixel: float = 1.0
    total_distance: float = 0.0
    dark_mode: bool = False
    scale_points: List[Point] = []
    path_points: List[Point] = []
    path_closed: bool = False
    instructions: str = "Load an image to begin."
    uploading: bool = False
    measuring: bool = False
    upload_error: Optional[str] = None
    measurement_error: Optional[str] = None
    last_uploaded_filename: Optional[str] = None
    measurement_result: Optional[dict[str, Any]] = None

    def _api_endpoint(self, path: str) -> str:
        if not self.api_base_url:
            raise ValueError("API base URL is not configured.")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.api_base_url}{path}"

    def _start_upload(self, filename: str):
        self.uploading = True
        self.upload_error = None
        self.last_uploaded_filename = filename

    def _complete_upload(self, image_url: str, filename: str):
        self.uploading = False
        self.upload_error = None
        self.last_uploaded_filename = filename
        self.image_url = image_url
        self.reset_measurements()
        self.instructions = "Select 'Set Scale' or 'Trace Path' to begin measuring."

    def _fail_upload(self, message: str):
        self.uploading = False
        self.upload_error = message

    def _clear_measurement(self):
        self.measurement_result = None
        self.total_distance = 0.0
        self.measuring = False
        self.measurement_error = None

    def _start_measurement(self):
        self.measuring = True
        self.measurement_error = None

    def _finish_measurement_success(self, measurement: dict[str, Any]):
        self.measuring = False
        self.measurement_error = None
        self.measurement_result = measurement
        total_units = measurement.get("total_units")
        if isinstance(total_units, (int, float)):
            self.total_distance = float(total_units)
        else:
            total_pixels = measurement.get("total_pixels")
            if isinstance(total_pixels, (int, float)):
                self.total_distance = float(total_pixels)
            else:
                self.total_distance = 0.0

    def _finish_measurement_failure(self, message: str):
        self.measuring = False
        self.measurement_error = message
        self.measurement_result = None
        self.total_distance = 0.0

    def _schedule_measurement(self):
        if len(self.path_points) >= 2:
            return MeasurementState.measure_path()
        self._clear_measurement()
        return None

    @rx.background
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Upload an image through the backend API and reset measurements."""

        if not files:
            return
        upload = files[0]
        data = await upload.read()
        if not data:
            yield MeasurementState._fail_upload("Unable to read the selected file.")
            return
        filename = upload.filename or "upload"
        yield MeasurementState._start_upload(filename)

        endpoint = self._api_endpoint("/upload")
        response: Optional[httpx.Response] = None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    files={
                        "file": (
                            filename,
                            data,
                            upload.content_type or "application/octet-stream",
                        )
                    },
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors
            message = _extract_error_message(exc.response, "Failed to upload image.")
            yield MeasurementState._fail_upload(message)
            return
        except httpx.RequestError as exc:  # pragma: no cover - network errors
            yield MeasurementState._fail_upload(str(exc))
            return

        try:
            payload = response.json()
        except ValueError:  # pragma: no cover - defensive
            yield MeasurementState._fail_upload(
                "Upload succeeded but the server returned invalid data."
            )
            return

        image_url = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(image_url, str) or not image_url:
            yield MeasurementState._fail_upload(
                "Upload succeeded but no image URL was provided."
            )
            return

        resolved_url = _normalise_image_url(self.api_base_url, image_url)
        yield MeasurementState._complete_upload(resolved_url, filename)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode

    def start_scale_mode(self):
        self.mode = "scale"
        self.scale_points = []
        self.instructions = "Click two points to define the scale."

    def complete_scale_mode(self, real_world_distance: float):
        if len(self.scale_points) == 2 and real_world_distance > 0:
            pixel_distance = self._distance(self.scale_points[0], self.scale_points[1])
            if pixel_distance > 0:
                self.units_per_pixel = real_world_distance / pixel_distance
                self.instructions = (
                    "Scale set. Switch to path tracing to measure distances."
                )
        self.mode = "idle"
        return self._schedule_measurement()

    def start_path_mode(self):
        self.mode = "path"
        if not self.path_points:
            self.instructions = (
                "Click on the image to create a path. Right click to remove the last point."
            )

    def end_active_mode(self):
        self.mode = "idle"
        if self.path_points:
            self.instructions = (
                "Path active. Continue clicking to add points or close the loop."
            )
        else:
            self.instructions = "Select a mode to begin measuring."

    def handle_canvas_click(self, x: float, y: float, button: str = "left"):
        if self.mode == "scale" and button == "left":
            return self._add_scale_point(x, y)
        elif self.mode in {"path", "idle"}:
            if button == "left":
                return self._add_path_point(x, y)
            elif button == "right":
                return self.remove_last_path_point()

    def _add_scale_point(self, x: float, y: float):
        points = [] if len(self.scale_points) >= 2 else list(self.scale_points)
        points.append(Point(x=x, y=y))
        self.scale_points = points
        if len(self.scale_points) == 2:
            self.instructions = "Enter the real-world distance for the scale."

    def _add_path_point(self, x: float, y: float):
        if self.mode == "idle":
            self.start_path_mode()
        if self.path_closed:
            self.path_closed = False
            self.path_points = []
        points = list(self.path_points)
        points.append(Point(x=x, y=y))
        self.path_points = points
        if len(self.path_points) == 1:
            self.instructions = "Add more points to trace a path."
        else:
            self.instructions = "Continue adding points or close the loop."
        return self._schedule_measurement()

    def remove_last_path_point(self):
        if self.path_points:
            points = list(self.path_points[:-1])
            self.path_points = points
            self.path_closed = False
            if not self.path_points:
                self.instructions = "Path cleared. Add a new point to start."
        return self._schedule_measurement()

    def close_path_loop(self):
        if len(self.path_points) >= 3 and not self.path_closed:
            self.path_closed = True
            self.instructions = "Path closed. Add points to start a new path."
            return self._schedule_measurement()
        return None

    def reset_measurements(self):
        self.mode = "idle"
        self.scale_points = []
        self.path_points = []
        self.path_closed = False
        self.units_per_pixel = 1.0
        self.total_distance = 0.0
        self.instructions = "Select 'Set Scale' or 'Trace Path' to begin measuring."
        self._clear_measurement()

    def set_unit_name(self, unit: str):
        self.unit_name = unit
        return self._schedule_measurement()

    def update_units_per_pixel(self, value: str):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return
        return self.set_units_per_pixel(parsed)

    def provide_scale_measurement(self, value: str):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return
        return self.complete_scale_mode(parsed)

    def set_units_per_pixel(self, value: float):
        if value <= 0:
            self.measurement_error = "Units per pixel must be greater than zero."
            self.measuring = False
            return None
        self.units_per_pixel = value
        return self._schedule_measurement()

    @staticmethod
    def _distance(a: Point, b: Point) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    @rx.var
    def formatted_total(self) -> str:
        if self.measurement_result:
            measurement = self.measurement_result
            display_unit = (
                measurement.get("display_unit_name")
                or measurement.get("unit_name")
                or self.unit_name
            )
            total_units = measurement.get("total_units")
            if isinstance(total_units, (int, float)):
                return f"Distance: {float(total_units):.2f} {display_unit}"
            total_pixels = measurement.get("total_pixels")
            if isinstance(total_pixels, (int, float)):
                return f"Distance: {float(total_pixels):.2f} px"
        return f"Distance: {self.total_distance:.2f} {self.unit_name}"

    @rx.var
    def scale_length(self) -> float:
        if len(self.scale_points) == 2:
            return self._distance(self.scale_points[0], self.scale_points[1])
        return 0.0

    @rx.var
    def scale_label(self) -> str:
        if self.scale_length > 0:
            return f"Scale length: {self.scale_length:.2f} px"
        return ""

    @rx.var
    def scale_values(self) -> list[dict[str, float]]:
        return [
            {"x": point.x, "y": point.y}
            for point in self.scale_points
        ]

    @rx.var
    def path_values(self) -> list[dict[str, float]]:
        return [
            {"x": point.x, "y": point.y}
            for point in self.path_points
        ]

    @rx.var
    def path_polyline(self) -> str:
        if not self.path_points:
            return ""
        coords = " ".join(f"{point.x},{point.y}" for point in self.path_points)
        if self.path_closed and len(self.path_points) > 2:
            first = self.path_points[0]
            coords = f"{coords} {first.x},{first.y}"
        return coords

    @rx.var
    def scale_polyline(self) -> str:
        if len(self.scale_points) == 2:
            return " ".join(f"{point.x},{point.y}" for point in self.scale_points)
        return ""

    @rx.background
    async def measure_path(self):
        if len(self.path_points) < 2:
            yield MeasurementState._clear_measurement()
            return

        try:
            endpoint = self._api_endpoint("/measure")
        except ValueError as exc:  # pragma: no cover - configuration errors
            yield MeasurementState._finish_measurement_failure(str(exc))
            return

        units_per_pixel = self.units_per_pixel if self.units_per_pixel > 0 else None
        if self.unit_name == "px":
            units_per_pixel = 1.0

        scale_payload: dict[str, Any] = {"unit_name": self.unit_name}
        if units_per_pixel is not None:
            scale_payload["units_per_pixel"] = units_per_pixel

        payload = {
            "points": [{"x": point.x, "y": point.y} for point in self.path_points],
            "closed": self.path_closed,
            "scale": scale_payload,
        }

        yield MeasurementState._start_measurement()

        response: Optional[httpx.Response] = None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(endpoint, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors
            message = _extract_error_message(exc.response, "Measurement request failed.")
            yield MeasurementState._finish_measurement_failure(message)
            return
        except httpx.RequestError as exc:  # pragma: no cover - network errors
            yield MeasurementState._finish_measurement_failure(str(exc))
            return

        try:
            data = response.json()
        except ValueError:  # pragma: no cover - defensive
            yield MeasurementState._finish_measurement_failure(
                "Measurement succeeded but returned invalid data."
            )
            return

        measurement = data.get("measurement") if isinstance(data, dict) else None
        if not isinstance(measurement, dict):
            yield MeasurementState._finish_measurement_failure(
                "Measurement succeeded but no results were provided."
            )
            return

        yield MeasurementState._finish_measurement_success(measurement)
