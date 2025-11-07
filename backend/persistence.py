"""Very small JSON-backed persistence helpers for saved sessions."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, Optional


class SessionStore:
    """Persist session dictionaries to a JSON file.

    The store keeps the entire dataset in memory for simplicity, and writes the
    full payload back to disk each time a session changes. This is sufficient
    for development and small workloads, and avoids introducing a heavy
    database dependency for the initial backend implementation.
    """

    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({})

    def _read(self) -> Dict[str, dict]:
        with self._path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: Dict[str, dict]) -> None:
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def save_session(self, session_id: str, data: dict) -> None:
        with self._lock:
            payload = self._read()
            payload[session_id] = data
            self._write(payload)

    def load_session(self, session_id: str) -> Optional[dict]:
        with self._lock:
            payload = self._read()
            return payload.get(session_id)

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            payload = self._read()
            if session_id in payload:
                del payload[session_id]
                self._write(payload)

    def list_sessions(self) -> Dict[str, dict]:
        with self._lock:
            return self._read()
