from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.channel_plan import ChannelPlan
from app.schemas.channel import ChannelPlanItem, ChannelPlanRequest, ChannelPlanResponse
from app.schemas.scoring import CandidateScore

# ---------------------------------------------------------------------------
# Title angle pool – grouped by goal so angles are contextually relevant
# ---------------------------------------------------------------------------
_GOAL_ANGLES: dict[str, list[str]] = {
    "awareness": [
        "The truth about {niche} you need to know",
        "Why everyone is talking about {niche} right now",
        "{niche} trends that are changing the game",
        "What no one tells you about {niche}",
        "The story behind {niche}",
        "Surprising facts about {niche}",
    ],
    "engagement": [
        "My honest {niche} experience",
        "Would you try this {niche} hack?",
        "Reacting to {niche} myths",
        "I tried {niche} for 7 days – here's what happened",
        "Hot take: {niche} is overrated (or is it?)",
        "Asking strangers about {niche}",
    ],
    "conversion": [
        "The {niche} product that changed my routine",
        "Why I switched to this {niche} solution",
        "{niche}: before vs after using this",
        "Stop wasting money on {niche} – do this instead",
        "Get your {niche} results in half the time",
        "The only {niche} guide you'll ever need",
    ],
    "retention": [
        "Part 2: My {niche} journey continues",
        "Update: 30 days of {niche}",
        "You asked, I answer: {niche} Q&A",
        "Deep dive into {niche}",
        "What I learned from 1 year of {niche}",
        "The {niche} series – episode {day}",
    ],
}

_DEFAULT_ANGLES = _GOAL_ANGLES["engagement"]

# ---------------------------------------------------------------------------
# Score profile weights – computed from request context instead of hardcoded
# ---------------------------------------------------------------------------
_PROFILE_NAMES = ("balanced", "platform_heavy", "conversion_push")

_GOAL_PROFILE_WEIGHTS: dict[str, dict[str, dict[str, float]]] = {
    "conversion": {
        "balanced":         {"audience_fit": 0.78, "platform_fit": 0.76, "product_fit": 0.80, "repeatability": 0.72, "conversion_potential": 0.88},
        "platform_heavy":   {"audience_fit": 0.74, "platform_fit": 0.88, "product_fit": 0.76, "repeatability": 0.80, "conversion_potential": 0.82},
        "conversion_push":  {"audience_fit": 0.72, "platform_fit": 0.72, "product_fit": 0.78, "repeatability": 0.70, "conversion_potential": 0.95},
    },
    "awareness": {
        "balanced":         {"audience_fit": 0.86, "platform_fit": 0.82, "product_fit": 0.74, "repeatability": 0.76, "conversion_potential": 0.68},
        "platform_heavy":   {"audience_fit": 0.80, "platform_fit": 0.90, "product_fit": 0.70, "repeatability": 0.82, "conversion_potential": 0.64},
        "conversion_push":  {"audience_fit": 0.78, "platform_fit": 0.74, "product_fit": 0.76, "repeatability": 0.68, "conversion_potential": 0.80},
    },
    "engagement": {
        "balanced":         {"audience_fit": 0.84, "platform_fit": 0.80, "product_fit": 0.78, "repeatability": 0.80, "conversion_potential": 0.74},
        "platform_heavy":   {"audience_fit": 0.78, "platform_fit": 0.90, "product_fit": 0.74, "repeatability": 0.84, "conversion_potential": 0.72},
        "conversion_push":  {"audience_fit": 0.74, "platform_fit": 0.76, "product_fit": 0.77, "repeatability": 0.70, "conversion_potential": 0.86},
    },
}

_SCORE_WEIGHTS = {
    "audience_fit": 0.22,
    "platform_fit": 0.20,
    "product_fit": 0.20,
    "repeatability": 0.18,
    "conversion_potential": 0.20,
}

# Maximum absolute adjustment any single weight can receive from learning data.
_MAX_WEIGHT_ADJUSTMENT = 0.05
# Per-weight floor/ceiling after adjustment to prevent any dimension collapsing.
_WEIGHT_MIN = 0.05
_WEIGHT_MAX = 0.50

# Thresholds for interpreting avg_conversion_score from the learning store.
_HIGH_CONVERSION_THRESHOLD = 0.75
_LOW_CONVERSION_THRESHOLD = 0.45

# Adjustment magnitudes applied when thresholds are crossed.
_CONVERSION_HIGH_BOOST = 0.03     # boost conversion_potential when performing well
_AUDIENCE_HIGH_PENALTY = -0.01    # minor rebalance away from audience_fit
_AUDIENCE_LOW_BOOST = 0.02        # diversify to audience reach when conversion is low
_PLATFORM_LOW_BOOST = 0.02        # diversify to platform reach when conversion is low
_CONVERSION_LOW_PENALTY = -0.02   # reduce conversion weight when avg score is poor
_REPEATABILITY_STABLE_HOOK = 0.02 # boost repeatability when a hook pattern is stable

# Minimum hook-pattern sample count considered "stable".
_STABLE_HOOK_MIN_SAMPLES = 3
# Minimum number of records required before any adaptive adjustment is made.
_ADAPTIVE_MIN_RECORDS = 5


def _derive_adaptive_weight_adjustments(learning_store: Any) -> dict[str, float]:
    """Return bounded additive adjustments to ``_SCORE_WEIGHTS`` from learning feedback.

    Requires at least ``_ADAPTIVE_MIN_RECORDS`` records before producing any
    adjustment so that a single outlier never biases the weight profile.
    All adjustments are clamped to ``±_MAX_WEIGHT_ADJUSTMENT``.
    """
    if learning_store is None:
        return {}
    try:
        summary = learning_store.feedback_summary()
    except Exception:
        return {}

    if summary.get("total_records", 0) < _ADAPTIVE_MIN_RECORDS:
        return {}

    avg_score: float = summary.get("avg_conversion_score", 0.0)
    adjustments: dict[str, float] = {}

    if avg_score >= _HIGH_CONVERSION_THRESHOLD:
        # High conversion performance observed – nudge toward conversion metrics
        adjustments["conversion_potential"] = _CONVERSION_HIGH_BOOST
        adjustments["audience_fit"] = _AUDIENCE_HIGH_PENALTY
    elif avg_score < _LOW_CONVERSION_THRESHOLD:
        # Low conversion – diversify toward audience and platform reach
        adjustments["audience_fit"] = _AUDIENCE_LOW_BOOST
        adjustments["platform_fit"] = _PLATFORM_LOW_BOOST
        adjustments["conversion_potential"] = _CONVERSION_LOW_PENALTY

    top_hooks = summary.get("top_hook_patterns", [])
    if top_hooks and top_hooks[0].get("sample_count", 0) >= _STABLE_HOOK_MIN_SAMPLES:
        # Stable hook patterns signal repeatable content formats
        adjustments["repeatability"] = (
            adjustments.get("repeatability", 0.0) + _REPEATABILITY_STABLE_HOOK
        )

    # Clamp all adjustments to ±_MAX_WEIGHT_ADJUSTMENT
    return {
        k: max(-_MAX_WEIGHT_ADJUSTMENT, min(_MAX_WEIGHT_ADJUSTMENT, v))
        for k, v in adjustments.items()
    }


def _apply_weight_adjustments(
    base: dict[str, float], adjustments: dict[str, float]
) -> dict[str, float]:
    """Return a normalised weight dict with adjustments applied."""
    adjusted = {k: base[k] + adjustments.get(k, 0.0) for k in base}
    # Clamp each weight so none collapses or dominates
    adjusted = {k: max(_WEIGHT_MIN, min(_WEIGHT_MAX, v)) for k, v in adjusted.items()}
    # Re-normalise so weights still sum to 1.0
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: round(v / total, 4) for k, v in adjusted.items()}
    return adjusted


def _compute_score_profile(req: ChannelPlanRequest) -> list[tuple[str, dict[str, float]]]:
    """Derive the three score profiles from the request goal, avoiding hardcoded index."""
    goal_key = (req.goal or "engagement").lower()
    profiles = _GOAL_PROFILE_WEIGHTS.get(goal_key, _GOAL_PROFILE_WEIGHTS["engagement"])
    return [(name, profiles[name]) for name in _PROFILE_NAMES]


class TitleAngleGenerator:
    """Generates non-repeating, context-aware title angles for a content plan.

    Selects from a goal-specific pool seeded by (niche, day, post_idx) so
    each post gets a deterministically different angle within the same run,
    ensuring no two posts in the same day share the same angle text.
    """

    def generate(
        self,
        niche: str,
        goal: str | None,
        day: int,
        post_idx: int,
        market_code: str | None = None,
    ) -> str:
        goal_key = (goal or "engagement").lower()
        pool = _GOAL_ANGLES.get(goal_key, _DEFAULT_ANGLES)
        # Stable, deterministic index: mix day + post_idx + niche + market using md5
        seed_str = f"{niche}:{day}:{post_idx}:{market_code or ''}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % len(pool)
        angle_template = pool[seed]
        return angle_template.format(niche=niche.title(), day=day)


class ChannelEngine:
    DEFAULT_FORMATS = ("short", "carousel", "talking_head")

    def __init__(self) -> None:
        self._angle_generator = TitleAngleGenerator()

    def generate_plan(
        self,
        req: ChannelPlanRequest,
        learning_store: Any | None = None,
    ) -> ChannelPlanResponse:
        candidates_with_plans = self._build_candidates(req, learning_store=learning_store)
        winner = max(candidates_with_plans, key=lambda item: item["score"].score_total)
        winner_score: CandidateScore = winner["score"]
        series_plan: list[ChannelPlanItem] = winner["plan"]

        candidates = [item["score"] for item in candidates_with_plans]
        for candidate in candidates:
            candidate.winner_flag = candidate.candidate_id == winner_score.candidate_id

        return ChannelPlanResponse(
            series_plan=series_plan,
            publish_queue_count=len(series_plan),
            calendar_summary={
                "days": req.days,
                "posts_per_day": req.posts_per_day,
                "total_posts": len(series_plan),
                "niche": req.niche,
            },
            candidates=candidates,
            winner_candidate_id=winner_score.candidate_id,
        )

    def generate_plan_and_persist(
        self,
        db: Session,
        req: ChannelPlanRequest,
        parent_plan_id: str | None = None,
        retry_count: int = 0,
        learning_store: Any | None = None,
    ) -> ChannelPlanResponse:
        plan = ChannelPlan(
            channel_name=req.channel_name,
            niche=req.niche,
            market_code=req.market_code,
            goal=req.goal,
            project_id=req.project_id,
            avatar_id=req.avatar_id,
            product_id=req.product_id,
            status="pending",
            request_context=req.model_dump(),
            payload={},
            parent_plan_id=parent_plan_id,
            retry_count=retry_count,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        plan.status = "running"
        plan.started_at = self._now()
        db.add(plan)
        db.commit()

        try:
            response = self.generate_plan(req, learning_store=learning_store)
            response.plan_id = plan.id
            plan.status = "completed"
            plan.completed_at = self._now()
            plan.payload = response.model_dump()
            plan.selected_variants = [item.model_dump() for item in response.series_plan]
            plan.ranking_scores = [candidate.model_dump() for candidate in response.candidates]
            plan.final_plan = {
                "winner_candidate_id": response.winner_candidate_id,
                "series_plan": [item.model_dump() for item in response.series_plan],
            }
            db.add(plan)
            db.commit()
            return response
        except Exception as exc:
            plan.status = "failed"
            plan.completed_at = self._now()
            plan.error_message = str(exc)
            db.add(plan)
            db.commit()
            raise

    def _build_candidates(
        self,
        req: ChannelPlanRequest,
        learning_store: Any | None = None,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        candidate_formats = [
            list(req.formats or self.DEFAULT_FORMATS),
            list(reversed(req.formats or self.DEFAULT_FORMATS)),
            [self.DEFAULT_FORMATS[0], self.DEFAULT_FORMATS[0], self.DEFAULT_FORMATS[-1]],
        ]
        score_profiles = _compute_score_profile(req)

        # Derive adaptive weight adjustments from learning store when available
        adjustments = _derive_adaptive_weight_adjustments(learning_store)
        effective_weights = (
            _apply_weight_adjustments(_SCORE_WEIGHTS, adjustments)
            if adjustments
            else _SCORE_WEIGHTS
        )
        feedback_applied = bool(adjustments)

        for idx, formats in enumerate(candidate_formats):
            variant_id, breakdown = score_profiles[idx]
            plan_items = self._build_plan_items(req, formats)
            total = round(
                sum(breakdown[k] * effective_weights[k] for k in effective_weights),
                3,
            )
            candidates.append(
                {
                    "plan": plan_items,
                    "score": CandidateScore(
                        candidate_id=f"channel_plan_{variant_id}",
                        score_total=total,
                        score_breakdown=breakdown,
                        rationale=f"Variant {variant_id} selected from audience/platform/product/repeatability/conversion matrix.",
                        metadata={"variant_index": idx + 1, "feedback_applied": feedback_applied},
                    ),
                }
            )
        return candidates

    def _build_plan_items(self, req: ChannelPlanRequest, formats: list[str]) -> list[ChannelPlanItem]:
        series_plan: list[ChannelPlanItem] = []
        for day in range(1, req.days + 1):
            for post_idx in range(req.posts_per_day):
                fmt = formats[(day + post_idx - 1) % len(formats)]
                title_angle = self._angle_generator.generate(
                    niche=req.niche,
                    goal=req.goal,
                    day=day,
                    post_idx=post_idx,
                    market_code=req.market_code,
                )
                series_plan.append(
                    ChannelPlanItem(
                        day_index=day,
                        format=fmt,
                        title_angle=title_angle,
                        content_goal=req.goal or "engagement",
                        cta_mode="soft" if (req.goal or "").lower() != "conversion" else "direct",
                        asset_type="video" if fmt in {"short", "talking_head"} else "image",
                        metadata={"channel_name": req.channel_name, "market_code": req.market_code},
                    )
                )
        return series_plan

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
