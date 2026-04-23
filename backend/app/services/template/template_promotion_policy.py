"""template_promotion_policy — rules for advancing or retiring template candidates.

Promotion thresholds
--------------------
candidate → qualified    : sample_count ≥ 3  AND avg ≥ 75
qualified → promoted     : sample_count ≥ 5  AND avg ≥ 82  AND stability ≥ 70
promoted  → incumbent    : avg ≥ incumbent + 5, n ≥ 5
                           OR avg ≥ 90 AND incumbent < 85
candidate → rejected     : sample_count ≥ 3  AND avg < 60
incumbent → declining    : last_5_avg < 75   OR consecutive_drops ≥ 3
declining → retired      : last_5_avg < 65   AND replacement exists
"""
from __future__ import annotations


class TemplatePromotionPolicy:
    """Pure-logic promotion and demotion rules — no I/O."""

    # --------------------------------------------------------------------------
    # Upward transitions
    # --------------------------------------------------------------------------

    def classify_candidate(
        self,
        *,
        sample_count: int,
        average_score: float,
        stability_score: float,
    ) -> str:
        """Return the next lifecycle status for a candidate under test.

        Returns one of: rejected | qualified | promoted | testing
        """
        if sample_count >= 3 and average_score < 60:
            return "rejected"
        if sample_count >= 5 and average_score >= 82 and stability_score >= 70:
            return "promoted"
        if sample_count >= 3 and average_score >= 75:
            return "qualified"
        return "testing"

    def should_be_incumbent(
        self,
        *,
        challenger_score: float,
        incumbent_score: float,
        sample_count: int,
    ) -> bool:
        """Return True when a challenger should replace the current incumbent."""
        if sample_count >= 5 and challenger_score >= incumbent_score + 5:
            return True
        if sample_count >= 5 and challenger_score >= 90 and incumbent_score < 85:
            return True
        return False

    # --------------------------------------------------------------------------
    # Downward transitions
    # --------------------------------------------------------------------------

    def should_decline_incumbent(
        self,
        *,
        last_5_average: float,
        consecutive_drops: int,
    ) -> bool:
        """Return True when an incumbent should transition to *declining*."""
        return last_5_average < 75 or consecutive_drops >= 3

    def should_retire(
        self,
        *,
        last_5_average: float,
        replacement_exists: bool,
    ) -> bool:
        """Return True when a declining template should be retired."""
        return last_5_average < 65 and replacement_exists

    # --------------------------------------------------------------------------
    # Seeding priority (used by tournament scheduler to order candidates)
    # --------------------------------------------------------------------------

    def candidate_priority(
        self,
        *,
        parent_score: float,
        novelty_score: float,
        context_fit_score: float,
        evolution_confidence: float,
    ) -> float:
        """Compute a scheduling priority score for a candidate (0–100 scale).

        priority =
          0.40 * parent_score
        + 0.25 * novelty_score
        + 0.20 * context_fit_score
        + 0.15 * evolution_confidence
        """
        return (
            0.40 * parent_score
            + 0.25 * novelty_score
            + 0.20 * context_fit_score
            + 0.15 * evolution_confidence
        )
