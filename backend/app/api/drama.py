"""Deprecated compatibility module.

Use app.drama.api routers instead.
All drama routes are now registered via ALL_DRAMA_ROUTERS from app.drama.api.
"""

from app.drama.api import ALL_DRAMA_ROUTERS

__all__ = ["ALL_DRAMA_ROUTERS"]
