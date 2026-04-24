from __future__ import annotations

from typing import Any, Dict


class ChemistryEngine:
    """Optional lightweight chemistry estimator used during recompute passes."""

    def score(self, relationship_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        trust = float(relationship_snapshot.get("trust_level", 0.0) or 0.0)
        attraction = float(relationship_snapshot.get("attraction_level", 0.0) or 0.0)
        fear = float(relationship_snapshot.get("fear_level", 0.0) or 0.0)

        affinity = max(0.0, min(1.0, 0.6 * trust + 0.4 * attraction - 0.25 * fear))
        volatility = max(0.0, min(1.0, abs(attraction - trust) + fear * 0.4))
        return {
            "affinity": round(affinity, 3),
            "volatility": round(volatility, 3),
        }
