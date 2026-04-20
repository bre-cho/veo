from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.channel_plan import ChannelPlan
from app.schemas.channel import ChannelPlanItem, ChannelPlanRequest, ChannelPlanResponse
from app.schemas.scoring import CandidateScore


class ChannelEngine:
    DEFAULT_FORMATS = ("short", "carousel", "talking_head")

    def generate_plan(self, req: ChannelPlanRequest) -> ChannelPlanResponse:
        candidates_with_plans = self._build_candidates(req)
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
            response = self.generate_plan(req)
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

    def _build_candidates(self, req: ChannelPlanRequest) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        candidate_formats = [
            list(req.formats or self.DEFAULT_FORMATS),
            list(reversed(req.formats or self.DEFAULT_FORMATS)),
            [self.DEFAULT_FORMATS[0], self.DEFAULT_FORMATS[0], self.DEFAULT_FORMATS[-1]],
        ]
        score_profiles = [
            ("balanced", {"audience_fit": 0.82, "platform_fit": 0.8, "product_fit": 0.79, "repeatability": 0.78, "conversion_potential": 0.76}),
            ("platform_heavy", {"audience_fit": 0.78, "platform_fit": 0.88, "product_fit": 0.74, "repeatability": 0.82, "conversion_potential": 0.75}),
            ("conversion_push", {"audience_fit": 0.74, "platform_fit": 0.76, "product_fit": 0.77, "repeatability": 0.71, "conversion_potential": 0.88}),
        ]

        for idx, formats in enumerate(candidate_formats):
            variant_id, breakdown = score_profiles[idx]
            plan_items = self._build_plan_items(req, formats)
            total = round(
                (breakdown["audience_fit"] * 0.22)
                + (breakdown["platform_fit"] * 0.2)
                + (breakdown["product_fit"] * 0.2)
                + (breakdown["repeatability"] * 0.18)
                + (breakdown["conversion_potential"] * 0.2),
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
                        metadata={"variant_index": idx + 1},
                    ),
                }
            )
        return candidates

    def _build_plan_items(self, req: ChannelPlanRequest, formats: list[str]) -> list[ChannelPlanItem]:
        series_plan: list[ChannelPlanItem] = []
        for day in range(1, req.days + 1):
            for post_idx in range(req.posts_per_day):
                fmt = formats[(day + post_idx - 1) % len(formats)]
                series_plan.append(
                    ChannelPlanItem(
                        day_index=day,
                        format=fmt,
                        title_angle=f"{req.niche.title()} angle day {day} post {post_idx + 1}",
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
