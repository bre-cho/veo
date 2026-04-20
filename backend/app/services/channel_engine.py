from __future__ import annotations

from app.schemas.channel import ChannelPlanItem, ChannelPlanRequest, ChannelPlanResponse


class ChannelEngine:
    DEFAULT_FORMATS = ("short", "carousel", "talking_head")

    def generate_plan(self, req: ChannelPlanRequest) -> ChannelPlanResponse:
        formats = req.formats or list(self.DEFAULT_FORMATS)
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

        return ChannelPlanResponse(
            series_plan=series_plan,
            publish_queue_count=len(series_plan),
            calendar_summary={
                "days": req.days,
                "posts_per_day": req.posts_per_day,
                "total_posts": len(series_plan),
                "niche": req.niche,
            },
        )
