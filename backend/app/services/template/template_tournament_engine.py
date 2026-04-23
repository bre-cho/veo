"""template_tournament_engine — runs challenger-vs-incumbent match evaluations.

Decision rules (delta = challenger_score - incumbent_score)
------------------------------------------------------------
delta ≥  10  →  challenger wins strongly  → challenger_promoted_to_incumbent
 5 ≤ delta < 10  →  challenger wins lightly  → challenger_promoted
-5 < delta <  5  →  draw                     → keep_weighted_routing
delta ≤ -5   →  incumbent retained           → incumbent_retained
"""
from __future__ import annotations

from app.schemas.template_tournament import TournamentMatchResult
from app.services.template.template_promotion_policy import TemplatePromotionPolicy


class TemplateTournamentEngine:
    """Compares two templates and emits a structured match result."""

    def __init__(self) -> None:
        self._policy = TemplatePromotionPolicy()

    def run_match(
        self,
        *,
        incumbent_template_id: str,
        challenger_template_id: str,
        incumbent_score: float,
        challenger_score: float,
        challenger_sample_count: int,
    ) -> TournamentMatchResult:
        """Evaluate one match between an incumbent and a challenger.

        Parameters
        ----------
        incumbent_template_id:
            ID of the currently dominant template in this bracket.
        challenger_template_id:
            ID of the candidate attempting to unseat the incumbent.
        incumbent_score:
            Average template_total_score for the incumbent over recent runs.
        challenger_score:
            Average template_total_score for the challenger so far.
        challenger_sample_count:
            Number of completed test runs for the challenger.
        """
        delta = challenger_score - incumbent_score

        if self._policy.should_be_incumbent(
            challenger_score=challenger_score,
            incumbent_score=incumbent_score,
            sample_count=challenger_sample_count,
        ):
            decision = "challenger_promoted_to_incumbent"
        elif delta >= 5.0:
            decision = "challenger_promoted"
        elif delta <= -5.0:
            decision = "incumbent_retained"
        else:
            decision = "keep_weighted_routing"

        return TournamentMatchResult(
            incumbent_template_id=incumbent_template_id,
            challenger_template_id=challenger_template_id,
            incumbent_score=round(incumbent_score, 4),
            challenger_score=round(challenger_score, 4),
            delta=round(delta, 4),
            decision=decision,
        )
