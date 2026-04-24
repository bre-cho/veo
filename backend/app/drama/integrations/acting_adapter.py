from __future__ import annotations

from typing import Any, Dict


def to_acting_hints(drama_state: Dict[str, Any]) -> Dict[str, Any]:
    pressure = float(drama_state.get("pressure_level", 0.0) or 0.0)
    return {
        "tempo_override": "slow_tight" if pressure > 0.6 else "neutral",
        "gaze_pattern": "avoid_then_lock" if pressure > 0.5 else "stable",
        "movement_density": "minimal_rigid" if pressure > 0.6 else "natural",
        "pause_pattern": "long_loaded" if pressure > 0.65 else "balanced",
        "pressure_behavior": "deepen_calm" if pressure > 0.6 else "keep_flow",
        "mask_openness_blend": max(0.0, min(1.0, 1.0 - pressure)),
    }
