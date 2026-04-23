"""avatar_weight_engine — computes the final selection weight for an avatar.

Final weight formula
---------------------
final_weight =
    base_priority_weight
  + pair_bonus
  + continuity_bonus
  + recent_win_bonus
  - decay_penalty
  - governance_penalty
  - risk_penalty

All components are normalised to [0, 1] before use.
The result is clamped to [0, 1].
"""
from __future__ import annotations

from typing import Any


# ── Weight constants ──────────────────────────────────────────────────────────
_PAIR_BONUS_MAX = 0.20
_CONTINUITY_BONUS_MAX = 0.15
_RECENT_WIN_BONUS_MAX = 0.10
_DECAY_PENALTY_MAX = 0.10
_RISK_PENALTY_MAX = 0.15


class AvatarWeightEngine:
    """Computes the final ranking weight for an avatar candidate."""

    def compute(
        self,
        *,
        base_priority_weight: float,
        pair_bonus: float = 0.0,
        continuity_bonus: float = 0.0,
        recent_win_bonus: float = 0.0,
        decay_penalty: float = 0.0,
        governance_penalty: float = 0.0,
        risk_penalty: float = 0.0,
    ) -> float:
        raw = (
            base_priority_weight
            + min(pair_bonus, _PAIR_BONUS_MAX)
            + min(continuity_bonus, _CONTINUITY_BONUS_MAX)
            + min(recent_win_bonus, _RECENT_WIN_BONUS_MAX)
            - min(decay_penalty, _DECAY_PENALTY_MAX)
            - governance_penalty
            - min(risk_penalty, _RISK_PENALTY_MAX)
        )
        return round(max(0.0, min(1.0, raw)), 4)

    def compute_pair_bonus(
        self,
        *,
        pair_score: float,
        pair_confidence: float = 1.0,
    ) -> float:
        """Convert a pair_score [0,1] into a bounded bonus contribution."""
        return round(min(pair_score * pair_confidence * _PAIR_BONUS_MAX, _PAIR_BONUS_MAX), 4)

    def compute_continuity_bonus(
        self,
        *,
        continuity_confidence: float | None,
    ) -> float:
        if continuity_confidence is None:
            return 0.0
        return round(min(continuity_confidence * _CONTINUITY_BONUS_MAX, _CONTINUITY_BONUS_MAX), 4)

    def compute_recent_win_bonus(
        self,
        *,
        recent_win_count: int,
        max_window: int = 5,
    ) -> float:
        ratio = min(recent_win_count / max(max_window, 1), 1.0)
        return round(ratio * _RECENT_WIN_BONUS_MAX, 4)

    def compute_decay_penalty(
        self,
        *,
        days_since_last_win: int,
        decay_start_days: int = 14,
    ) -> float:
        if days_since_last_win <= decay_start_days:
            return 0.0
        excess = days_since_last_win - decay_start_days
        ratio = min(excess / 30.0, 1.0)
        return round(ratio * _DECAY_PENALTY_MAX, 4)

    def build_debug_breakdown(
        self,
        *,
        avatar_id: str,
        base_priority_weight: float,
        pair_bonus: float,
        continuity_bonus: float,
        recent_win_bonus: float,
        decay_penalty: float,
        governance_penalty: float,
        risk_penalty: float,
        final_weight: float,
        state: str,
    ) -> dict[str, Any]:
        lines: list[str] = []
        if pair_bonus > 0:
            lines.append(f"Pair fit bonus: +{pair_bonus:.3f}")
        if continuity_bonus > 0:
            lines.append(f"Continuity bonus: +{continuity_bonus:.3f}")
        if recent_win_bonus > 0:
            lines.append(f"Recent win bonus: +{recent_win_bonus:.3f}")
        if decay_penalty > 0:
            lines.append(f"Decay penalty: -{decay_penalty:.3f}")
        if governance_penalty > 0:
            lines.append(f"Governance penalty: -{governance_penalty:.3f}")
        if risk_penalty > 0:
            lines.append(f"Risk penalty: -{risk_penalty:.3f}")
        return {
            "avatar_id": avatar_id,
            "base_score": base_priority_weight,
            "pair_bonus": pair_bonus,
            "continuity_bonus": continuity_bonus,
            "governance_penalty": governance_penalty,
            "exploration_bonus": 0.0,
            "final_score": final_weight,
            "state": state,
            "explanation_lines": lines,
        }
