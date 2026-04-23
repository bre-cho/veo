"""avatar_pair_optimizer — evaluates and ranks avatar × template pairings.

Pair score
----------
pair_score = 0.50 × avatar_score + 0.50 × template_score

Pair key format
---------------
``avatar_id::template_id::topic_class::market_code``

The equal weighting is intentional: neither avatar persona nor template
structure should dominate the other.  Tune the weights here as your data
matures.

Extended tracking (tournament layer)
--------------------------------------
The optimizer also tracks avatar × template_family, avatar × topic_class,
and avatar × platform affinities.  These are used by the tournament engine
to compute pair fit bonuses during candidate scoring.
"""
from __future__ import annotations

from typing import Any


class AvatarPairOptimizer:
    """Computes composite scores for avatar × template pairings."""

    def pair_key(
        self,
        *,
        avatar_id: str,
        template_id: str | None,
        topic_class: str | None,
        market_code: str | None,
    ) -> str:
        """Return a stable string key for an avatar × template × context combo."""
        return "::".join(
            [
                avatar_id or "none",
                template_id or "none",
                topic_class or "none",
                market_code or "none",
            ]
        )

    def compute_pair_score(
        self,
        *,
        avatar_score: float,
        template_score: float,
    ) -> float:
        """Compute the joint performance score for a (avatar, template) pair.

        Both inputs are expected to be normalised to [0, 1] (or 0–100 if
        you normalise at call site).  The output is on the same scale.
        """
        return round(0.50 * avatar_score + 0.50 * template_score, 4)

    def rank_pairs(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort a list of pair dicts by ``pair_score`` descending.

        Each element must contain at least ``avatar_id``, ``template_id``,
        and ``pair_score``.
        """
        return sorted(candidates, key=lambda x: x.get("pair_score", 0.0), reverse=True)

    # ── Extended tracking helpers ─────────────────────────────────────────────

    def build_pair_tracking_payload(
        self,
        *,
        avatar_id: str,
        template_id: str | None,
        template_family: str | None,
        topic_class: str | None,
        platform: str | None,
        market_code: str | None,
        avatar_score: float,
        template_score: float,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the full pair-tracking payload stored in PatternMemory.

        Returns a dict ready to be stored as the ``payload`` field in a
        PatternMemoryIn record with pattern_type="avatar_pair_fit".
        """
        pair_score = self.compute_pair_score(
            avatar_score=avatar_score,
            template_score=template_score,
        )
        return {
            "pair_key": self.pair_key(
                avatar_id=avatar_id,
                template_id=template_id,
                topic_class=topic_class,
                market_code=market_code,
            ),
            "avatar_id": avatar_id,
            "template_id": template_id,
            "template_family": template_family,
            "topic_class": topic_class,
            "platform": platform,
            "market_code": market_code,
            "pair_score": pair_score,
            "pair_confidence": 1.0,
            "pair_history_count": 1,
            "metrics": metrics or {},
        }

    def get_pair_bonus(
        self,
        *,
        pair_payload: dict[str, Any],
    ) -> float:
        """Extract the pair_score (bonus) from a stored pair-tracking payload."""
        return float((pair_payload or {}).get("pair_score", 0.0))

    def get_pair_confidence(
        self,
        *,
        pair_payload: dict[str, Any],
    ) -> float:
        """Extract confidence from a stored pair-tracking payload."""
        return float((pair_payload or {}).get("pair_confidence", 1.0))

    def get_pair_history_count(
        self,
        *,
        pair_payload: dict[str, Any],
    ) -> int:
        """Extract the history count from a stored pair-tracking payload."""
        return int((pair_payload or {}).get("pair_history_count", 0))
