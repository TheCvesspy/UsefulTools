from __future__ import annotations

import reflex as rx


class AppState(rx.State):
    """Application-wide state shared across all features."""

    dark_mode: bool = False

    def toggle_theme(self) -> None:
        """Toggle between light and dark color schemes."""

        self.dark_mode = not self.dark_mode
