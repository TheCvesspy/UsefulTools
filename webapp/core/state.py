from __future__ import annotations

import reflex as rx


class AppState(rx.State):
    """Base application state shared across all features."""

    dark_mode: bool = False

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
