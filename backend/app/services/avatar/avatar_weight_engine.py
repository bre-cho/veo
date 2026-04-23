from __future__ import annotations

from typing import Any


class AvatarWeightEngine:
    def compute_final_score(self, *, base_score: float, priority_weight: float, pair_bonus: float, continuity_bonus: float, exploration_bonus: float, governance_penalty: float) -> float:
        weighted = base_score * max(priority_weight, 0.0)
        weighted += pair_bonus + continuity_bonus + exploration_bonus
        weighted -= max(governance_penalty, 0.0)
        return round(weighted, 4)

    def compute_governance_penalty(self, *, state: str, risk_weight: float, cooldown_until, now) -> float:
        penalty = risk_weight
        if state == "cooldown" and cooldown_until and cooldown_until > now:
            penalty += 1.0
        if state == "blocked":
            penalty += 999.0
        return penalty
