from __future__ import annotations

from typing import Any, Dict


class EmotionalUpdateEngine:
    """Applies outcome-driven emotional shifts on top of a prior character state."""

    def apply(self, previous_state: Dict[str, Any], outcome: Dict[str, Any]) -> Dict[str, Any]:
        next_state = dict(previous_state or {})
        outcome_type = (outcome.get("outcome_type") or "").lower()

        trust_delta = float(outcome.get("trust_shift_delta", 0.0) or 0.0)
        exposure_delta = float(outcome.get("exposure_shift_delta", 0.0) or 0.0)

        if outcome_type == "betrayal":
            trust_delta -= 0.2
            exposure_delta += 0.15
        elif outcome_type == "confession":
            trust_delta += 0.15
            exposure_delta += 0.1

        next_state["trust_level"] = max(0.0, min(1.0, float(next_state.get("trust_level", 0.5)) + trust_delta))
        next_state["mask_strength"] = max(0.0, min(1.0, float(next_state.get("mask_strength", 0.5)) - max(0.0, exposure_delta)))
        next_state["openness_level"] = max(0.0, min(1.0, float(next_state.get("openness_level", 0.5)) + max(0.0, exposure_delta * 0.5)))
        return next_state
