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
