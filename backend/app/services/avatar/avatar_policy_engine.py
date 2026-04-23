"""avatar_policy_engine — static + dynamic policy rules for avatar governance.

Policy constants
----------------
ACTIVE_THRESHOLD          Minimum total_score to be considered active-quality.
PRIORITY_THRESHOLD        Minimum total_score for priority promotion.
ROLLBACK_THRESHOLD        Score below which a rollback flag is raised.
COOLDOWN_DAYS             Default cooldown duration in publish cycles (days).
EXPLORATION_FLOOR         Minimum exploration quota (0–1) that must always be kept.
MIN_OUTCOMES_TO_PROMOTE   How many valid outcomes needed before any promotion.
CONSECUTIVE_WINS_NEEDED   Consecutive wins required for priority promotion.
RETENTION_DROP_THRESHOLD  Fractional drop vs. baseline that triggers rollback flag.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


# ── Policy constants ──────────────────────────────────────────────────────────
ACTIVE_THRESHOLD = 0.35
PRIORITY_THRESHOLD = 0.60
ROLLBACK_THRESHOLD = 0.20
COOLDOWN_DAYS = 5
EXPLORATION_FLOOR = 0.10
MIN_OUTCOMES_TO_PROMOTE = 3
CONSECUTIVE_WINS_NEEDED = 2
RETENTION_DROP_THRESHOLD = 0.15  # 15% drop triggers rollback consideration

# Governance penalty table (applied to final_rank_score)
GOVERNANCE_PENALTIES: dict[str, float] = {
    "continuity_break": -0.20,
    "brand_drift": -0.15,
    "retention_drop": -0.25,
    "consecutive_losses": -0.10,
    "policy_violation": -0.50,
}


class AvatarPolicyEngine:
    """Holds the rule set that governs avatar state transitions and scoring."""

    # ── Evaluation helpers ────────────────────────────────────────────────────

    def should_promote_to_active(
        self,
        *,
        total_score: float,
        outcome_count: int,
    ) -> bool:
        return outcome_count >= MIN_OUTCOMES_TO_PROMOTE and total_score >= ACTIVE_THRESHOLD

    def should_promote_to_priority(
        self,
        *,
        total_score: float,
        consecutive_wins: int,
        pair_fit_ok: bool = True,
    ) -> bool:
        return (
            total_score >= PRIORITY_THRESHOLD
            and consecutive_wins >= CONSECUTIVE_WINS_NEEDED
            and pair_fit_ok
        )

    def should_rollback(
        self,
        *,
        total_score: float,
        retention_drop: float = 0.0,
    ) -> bool:
        return (
            total_score < ROLLBACK_THRESHOLD
            or retention_drop >= RETENTION_DROP_THRESHOLD
        )

    def should_cooldown(
        self,
        *,
        has_continuity_break: bool,
        has_brand_drift: bool,
        consecutive_losses: int,
    ) -> bool:
        return (
            has_continuity_break
            or has_brand_drift
            or consecutive_losses >= 3
        )

    def compute_cooldown_until(self, days: int | None = None) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=days or COOLDOWN_DAYS
        )

    def is_in_cooldown(self, cooldown_until: datetime | None) -> bool:
        if cooldown_until is None:
            return False
        return datetime.now(timezone.utc).replace(tzinfo=None) < cooldown_until

    # ── Penalty computation ───────────────────────────────────────────────────

    def compute_governance_penalty(
        self,
        *,
        has_continuity_break: bool = False,
        has_brand_drift: bool = False,
        has_retention_drop: bool = False,
        consecutive_losses: int = 0,
        has_policy_violation: bool = False,
    ) -> float:
        penalty = 0.0
        if has_continuity_break:
            penalty += abs(GOVERNANCE_PENALTIES["continuity_break"])
        if has_brand_drift:
            penalty += abs(GOVERNANCE_PENALTIES["brand_drift"])
        if has_retention_drop:
            penalty += abs(GOVERNANCE_PENALTIES["retention_drop"])
        if consecutive_losses >= 3:
            penalty += abs(GOVERNANCE_PENALTIES["consecutive_losses"])
        if has_policy_violation:
            penalty += abs(GOVERNANCE_PENALTIES["policy_violation"])
        return round(penalty, 4)

    # ── Exploration budget ────────────────────────────────────────────────────

    def is_exploration_slot(
        self,
        *,
        rank: int,
        total_candidates: int,
        exploration_ratio: float,
    ) -> bool:
        """Return True if this rank slot should be filled by an exploration candidate."""
        if total_candidates == 0:
            return False
        floor = max(EXPLORATION_FLOOR, exploration_ratio)
        exploration_count = max(1, round(floor * total_candidates))
        return rank >= (total_candidates - exploration_count + 1)

    # ── State-machine helpers ─────────────────────────────────────────────────

    def next_state_after_action(
        self,
        current_state: str,
        action: str,
    ) -> str:
        transitions: dict[tuple[str, str], str] = {
            ("candidate", "promote"): "active",
            ("active", "promote"): "priority",
            ("priority", "cooldown"): "cooldown",
            ("active", "cooldown"): "cooldown",
            ("cooldown", "reactivate"): "active",
            ("active", "rollback"): "cooldown",
            ("priority", "rollback"): "cooldown",
            ("active", "block"): "blocked",
            ("priority", "block"): "blocked",
            ("cooldown", "block"): "blocked",
            ("blocked", "retire"): "retired",
            ("candidate", "block"): "blocked",
        }
        return transitions.get((current_state, action), current_state)

    def default_state_for_new_avatar(self) -> dict[str, Any]:
        return {
            "state": "candidate",
            "priority_weight": 0.5,
            "exploration_weight": 0.2,
            "risk_weight": 0.0,
        }
