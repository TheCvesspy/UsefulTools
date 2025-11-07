"""Geometry utilities shared by the desktop app and API."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple, Union

# Public unit definitions so the UI and API can stay in sync.
UNIT_CHOICES: Sequence[Tuple[str, str]] = (
    ("px", "px"),
    ("mm", "mm"),
    ("cm", "cm"),
    ("km", "km"),
    ("mi", "miles (mi)"),
)

_UNIT_DISPLAY_LOOKUP: Dict[str, str] = {value: label for value, label in UNIT_CHOICES}

PointLike = Union[Sequence[float], Mapping[str, float], object]


def _extract_xy(point: PointLike) -> Tuple[float, float]:
    """Return a numeric (x, y) pair from supported *point* inputs."""

    if hasattr(point, "x") and hasattr(point, "y"):
        x_attr = getattr(point, "x")
        y_attr = getattr(point, "y")
        x_val = x_attr() if callable(x_attr) else x_attr
        y_val = y_attr() if callable(y_attr) else y_attr
        return float(x_val), float(y_val)
    if isinstance(point, Mapping):
        return float(point["x"]), float(point["y"])
    if isinstance(point, Sequence) and not isinstance(point, (str, bytes, bytearray)):
        if len(point) != 2:
            raise ValueError("Point sequences must contain exactly two values.")
        return float(point[0]), float(point[1])
    raise TypeError(f"Unsupported point representation: {type(point)!r}")


def distance_between_points(start: PointLike, end: PointLike) -> float:
    """Return the Euclidean distance between *start* and *end*."""

    sx, sy = _extract_xy(start)
    ex, ey = _extract_xy(end)
    return math.hypot(sx - ex, sy - ey)


def total_path_length(points: Sequence[PointLike], closed: bool = False) -> float:
    """Return the total length of a polyline or closed polygon in pixel units."""

    if len(points) < 2:
        return 0.0
    total = 0.0
    for start, end in zip(points[:-1], points[1:]):
        total += distance_between_points(start, end)
    if closed and len(points) >= 3:
        total += distance_between_points(points[-1], points[0])
    return total


def polygon_area(points: Sequence[PointLike]) -> float:
    """Return the area enclosed by *points* using the shoelace formula."""

    if len(points) < 3:
        return 0.0
    area = 0.0
    extracted = [_extract_xy(point) for point in points]
    for idx, (x, y) in enumerate(extracted):
        nx, ny = extracted[(idx + 1) % len(extracted)]
        area += x * ny
        area -= nx * y
    return abs(area) / 2.0


def can_close_loop(points: Sequence[PointLike]) -> bool:
    """Return ``True`` when *points* can form a closed loop."""

    return len(points) >= 3


def resolve_unit_multiplier(unit_name: str, units_per_pixel: Optional[float]) -> Optional[float]:
    """Return the conversion factor from pixels to the requested units."""

    if unit_name == "px":
        return 1.0
    return units_per_pixel


def unit_choice_label(unit_name: str) -> str:
    """Return the UI label for *unit_name*."""

    return _UNIT_DISPLAY_LOOKUP.get(unit_name, unit_name)


def display_unit_name(unit_name: str) -> str:
    """Return a concise unit name for measurements and area labels."""

    return "mi" if unit_name == "mi" else unit_name


@dataclass
class MeasurementResult:
    """Aggregate measurement values for a traced path."""

    total_pixels: float
    area_pixels: float
    unit_name: str
    unit_label: str
    display_unit_name: str
    unit_multiplier: Optional[float]
    total_units: Optional[float]
    area_units: Optional[float]
    closed: bool
    points_count: int
    secondary_distances: Dict[str, float]
    secondary_areas: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        """Return a serialisable representation for API responses."""

        return {
            "total_pixels": self.total_pixels,
            "area_pixels": self.area_pixels,
            "unit_name": self.unit_name,
            "unit_label": self.unit_label,
            "display_unit_name": self.display_unit_name,
            "unit_multiplier": self.unit_multiplier,
            "total_units": self.total_units,
            "area_units": self.area_units,
            "closed": self.closed,
            "points_count": self.points_count,
            "secondary_distances": self.secondary_distances,
            "secondary_areas": self.secondary_areas,
        }


def compute_measurements(
    points: Sequence[PointLike],
    *,
    closed: bool = False,
    unit_name: str = "px",
    units_per_pixel: Optional[float] = None,
) -> MeasurementResult:
    """Compute pixel and unit-based metrics for *points*."""

    points_count = len(points)
    loop_is_closed = closed and can_close_loop(points)
    total_pixels = total_path_length(points, closed=loop_is_closed)
    area_pixels = polygon_area(points) if loop_is_closed else 0.0
    unit_multiplier = resolve_unit_multiplier(unit_name, units_per_pixel)

    total_units: Optional[float]
    area_units: Optional[float]
    total_units = None
    area_units = None
    secondary_distances: Dict[str, float] = {}
    secondary_areas: Dict[str, float] = {}

    if unit_multiplier is not None:
        total_units = total_pixels * unit_multiplier
        if loop_is_closed:
            area_units = area_pixels * (unit_multiplier ** 2)
        if unit_name == "mi" and total_units is not None:
            km_value = total_units * 1.60934
            secondary_distances["km"] = km_value
            if area_units is not None:
                secondary_areas["km²"] = area_units * (1.60934 ** 2)

    return MeasurementResult(
        total_pixels=total_pixels,
        area_pixels=area_pixels,
        unit_name=unit_name,
        unit_label=unit_choice_label(unit_name),
        display_unit_name=display_unit_name(unit_name),
        unit_multiplier=unit_multiplier,
        total_units=total_units,
        area_units=area_units,
        closed=loop_is_closed,
        points_count=points_count,
        secondary_distances=secondary_distances,
        secondary_areas=secondary_areas,
    )


__all__ = [
    "UNIT_CHOICES",
    "MeasurementResult",
    "can_close_loop",
    "compute_measurements",
    "display_unit_name",
    "distance_between_points",
    "polygon_area",
    "resolve_unit_multiplier",
    "total_path_length",
    "unit_choice_label",
]
