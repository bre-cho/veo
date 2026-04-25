from __future__ import annotations

REBUILD_POLICY: dict = {
    "required_threshold": 0.75,
    "optional_threshold": 0.45,
    "always_required": [
        "timeline",
        "voice",
        "subtitle",
    ],
}
