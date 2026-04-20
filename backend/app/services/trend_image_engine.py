from __future__ import annotations

import uuid

from app.schemas.scoring import CandidateScore
from app.schemas.trend_image import TrendImageConcept, TrendImageRequest, TrendImageResponse


class TrendImageEngine:
    DEFAULT_STYLES = ("editorial", "ugc", "cinematic", "minimal")

    def generate(self, req: TrendImageRequest) -> TrendImageResponse:
        concepts: list[TrendImageConcept] = []
        candidates: list[CandidateScore] = []
        style = req.style_preset

        for idx in range(req.count):
            style_label = style or self.DEFAULT_STYLES[idx % len(self.DEFAULT_STYLES)]
            trend_score = round(max(0.45, 0.92 - (idx * 0.08)), 3)
            thumbnail_bias = round(0.55 + (idx * 0.07), 3)
            concept_id = str(uuid.uuid4())
            concepts.append(
                TrendImageConcept(
                    concept_id=concept_id,
                    title=f"{req.topic.title()} Concept {idx + 1}",
                    prompt_text=self._build_prompt(req, style_label, idx + 1),
                    style_label=style_label,
                    trend_score=trend_score,
                    thumbnail_bias=min(thumbnail_bias, 0.99),
                    metadata={"niche": req.niche, "market_code": req.market_code, "rank": idx + 1},
                )
            )

            relevance = round(max(0.5, 0.88 - (idx * 0.04)), 3)
            trend_fit = trend_score
            market_fit = round(max(0.48, 0.84 - (idx * 0.05)), 3)
            visual_strength = round(max(0.52, 0.9 - (idx * 0.05)), 3)
            total = round((relevance * 0.28) + (trend_fit * 0.3) + (market_fit * 0.2) + (visual_strength * 0.22), 3)
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
                    rationale="Ranked by relevance/trend/market/visual scoring matrix.",
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
