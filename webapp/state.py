from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional

import reflex as rx


class Point(rx.Base):
    """Serializable point representation used across the UI."""

    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


class MeasurementState(rx.State):
    """Global application state mirroring the PyQt behaviour."""

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

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Save the uploaded image and reset measurements."""

        if not files:
            return
        upload = files[0]
        data = await upload.read()
        if not data:
            return
        upload_dir = rx.get_upload_dir()
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / Path(upload.filename).name
        file_path.write_bytes(data)
        self.image_url = f"/upload/{file_path.name}"
        self.reset_measurements()
        self.instructions = "Select 'Set Scale' or 'Trace Path' to begin measuring."

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
            self._add_scale_point(x, y)
        elif self.mode in {"path", "idle"}:
            if button == "left":
                self._add_path_point(x, y)
            elif button == "right":
                self.remove_last_path_point()

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
        self._update_total_distance()
        if len(self.path_points) == 1:
            self.instructions = "Add more points to trace a path."
        else:
            self.instructions = "Continue adding points or close the loop."

    def remove_last_path_point(self):
        if self.path_points:
            points = list(self.path_points[:-1])
            self.path_points = points
            self.path_closed = False
            self._update_total_distance()
            if not self.path_points:
                self.instructions = "Path cleared. Add a new point to start."

    def close_path_loop(self):
        if len(self.path_points) >= 3 and not self.path_closed:
            self.path_closed = True
            self._update_total_distance(close_loop=True)
            self.instructions = "Path closed. Add points to start a new path."

    def reset_measurements(self):
        self.mode = "idle"
        self.scale_points = []
        self.path_points = []
        self.path_closed = False
        self.units_per_pixel = 1.0
        self.total_distance = 0.0
        self.instructions = "Select 'Set Scale' or 'Trace Path' to begin measuring."

    def set_unit_name(self, unit: str):
        self.unit_name = unit

    def update_units_per_pixel(self, value: str):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return
        self.set_units_per_pixel(parsed)

    def provide_scale_measurement(self, value: str):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return
        self.complete_scale_mode(parsed)

    def set_units_per_pixel(self, value: float):
        if value > 0:
            self.units_per_pixel = value
            self._update_total_distance()

    def _update_total_distance(self, close_loop: bool = False):
        distance = 0.0
        if len(self.path_points) >= 2:
            for start, end in zip(self.path_points, self.path_points[1:]):
                distance += self._distance(start, end)
            if close_loop or self.path_closed:
                distance += self._distance(self.path_points[-1], self.path_points[0])
        self.total_distance = distance * self.units_per_pixel

    @staticmethod
    def _distance(a: Point, b: Point) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    @rx.var
    def formatted_total(self) -> str:
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
