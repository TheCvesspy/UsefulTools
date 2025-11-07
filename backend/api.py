"""FastAPI application exposing measurement utilities for the frontend."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, root_validator

from .geometry import can_close_loop, compute_measurements
from .persistence import SessionStore

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STORE_PATH = Path(__file__).resolve().parent / "data" / "sessions.json"
_session_store = SessionStore(STORE_PATH)


def get_store() -> SessionStore:
    return _session_store


class Point(BaseModel):
    x: float
    y: float


class ScalePayload(BaseModel):
    unit_name: str = Field("px", description="Unit identifier, e.g. 'px' or 'cm'.")
    units_per_pixel: Optional[float] = Field(
        None, description="Conversion factor from pixels to the provided units."
    )
    reference_distance: Optional[float] = Field(
        None, description="Real-world distance between the reference points."
    )
    reference_pixel_length: Optional[float] = Field(
        None, description="Pixel distance between the reference points."
    )

    @root_validator
    def validate_scale(cls, values):  # type: ignore[override]
        units_per_pixel = values.get("units_per_pixel")
        ref_distance = values.get("reference_distance")
        ref_pixels = values.get("reference_pixel_length")
        if units_per_pixel is not None:
            return values
        if ref_distance is not None and ref_pixels not in {None, 0}:
            values["units_per_pixel"] = ref_distance / ref_pixels
            return values
        if values.get("unit_name") != "px":
            raise ValueError(
                "Provide either 'units_per_pixel' or both 'reference_distance' and "
                "'reference_pixel_length' for non-pixel units."
            )
        return values


class MeasurePayload(BaseModel):
    points: list[Point] = Field(..., description="Ordered list of measurement points.")
    closed: bool = Field(False, description="Treat the path as a closed polygon when true.")
    scale: ScalePayload = Field(default_factory=ScalePayload)
    session_id: Optional[str] = Field(None, description="Optional session identifier.")
    persist: bool = Field(
        False,
        description="Persist the request/response payload when a session identifier is provided.",
    )

    @root_validator
    def validate_points(cls, values):  # type: ignore[override]
        if values.get("closed") and not can_close_loop(values.get("points", [])):
            raise ValueError("At least three points are required to close a path.")
        return values


class MeasurementResponse(BaseModel):
    session_id: Optional[str]
    measurement: dict


app = FastAPI(title="Image Measurement Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.post("/upload")
async def upload_image(request: Request, file: UploadFile = File(...)) -> dict:
    """Store an uploaded image locally and return the public URL."""

    suffix = Path(file.filename).suffix or ".bin"
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    contents = await file.read()
    destination.write_bytes(contents)
    url = request.url_for("uploads", path=destination.name)
    return {"url": str(url), "filename": file.filename}


@app.post("/measure", response_model=MeasurementResponse)
def measure_points(payload: MeasurePayload, store: SessionStore = Depends(get_store)):
    """Return pixel/unit distances and optional persistence metadata."""

    measurement = compute_measurements(
        payload.points,
        closed=payload.closed,
        unit_name=payload.scale.unit_name,
        units_per_pixel=payload.scale.units_per_pixel,
    )

    response_payload = MeasurementResponse(session_id=payload.session_id, measurement=measurement.to_dict())

    if payload.persist and payload.session_id:
        store.save_session(
            payload.session_id,
            {
                "points": [point.dict() for point in payload.points],
                "closed": payload.closed,
                "scale": payload.scale.dict(),
                "measurement": measurement.to_dict(),
            },
        )

    return response_payload


@app.get("/sessions/{session_id}")
def get_session(session_id: str, store: SessionStore = Depends(get_store)) -> dict:
    session = store.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "payload": session}


@app.get("/sessions")
def list_sessions(store: SessionStore = Depends(get_store)) -> dict:
    return {"sessions": store.list_sessions()}
