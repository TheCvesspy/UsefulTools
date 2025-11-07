from __future__ import annotations

import reflex as rx

from ..core.pages.landing import landing as landing_page


def index() -> rx.Component:
    """Entry point page rendering the shared landing dashboard."""

    return landing_page()
