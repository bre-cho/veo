"""template_routing_policy — maps tournament decisions to weighted routing splits.

Routing splits
--------------
challenger_promoted_to_incumbent  → incumbent 20% / challenger 80%
challenger_promoted               → incumbent 60% / challenger 40%
keep_weighted_routing             → incumbent 70% / challenger 30%
incumbent_retained                → incumbent 85% / challenger 15%
"""
from __future__ import annotations

from app.schemas.template_tournament import RoutingDecision

_ROUTING_TABLE: dict[str, tuple[float, float, str]] = {
    "challenger_promoted_to_incumbent": (0.20, 0.80, "challenger_overtook_incumbent"),
    "challenger_promoted": (0.60, 0.40, "challenger_showing_strength"),
    "keep_weighted_routing": (0.70, 0.30, "close_match_keep_testing"),
    "incumbent_retained": (0.85, 0.15, "incumbent_retained"),
}


class TemplateRoutingPolicy:
    """Translates a tournament decision string into a traffic routing split."""

    def decide(
        self,
        *,
        bracket_key: str,
        decision: str,
    ) -> RoutingDecision:
        """Return the routing weights for the given bracket after a match.

        Parameters
        ----------
        bracket_key:
            Composite key identifying the context bracket, e.g.
            ``"US|retention|ai|escalation"``.
        decision:
            One of the decision strings returned by
            :meth:`TemplateTournamentEngine.run_match`.
        """
        incumbent_weight, challenger_weight, reason = _ROUTING_TABLE.get(
            decision,
            (0.85, 0.15, "incumbent_retained"),  # safe default
        )
        return RoutingDecision(
            bracket_key=bracket_key,
            incumbent_weight=incumbent_weight,
            challenger_weight=challenger_weight,
            reason=reason,
        )
