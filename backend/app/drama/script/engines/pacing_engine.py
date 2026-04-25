"""pacing_engine — assigns duration_sec to each script segment."""
from __future__ import annotations

from typing import Any, Dict, List

_PURPOSE_DURATIONS: Dict[str, float] = {
    "hook": 3.0,
    "reveal": 5.0,
    "twist": 5.0,
    "cliffhanger": 4.0,
    "escalation": 4.0,
    "callback": 4.0,
    "setup": 3.5,
    "context": 3.5,
}

_DEFAULT_DURATION = 4.0


def apply_pacing(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Set ``duration_sec`` on each segment based on its ``purpose``."""
    paced = []
    for seg in segments:
        purpose = seg.get("purpose", "")
        seg["duration_sec"] = _PURPOSE_DURATIONS.get(purpose, _DEFAULT_DURATION)
        paced.append(seg)
    return paced
