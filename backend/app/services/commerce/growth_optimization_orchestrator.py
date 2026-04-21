"""GrowthOptimizationOrchestrator — joint budget + creative + conversion optimizer.

Combines:
- ``MultiObjectiveScorer``: Pareto-weighted scoring of variant candidates
- ``CampaignBudgetPolicy``: budget feasibility filter
- ``PerformanceLearningEngine``: creative feedback boosts

Usage::

    orchestrator = GrowthOptimizationOrchestrator(db=db)
    plan = orchestrator.optimize(
        campaign_id="camp_123",
        candidates=[{"video_id": ..., "conversion_score": 0.8, ...}],
        objectives={"conversion": 0.5, "ctr": 0.3, "roas": 0.2},
        budget_constraint={"daily_limit": 5, "remaining": 3},
        platform="tiktok",
    )
"""
from __future__ import annotations

import logging
import os
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Portfolio-level platform daily limit (overrides per-campaign when set)
_PORTFOLIO_DAILY_PLATFORM_LIMIT = int(
    os.environ.get("PORTFOLIO_DAILY_PLATFORM_LIMIT", "100")
)


class GrowthOptimizationOrchestrator:
    """Jointly optimise budget allocation and creative selection.

    ``optimize()`` returns a ranked allocation plan that:
    1. Scores each candidate with ``MultiObjectiveScorer`` (with calibration)
    2. Filters out candidates that would exceed the campaign budget
    3. Enriches scores with creative feedback boosts from the learning engine
    4. Returns a ranked list with budget allocation recommendations
    """

    def __init__(
        self,
        db: "Session | None" = None,
        learning_store: Any | None = None,
    ) -> None:
        self._db = db
        self._learning_store = learning_store

    def optimize(
        self,
        campaign_id: str,
        candidates: list[dict[str, Any]],
        objectives: dict[str, float] | None = None,
        budget_constraint: dict[str, Any] | None = None,
        platform: str | None = None,
        product_category: str | None = None,
        market_code: str | None = None,
        goal: str | None = None,
        use_model_ranking: bool = True,
    ) -> dict[str, Any]:
        """Return a ranked allocation plan for a campaign's variant candidates.

        Args:
            campaign_id: The campaign to optimize for.
            candidates: List of variant/creative candidate records.  Each record
                should contain at minimum ``video_id``, ``conversion_score``, and
                optionally ``click_through_rate``, ``performance_metrics``.
            objectives: Objective weights for MultiObjectiveScorer.  Defaults to
                ``{"conversion": 0.5, "ctr": 0.3, "roas": 0.2}``.
            budget_constraint: Dict with ``daily_limit`` (int) and ``remaining``
                (int) keys.  Candidates are filtered to those that fit within the
                remaining budget.
            platform: Target platform for calibration lookup.
            product_category: Product category for calibration lookup.
            market_code: Market code for contextual weight adjustments.
            goal: Content goal (e.g. "conversion", "awareness").
            use_model_ranking: When True (default), apply ``ModelDrivenRankingEngine``
                on top of the composite score for a richer final ranking.

        Returns:
            Dict with:
            - ``campaign_id``
            - ``ranked_candidates``: list of scored+ranked candidates
            - ``budget_summary``: remaining / limit / feasible_count
            - ``top_pick``: highest-scoring budget-feasible candidate
            - ``allocation_plan``: list of {video_id, score, budget_share}
            - ``ranking_method``: "model_driven" or "linear_weighted"
            - ``funnel_summary``: joint creative × conversion × budget funnel breakdown
        """
        from app.services.commerce.multi_objective_scorer import MultiObjectiveScorer
        from app.services.commerce.scoring_calibration_applier import ScoringCalibrationApplier
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        base_objectives = objectives or {"conversion": 0.5, "ctr": 0.3, "roas": 0.2}

        # Apply calibration to objective weights when available
        calibration_applier = ScoringCalibrationApplier(db=self._db)
        effective_objectives = calibration_applier.get_objective_weights(
            base_objectives=base_objectives,
            platform=platform,
            product_category=product_category,
        )

        # Enrich candidates with budget_score if budget_constraint provided
        enriched = self._enrich_with_budget_score(candidates, budget_constraint)

        # Add budget_score to objectives if budget is constrained
        if budget_constraint:
            effective_objectives["budget_score"] = 0.15
            # Re-normalise
            total = sum(effective_objectives.values())
            effective_objectives = {k: round(v / total, 4) for k, v in effective_objectives.items()}

        scorer = MultiObjectiveScorer(
            effective_objectives,
            calibration_store=calibration_applier,
            platform=platform,
            product_category=product_category,
        )
        scored = scorer.score_candidates(enriched)

        # --- Model-driven ranking on top of composite score ---
        ranking_method = "linear_weighted"
        if use_model_ranking and len(scored) > 1:
            try:
                ranker = ModelDrivenRankingEngine(n_rounds=5)
                # Use historical records from learning store as reference
                reference_records: list[dict[str, Any]] = []
                if self._learning_store is not None:
                    try:
                        reference_records = self._learning_store.all_records()
                    except Exception:
                        pass
                ranked = ranker.rank(scored, reference_records=reference_records)
                # Blend: 70% composite_score + 30% ensemble_score
                for item in ranked:
                    blended = round(
                        0.70 * item.get("composite_score", 0.0)
                        + 0.30 * item.get("ensemble_score", 0.0),
                        4,
                    )
                    item["blended_score"] = blended
                ranked.sort(key=lambda x: x.get("blended_score", 0.0), reverse=True)
                scored = ranked
                ranking_method = "model_driven"
            except Exception as exc:
                logger.warning("GrowthOptimizationOrchestrator: model ranking failed: %s", exc)

        # Budget feasibility filter
        daily_limit = int((budget_constraint or {}).get("daily_limit", 999))
        remaining = int((budget_constraint or {}).get("remaining", daily_limit))
        feasible = scored[:remaining] if remaining < len(scored) else scored

        score_key = "blended_score" if ranking_method == "model_driven" else "composite_score"
        total_score = sum(c.get(score_key, 0.0) for c in feasible) or 1.0

        allocation_plan = [
            {
                "video_id": c.get("video_id"),
                "variant_id": c.get("variant_id"),
                "composite_score": c.get("composite_score"),
                "blended_score": c.get(score_key),
                "budget_share": round(c.get(score_key, 0.0) / total_score, 4),
                "recommended_publishes": max(
                    1,
                    round(remaining * c.get(score_key, 0.0) / total_score),
                ),
            }
            for c in feasible
        ]

        # --- Joint funnel summary ---
        funnel_summary = self._build_funnel_summary(
            candidates=candidates,
            feasible=feasible,
            budget_constraint=budget_constraint,
            platform=platform,
            goal=goal,
        )

        return {
            "campaign_id": campaign_id,
            "platform": platform,
            "market_code": market_code,
            "goal": goal,
            "objectives_used": effective_objectives,
            "ranking_method": ranking_method,
            "ranked_candidates": scored,
            "budget_summary": {
                "daily_limit": daily_limit,
                "remaining": remaining,
                "total_candidates": len(candidates),
                "feasible_count": len(feasible),
            },
            "top_pick": feasible[0] if feasible else None,
            "allocation_plan": allocation_plan,
            "funnel_summary": funnel_summary,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_funnel_summary(
        self,
        candidates: list[dict[str, Any]],
        feasible: list[dict[str, Any]],
        budget_constraint: dict[str, Any] | None,
        platform: str | None,
        goal: str | None,
    ) -> dict[str, Any]:
        """Build a joint creative × conversion × budget × platform funnel breakdown."""
        if not candidates:
            return {}

        # Creative diversity: unique hook_patterns
        hook_patterns = {c.get("hook_pattern") for c in candidates if c.get("hook_pattern")}
        conversion_scores = [float(c.get("conversion_score", 0.0)) for c in candidates]
        avg_conversion = round(sum(conversion_scores) / len(conversion_scores), 4)
        top_conversion = round(max(conversion_scores), 4) if conversion_scores else 0.0

        # Budget utilization
        daily_limit = float((budget_constraint or {}).get("daily_limit", len(candidates)))
        budget_utilization = round(len(feasible) / max(daily_limit, 1), 4)

        # Platform fit (proxy: count candidates with platform-specific metadata)
        platform_fit_count = sum(
            1 for c in candidates
            if c.get("platform") == platform or not c.get("platform")
        )

        return {
            "creative_diversity": len(hook_patterns),
            "avg_conversion_score": avg_conversion,
            "top_conversion_score": top_conversion,
            "budget_utilization": budget_utilization,
            "feasible_candidates": len(feasible),
            "total_candidates": len(candidates),
            "platform_fit_count": platform_fit_count,
            "goal": goal,
            "funnel_stages": {
                "creative": len(candidates),
                "conversion_eligible": sum(1 for c in candidates if float(c.get("conversion_score", 0.0)) >= 0.5),
                "budget_feasible": len(feasible),
                "platform_ready": platform_fit_count,
            },
        }

    @staticmethod
    def _enrich_with_budget_score(
        candidates: list[dict[str, Any]],
        budget_constraint: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Inject budget_remaining / budget_daily_limit into performance_metrics."""
        if not budget_constraint:
            return candidates
        daily_limit = float(budget_constraint.get("daily_limit", 1))
        remaining = float(budget_constraint.get("remaining", daily_limit))
        enriched = []
        for c in candidates:
            c2 = dict(c)
            metrics = dict(c2.get("performance_metrics") or {})
            metrics["budget_remaining"] = remaining
            metrics["budget_daily_limit"] = daily_limit
            c2["performance_metrics"] = metrics
            enriched.append(c2)
        return enriched
