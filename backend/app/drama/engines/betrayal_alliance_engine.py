from __future__ import annotations

from typing import Any, Dict


class BetrayalAllianceEngine:
    """Simple directional relationship mutation for betrayal/alliance events."""

    def apply(self, relationship_snapshot: Dict[str, Any], outcome: Dict[str, Any]) -> Dict[str, Any]:
        updated = dict(relationship_snapshot or {})
        outcome_type = (outcome.get("outcome_type") or "").lower()

        trust = float(updated.get("trust_level", 0.0) or 0.0)
        resentment = float(updated.get("resentment_level", 0.0) or 0.0)

        if outcome_type == "betrayal":
            trust = max(0.0, trust - 0.25)
            resentment = min(1.0, resentment + 0.3)
        elif outcome_type in {"rescue", "reassurance"}:
            trust = min(1.0, trust + 0.2)
            resentment = max(0.0, resentment - 0.1)

        updated["trust_level"] = trust
        updated["resentment_level"] = resentment
        return updated
