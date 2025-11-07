"""FastAPI application exposing measurement utilities for the frontend."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, model_validator

from .geometry import can_close_loop, compute_measurements
from .persistence import SessionStore

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STORE_PATH = BASE_DIR / "data" / "sessions.json"
_session_store = SessionStore(STORE_PATH)

FRONTEND_BUILD_DIR = PROJECT_ROOT / "webapp" / ".web"


def _find_frontend_index() -> Optional[Path]:
    """Return the bundled Reflex index page if one is available."""

    if not FRONTEND_BUILD_DIR.exists():
        return None

    candidates = [
        FRONTEND_BUILD_DIR / "_static" / "index.html",
        FRONTEND_BUILD_DIR / "pages" / "index.html",
        FRONTEND_BUILD_DIR / "index.html",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _frontend_fallback_html() -> str:
    """Return a helpful HTML landing page when the UI build is missing."""

    return """
    <!DOCTYPE html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <title>Useful Tools API</title>
        <style>
          body { font-family: system-ui, sans-serif; margin: 3rem auto; max-width: 640px; line-height: 1.6; color: #1f2933; }
          h1 { font-size: 2rem; margin-bottom: 1rem; }
          p { margin-bottom: 1rem; }
          code, pre { background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 0.25rem; }
          a { color: #2563eb; }
        </style>
      </head>
      <body>
        <h1>Useful Tools backend is running</h1>
        <p>This server powers the image measurement UI. The interactive interface is built with Reflex and can be launched separately with <code>reflex run</code>.</p>
        <p>If you only need to explore the API, head over to the <a href=\"/docs\">OpenAPI documentation</a>.</p>
        <p>To enable the web UI on this server, generate a Reflex build so that the static files appear under <code>webapp/.web</code> before starting the backend.</p>
      </body>
    </html>
    """


def _serve_frontend_index() -> HTMLResponse | FileResponse:
    """Serve the built Reflex UI or the fallback landing page."""

    frontend_index = _find_frontend_index()
    if frontend_index and frontend_index.is_file():
        return FileResponse(frontend_index)

    return HTMLResponse(content=_frontend_fallback_html(), status_code=200)


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

_STATIC_MOUNT_CANDIDATES: list[tuple[str, Path]] = [
    ("/_next", FRONTEND_BUILD_DIR / "_next"),
    ("/static", FRONTEND_BUILD_DIR / "static"),
    ("/assets", FRONTEND_BUILD_DIR / "assets"),
    ("/public", FRONTEND_BUILD_DIR / "public"),
    ("/_static", FRONTEND_BUILD_DIR / "_static"),
]

for mount_path, directory in _STATIC_MOUNT_CANDIDATES:
    if directory.is_dir():
        app.mount(mount_path, StaticFiles(directory=str(directory)), name=f"frontend-{mount_path.strip('/')}")


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


@app.get("/", include_in_schema=False)
def serve_frontend_root() -> HTMLResponse | FileResponse:
    """Serve the bundled Reflex front-end or display a helpful welcome page."""

    return _serve_frontend_index()


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    """Provide a helpful UI fallback when the root path returns 404."""

    if (
        exc.status_code == status.HTTP_404_NOT_FOUND
        and request.method in {"GET", "HEAD"}
        and request.url.path in {"", "/", "/index.html"}
    ):
        # Re-serve the frontend landing page when the router does not match the root path.
        return _serve_frontend_index()

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
