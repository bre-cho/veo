from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.channel_plan import ChannelPlan
from app.schemas.channel import ChannelPlanItem, ChannelPlanRequest, ChannelPlanResponse
from app.schemas.scoring import CandidateScore

# ---------------------------------------------------------------------------
# Angle pattern library – richer pool grouped by goal + pattern type
# ---------------------------------------------------------------------------
_ANGLE_PATTERN_LIBRARY: dict[str, dict[str, list[str]]] = {
    "awareness": {
        "curiosity": [
            "The truth about {niche} you need to know",
            "Why everyone is talking about {niche} right now",
            "What no one tells you about {niche}",
            "Surprising facts about {niche}",
        ],
        "story": [
            "The story behind {niche}",
            "{niche} trends that are changing the game",
            "How {niche} changed everything",
        ],
        "stat": [
            "Why 9 out of 10 {niche} users switch after 30 days",
            "The {niche} myth that is costing you time",
        ],
    },
    "engagement": {
        "personal": [
            "My honest {niche} experience",
            "I tried {niche} for 7 days – here's what happened",
            "What actually happened when I tested {niche}",
        ],
        "interactive": [
            "Would you try this {niche} hack?",
            "Reacting to {niche} myths",
            "Asking strangers about {niche}",
        ],
        "debate": [
            "Hot take: {niche} is overrated (or is it?)",
            "Unpopular opinion: {niche} needs this",
            "The {niche} debate no one is having",
        ],
    },
    "conversion": {
        "transformation": [
            "The {niche} product that changed my routine",
            "Why I switched to this {niche} solution",
            "{niche}: before vs after using this",
        ],
        "urgency": [
            "Stop wasting money on {niche} – do this instead",
            "Get your {niche} results in half the time",
            "The only {niche} guide you'll ever need",
        ],
        "proof": [
            "{niche} results after 30 days of consistent use",
            "Real {niche} before and after – no filter",
            "How I finally solved {niche} for good",
        ],
    },
    "retention": {
        "series": [
            "Part 2: My {niche} journey continues",
            "Update: 30 days of {niche}",
            "The {niche} series – episode {day}",
        ],
        "qa": [
            "You asked, I answer: {niche} Q&A",
            "Deep dive into {niche}",
            "{niche} FAQ – answering your top questions",
        ],
        "milestone": [
            "What I learned from 1 year of {niche}",
            "Month 3 of {niche}: honest reflections",
        ],
    },
}

# Flat pools keyed by goal for backward-compatible access
_GOAL_ANGLES: dict[str, list[str]] = {
    goal: [t for patterns in patterns_dict.values() for t in patterns]
    for goal, patterns_dict in _ANGLE_PATTERN_LIBRARY.items()
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

# Adjustment applied when a top template family consistently wins for the
# specific platform/market/goal context (contextual specialisation).
_CONTEXT_WIN_BOOST = 0.04
_CONTEXT_WIN_THRESHOLD = 2  # minimum wins to apply contextual boost

# Novelty scoring: penalise angles that were used in recent history.
_NOVELTY_DECAY_WINDOW = 30  # recent angle count considered for dedup
_NOVELTY_PENALTY = 0.25     # fraction of pool to avoid from head of recent history

# Budget constraint: assumed cost per published post (currency-agnostic unit).
# When a budget_constraint is supplied to generate_plan(), the series plan is
# capped to floor(budget_constraint / _DEFAULT_COST_PER_POST) total posts.
_DEFAULT_COST_PER_POST = 1.0


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


def _derive_contextual_weight_adjustments(
    learning_store: Any,
    *,
    platform: str | None,
    goal: str | None,
    market_code: str | None,
) -> dict[str, float]:
    """Derive weight adjustments filtered to the exact platform/market/goal context.

    This supplements the global ``_derive_adaptive_weight_adjustments()`` with
    context-specific signal: when we have enough data for this exact platform +
    market combination, those records are the strongest signal available and
    should dominate weight recalibration.

    Returns an additive adjustment dict (same shape as ``_SCORE_WEIGHTS``).
    Falls back to an empty dict when context-filtered data is insufficient.
    """
    if learning_store is None:
        return {}
    if not platform and not market_code:
        return {}  # no context to filter on – global adjustments are sufficient
    try:
        summary = learning_store.feedback_summary(platform=platform, market_code=market_code)
    except Exception:
        return {}

    if summary.get("total_records", 0) < _ADAPTIVE_MIN_RECORDS:
        return {}

    adjustments: dict[str, float] = {}
    avg_score: float = summary.get("avg_conversion_score", 0.0)

    # Inherit the same high/low threshold logic as the global version but with
    # doubled magnitude because the data is more contextually relevant.
    if avg_score >= _HIGH_CONVERSION_THRESHOLD:
        adjustments["conversion_potential"] = min(_MAX_WEIGHT_ADJUSTMENT, _CONVERSION_HIGH_BOOST * 1.5)
        adjustments["audience_fit"] = max(-_MAX_WEIGHT_ADJUSTMENT, _AUDIENCE_HIGH_PENALTY * 1.5)
    elif avg_score < _LOW_CONVERSION_THRESHOLD:
        adjustments["audience_fit"] = min(_MAX_WEIGHT_ADJUSTMENT, _AUDIENCE_LOW_BOOST * 1.5)
        adjustments["platform_fit"] = min(_MAX_WEIGHT_ADJUSTMENT, _PLATFORM_LOW_BOOST * 1.5)
        adjustments["conversion_potential"] = max(-_MAX_WEIGHT_ADJUSTMENT, _CONVERSION_LOW_PENALTY * 1.5)

    # Boost platform_fit when context data is platform-specific (strong signal that
    # platform matters for this channel).
    if platform:
        top_hooks = summary.get("top_hook_patterns", [])
        for hook in top_hooks:
            if hook.get("sample_count", 0) >= _CONTEXT_WIN_THRESHOLD:
                adjustments["platform_fit"] = (
                    adjustments.get("platform_fit", 0.0) + _CONTEXT_WIN_BOOST
                )
                break

    # Clamp all adjustments
    return {
        k: max(-_MAX_WEIGHT_ADJUSTMENT, min(_MAX_WEIGHT_ADJUSTMENT, v))
        for k, v in adjustments.items()
    }


def _compute_score_profile(req: ChannelPlanRequest) -> list[tuple[str, dict[str, float]]]:
    """Derive the three score profiles from the request goal, avoiding hardcoded index."""
    goal_key = (req.goal or "engagement").lower()
    profiles = _GOAL_PROFILE_WEIGHTS.get(goal_key, _GOAL_PROFILE_WEIGHTS["engagement"])
    return [(name, profiles[name]) for name in _PROFILE_NAMES]


class TitleAngleGenerator:
    """Generates non-repeating, context-aware title angles for a content plan.

    Supports:
    - Pattern library with multiple angle types per goal
    - Novelty scoring: avoids recently used angles via history injection
    - Non-deterministic selection within a session via seeded randomness,
      while still being reproducible when the same seed is given
    """

    def generate(
        self,
        niche: str,
        goal: str | None,
        day: int,
        post_idx: int,
        market_code: str | None = None,
        recent_angles: list[str] | None = None,
        platform: str | None = None,
    ) -> str:
        goal_key = (goal or "engagement").lower()
        pool = self._build_pool(goal_key, niche, platform)

        # Anti-duplicate: build set of recently-used formatted angles
        recent_window = recent_angles[-_NOVELTY_DECAY_WINDOW:] if recent_angles else []
        avoided = set(recent_window)

        # Build candidate pool excluding angles whose formatted version was recently used
        candidates = [
            t for t in pool
            if t.format(niche=niche.title(), day=day) not in avoided
        ]
        if not candidates:
            # Full fallback: at minimum, exclude the immediately preceding angle so
            # consecutive posts on the same day never produce identical angles
            last_used = recent_window[-1] if recent_window else None
            if last_used:
                candidates = [
                    t for t in pool
                    if t.format(niche=niche.title(), day=day) != last_used
                ]
            if not candidates:
                candidates = pool  # absolute fallback

        # Seed mixes niche + day + post + market for deterministic variety across days
        seed_str = f"{niche}:{goal_key}:{day}:{post_idx}:{market_code or ''}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        angle_template = rng.choice(candidates)
        return angle_template.format(niche=niche.title(), day=day)

    def compute_novelty_score(
        self,
        angle: str,
        recent_angles: list[str],
    ) -> float:
        """Return a novelty score in [0, 1] for an angle given recent history.

        1.0 = completely novel, 0.0 = exact duplicate of a very recent angle.
        The more recently an angle was used, the lower its novelty score.
        """
        if not recent_angles:
            return 1.0
        window = recent_angles[-_NOVELTY_DECAY_WINDOW:]
        if angle in window:
            # Higher forward-index in window = used more recently = lower novelty
            last_idx = len(window) - 1 - window[::-1].index(angle)
            recency = last_idx / max(len(window), 1)
            # Invert: very recent (recency→1) → score→0.1; older (recency→0) → score→0.6
            return round(0.1 + (1.0 - recency) * 0.5, 3)
        return 1.0

    @staticmethod
    def _build_pool(goal_key: str, niche: str, platform: str | None) -> list[str]:
        """Build an angle pool from the library, with platform-specific additions."""
        pool = list(_GOAL_ANGLES.get(goal_key, _DEFAULT_ANGLES))
        # TikTok/Reels: add short punchy patterns from engagement + awareness
        if platform and platform.lower() in ("tiktok", "reels", "shorts"):
            extra: list[str] = []
            for pt in ("curiosity", "personal", "interactive"):
                extra.extend(
                    _ANGLE_PATTERN_LIBRARY.get(goal_key, {}).get(pt, [])
                    + _ANGLE_PATTERN_LIBRARY.get("engagement", {}).get(pt, [])
                )
            pool.extend(t for t in extra if t not in pool)
        # YouTube: add series and milestone patterns for retention-style content
        elif platform and platform.lower() == "youtube":
            pool.extend(
                t for t in _GOAL_ANGLES.get("retention", [])
                if t not in pool
            )
        return pool


class ChannelEngine:
    DEFAULT_FORMATS = ("short", "carousel", "talking_head")

    def __init__(self) -> None:
        self._angle_generator = TitleAngleGenerator()

    def generate_plan(
        self,
        req: ChannelPlanRequest,
        learning_store: Any | None = None,
        angle_history: list[str] | None = None,
        objectives: dict[str, float] | None = None,
        budget_constraint: float | None = None,
    ) -> ChannelPlanResponse:
        candidates_with_plans = self._build_candidates(
            req,
            learning_store=learning_store,
            angle_history=angle_history,
            objectives=objectives,
        )
        winner = max(candidates_with_plans, key=lambda item: item["score"].score_total)
        winner_score: CandidateScore = winner["score"]
        series_plan: list[ChannelPlanItem] = winner["plan"]

        # Apply budget constraint: cap total posts to what the budget allows.
        budget_posts_cap: int | None = None
        if budget_constraint is not None and budget_constraint >= 0:
            budget_posts_cap = int(budget_constraint / _DEFAULT_COST_PER_POST)
            series_plan = series_plan[:budget_posts_cap]

        candidates = [item["score"] for item in candidates_with_plans]
        for candidate in candidates:
            candidate.winner_flag = candidate.candidate_id == winner_score.candidate_id

        calendar_summary: dict[str, Any] = {
            "days": req.days,
            "posts_per_day": req.posts_per_day,
            "total_posts": len(series_plan),
            "niche": req.niche,
        }
        if budget_posts_cap is not None:
            calendar_summary["budget_constraint"] = budget_constraint
            calendar_summary["budget_posts_cap"] = budget_posts_cap
            calendar_summary["budget_applied"] = len(series_plan) < req.days * req.posts_per_day

        return ChannelPlanResponse(
            series_plan=series_plan,
            publish_queue_count=len(series_plan),
            calendar_summary=calendar_summary,
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
        angle_history: list[str] | None = None,
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
            response = self.generate_plan(
                req,
                learning_store=learning_store,
                angle_history=angle_history,
            )
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
        angle_history: list[str] | None = None,
        objectives: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        candidate_formats = [
            list(req.formats or self.DEFAULT_FORMATS),
            list(reversed(req.formats or self.DEFAULT_FORMATS)),
            [self.DEFAULT_FORMATS[0], self.DEFAULT_FORMATS[0], self.DEFAULT_FORMATS[-1]],
        ]
        score_profiles = _compute_score_profile(req)

        # Derive adaptive weight adjustments from learning store when available.
        # Global adjustments are derived first; contextual (platform/market/goal)
        # adjustments are then ADDITIVELY merged so both signals compound.
        # Contextual signal is derived from a narrower, more relevant slice of
        # history, so the two sets reinforce each other rather than one cancelling
        # the other.
        adjustments = _derive_adaptive_weight_adjustments(learning_store)
        contextual = _derive_contextual_weight_adjustments(
            learning_store,
            platform=getattr(req, "platform", None),
            goal=req.goal,
            market_code=req.market_code,
        )
        # Additive merge: contextual adjustments are summed onto global adjustments
        # (both pulled from non-overlapping signal slices).
        merged_adjustments = {
            k: adjustments.get(k, 0.0) + contextual.get(k, 0.0)
            for k in set(list(adjustments) + list(contextual))
        }
        # Re-clamp after merge
        merged_adjustments = {
            k: max(-_MAX_WEIGHT_ADJUSTMENT, min(_MAX_WEIGHT_ADJUSTMENT, v))
            for k, v in merged_adjustments.items()
        }
        effective_weights = (
            _apply_weight_adjustments(_SCORE_WEIGHTS, merged_adjustments)
            if merged_adjustments
            else _SCORE_WEIGHTS
        )
        feedback_applied = bool(merged_adjustments)

        # Build MultiObjectiveScorer when objectives dict is supplied
        multi_scorer = None
        if objectives:
            try:
                from app.services.commerce.multi_objective_scorer import MultiObjectiveScorer
                multi_scorer = MultiObjectiveScorer(objectives)
            except Exception:
                pass

        for idx, formats in enumerate(candidate_formats):
            variant_id, breakdown = score_profiles[idx]
            plan_items = self._build_plan_items(req, formats, angle_history=angle_history)
            base_total = round(
                sum(breakdown[k] * effective_weights[k] for k in effective_weights),
                3,
            )
            # When multi-objective scorer is provided, blend it with the base score
            if multi_scorer is not None and learning_store is not None:
                try:
                    records = learning_store.all_records()
                    if records:
                        obj_scores = [multi_scorer.score(r) for r in records]
                        avg_obj = sum(obj_scores) / len(obj_scores)
                        # 50/50 blend of base score and objective score
                        total = round((base_total + avg_obj) / 2.0, 3)
                    else:
                        total = base_total
                except Exception:
                    total = base_total
            else:
                total = base_total

            candidates.append(
                {
                    "plan": plan_items,
                    "score": CandidateScore(
                        candidate_id=f"channel_plan_{variant_id}",
                        score_total=total,
                        score_breakdown=breakdown,
                        rationale=f"Variant {variant_id} selected from audience/platform/product/repeatability/conversion matrix.",
                        metadata={
                            "variant_index": idx + 1,
                            "feedback_applied": feedback_applied,
                            "multi_objective": objectives is not None,
                        },
                    ),
                }
            )
        return candidates

    def _build_plan_items(
        self,
        req: ChannelPlanRequest,
        formats: list[str],
        angle_history: list[str] | None = None,
    ) -> list[ChannelPlanItem]:
        series_plan: list[ChannelPlanItem] = []
        used_angles: list[str] = list(angle_history or [])
        platform = getattr(req, "platform", None)

        for day in range(1, req.days + 1):
            for post_idx in range(req.posts_per_day):
                fmt = formats[(day + post_idx - 1) % len(formats)]
                title_angle = self._angle_generator.generate(
                    niche=req.niche,
                    goal=req.goal,
                    day=day,
                    post_idx=post_idx,
                    market_code=req.market_code,
                    recent_angles=used_angles,
                    platform=platform,
                )
                novelty = self._angle_generator.compute_novelty_score(title_angle, used_angles)
                used_angles.append(title_angle)

                series_plan.append(
                    ChannelPlanItem(
                        day_index=day,
                        format=fmt,
                        title_angle=title_angle,
                        content_goal=req.goal or "engagement",
                        cta_mode="soft" if (req.goal or "").lower() != "conversion" else "direct",
                        asset_type="video" if fmt in {"short", "talking_head"} else "image",
                        metadata={
                            "channel_name": req.channel_name,
                            "market_code": req.market_code,
                            "novelty_score": novelty,
                        },
                    )
                )
        return series_plan

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
