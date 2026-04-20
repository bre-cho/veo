from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas.scoring import CandidateScore
from app.schemas.trend_image import TrendImageConcept, TrendImageRequest, TrendImageResponse

# ---------------------------------------------------------------------------
# Scoring weights – kept in a module-level dict so they are easy to tune
# without touching business logic.
# ---------------------------------------------------------------------------
_SCORE_WEIGHTS: dict[str, float] = {
    "relevance": 0.28,
    "trend_fit": 0.30,
    "market_fit": 0.20,
    "visual_strength": 0.22,
}

_NICHE_STYLE_MAP: dict[str, list[str]] = {
    "fashion": ["editorial", "ugc"],
    "food": ["minimal", "ugc"],
    "tech": ["cinematic", "minimal"],
    "fitness": ["ugc", "cinematic"],
    "beauty": ["editorial", "minimal"],
    "travel": ["cinematic", "editorial"],
}

_PLATFORM_VISUAL_MAP: dict[str, float] = {
    "shorts": 0.90,
    "reels": 0.88,
    "tiktok": 0.86,
    "youtube": 0.80,
    "instagram": 0.82,
}

_GOAL_RELEVANCE_BOOST: dict[str, float] = {
    "conversion": 0.12,
    "awareness": 0.08,
    "engagement": 0.06,
    "retention": 0.05,
}


def _niche_style_score(niche: str | None, style_label: str) -> float:
    """Return a [0, 1] score for how well a style fits the niche."""
    niche_key = (niche or "").lower()
    preferred = _NICHE_STYLE_MAP.get(niche_key, [])
    if not preferred:
        return 0.70  # neutral when niche is unknown
    if style_label in preferred:
        idx_bonus = 1.0 - (preferred.index(style_label) * 0.05)
        return min(0.95, 0.80 + idx_bonus * 0.10)
    return 0.62


def _market_locale_score(market_code: str | None) -> float:
    """Higher score when market/locale is specified (signals real targeting)."""
    if not market_code:
        return 0.65
    # Longer / more-specific locale strings get marginally higher score
    return min(0.92, 0.70 + len(market_code) * 0.02)


def _visual_hook_score(style_label: str, content_goal: str | None) -> float:
    """Visual hook strength based on style and campaign goal."""
    goal_key = (content_goal or "engagement").lower()
    base = _PLATFORM_VISUAL_MAP.get(style_label, 0.72)
    boost = _GOAL_RELEVANCE_BOOST.get(goal_key, 0.05)
    return min(0.96, base + boost)


def _relevance_score(topic: str, niche: str | None, content_goal: str | None) -> float:
    """Relevance is driven by topic length/specificity + goal alignment."""
    topic_specificity = min(0.20, len(topic.strip()) * 0.008)
    base = 0.68 + topic_specificity
    goal_boost = _GOAL_RELEVANCE_BOOST.get((content_goal or "").lower(), 0.04)
    return min(0.96, base + goal_boost)


class TrendImageEngine:
    DEFAULT_STYLES = ("editorial", "ugc", "cinematic", "minimal")

    def generate(self, req: TrendImageRequest, db=None) -> TrendImageResponse:
        """Generate trend image concepts. If ``db`` (SQLAlchemy Session) is
        provided the run is persisted in ``creative_engine_runs``."""
        run_record = None
        if db is not None:
            from app.models.creative_engine_run import CreativeEngineRun
            run_record = CreativeEngineRun(
                engine_type="trend_image",
                status="running",
                input_payload=req.model_dump(),
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

        try:
            result = self._generate_internal(req)
            if run_record is not None:
                run_record.status = "completed"
                run_record.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                run_record.candidates = [c.model_dump() for c in result.candidates]
                run_record.winner_candidate_id = result.recommended_winner_id
                run_record.output_payload = result.model_dump()
                db.add(run_record)
                db.commit()
                result.run_id = run_record.id  # type: ignore[attr-defined]
            return result
        except Exception as exc:
            if run_record is not None:
                run_record.status = "failed"
                run_record.error_message = str(exc)
                run_record.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                db.add(run_record)
                db.commit()
            raise

    def _generate_internal(self, req: TrendImageRequest) -> TrendImageResponse:
        concepts: list[TrendImageConcept] = []
        candidates: list[CandidateScore] = []
        style = req.style_preset

        for idx in range(req.count):
            style_label = style or self.DEFAULT_STYLES[idx % len(self.DEFAULT_STYLES)]
            concept_id = str(uuid.uuid4())

            # --- input-driven scores (no idx dependency) ---
            relevance = _relevance_score(req.topic, req.niche, req.content_goal)
            trend_fit = _niche_style_score(req.niche, style_label)
            market_fit = _market_locale_score(req.market_code)
            visual_strength = _visual_hook_score(style_label, req.content_goal)

            # Style variation: use a hash of (concept_id, style_label) for
            # deterministic jitter in range [0, +0.099] so multiple concepts
            # of the same style don't all get identical scores, without relying on idx.
            jitter = (hash(style_label + concept_id) % 100) / 1000.0  # [0, 0.099]
            relevance = round(min(0.99, max(0.50, relevance + jitter * 0.5)), 3)
            trend_fit = round(min(0.99, max(0.50, trend_fit + jitter * 0.3)), 3)
            market_fit = round(min(0.99, max(0.50, market_fit + jitter * 0.2)), 3)
            visual_strength = round(min(0.99, max(0.50, visual_strength + jitter * 0.4)), 3)

            total = round(
                (relevance * _SCORE_WEIGHTS["relevance"])
                + (trend_fit * _SCORE_WEIGHTS["trend_fit"])
                + (market_fit * _SCORE_WEIGHTS["market_fit"])
                + (visual_strength * _SCORE_WEIGHTS["visual_strength"]),
                3,
            )

            # thumbnail_bias derived from visual hook, not from position
            thumbnail_bias = round(min(0.99, visual_strength * 0.9 + market_fit * 0.1), 3)

            concepts.append(
                TrendImageConcept(
                    concept_id=concept_id,
                    title=f"{req.topic.title()} Concept {idx + 1}",
                    prompt_text=self._build_prompt(req, style_label, idx + 1),
                    style_label=style_label,
                    trend_score=trend_fit,
                    thumbnail_bias=thumbnail_bias,
                    metadata={"niche": req.niche, "market_code": req.market_code, "rank": idx + 1},
                )
            )
            candidates.append(
                CandidateScore(
                    candidate_id=concept_id,
                    score_total=total,
                    score_breakdown={
                        "relevance": relevance,
                        "trend_fit": trend_fit,
                        "market_fit": market_fit,
                        "visual_strength": visual_strength,
                    },
                    rationale=(
                        f"Scored by niche-style fit ({req.niche or 'general'}), "
                        f"locale targeting ({req.market_code or 'unset'}), "
                        f"visual hook ({style_label}), "
                        f"campaign goal ({req.content_goal or 'engagement'})."
                    ),
                    metadata={"style_label": style_label},
                )
            )

        winner = max(candidates, key=lambda c: c.score_total, default=None)
        if winner:
            winner.winner_flag = True

        return TrendImageResponse(
            concepts=concepts,
            recommended_winner_id=winner.candidate_id if winner else None,
            candidates=candidates,
        )

    @staticmethod
    def _build_prompt(req: TrendImageRequest, style_label: str, rank: int) -> str:
        niche = req.niche or "general"
        goal = req.content_goal or "engagement"
        return (
            f"High-performing thumbnail concept for {req.topic} in {niche} niche, "
            f"style {style_label}, optimized for {goal}, variation {rank}."
        )

    @staticmethod
    def score_weights() -> dict[str, Any]:
        """Expose scoring weights for audit / QA inspection."""
        return dict(_SCORE_WEIGHTS)
