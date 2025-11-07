"""FastAPI application exposing measurement utilities for the frontend."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .geometry import can_close_loop, compute_measurements
from .persistence import SessionStore

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "static"
INDEX_FILE = FRONTEND_DIR / "index.html"

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STORE_PATH = BASE_DIR / "data" / "sessions.json"
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

    @model_validator(mode="after")
    def validate_scale(self):
        units_per_pixel = self.units_per_pixel
        ref_distance = self.reference_distance
        ref_pixels = self.reference_pixel_length
        if units_per_pixel is not None:
            return self
        if ref_distance is not None and ref_pixels not in {None, 0}:
            self.units_per_pixel = ref_distance / ref_pixels
            return self
        if self.unit_name != "px":
            raise ValueError(
                "Provide either 'units_per_pixel' or both 'reference_distance' and "
                "'reference_pixel_length' for non-pixel units."
            )
        return self


class MeasurePayload(BaseModel):
    points: list[Point] = Field(..., description="Ordered list of measurement points.")
    closed: bool = Field(False, description="Treat the path as a closed polygon when true.")
    scale: ScalePayload = Field(default_factory=ScalePayload)
    session_id: Optional[str] = Field(None, description="Optional session identifier.")
    persist: bool = Field(
        False,
        description="Persist the request/response payload when a session identifier is provided.",
    )

    @model_validator(mode="after")
    def validate_points(self):
        if self.closed and not can_close_loop(self.points):
            raise ValueError("At least three points are required to close a path.")
        return self


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
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


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
                "points": [point.model_dump() for point in payload.points],
                "closed": payload.closed,
                "scale": payload.scale.model_dump(),
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


@app.get("/", response_class=HTMLResponse)
def frontend_index() -> HTMLResponse:
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=500, detail="Frontend assets are missing.")
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))
