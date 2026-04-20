from __future__ import annotations

from app.schemas.channel import ChannelPlanRequest
from app.services.channel_engine import ChannelEngine
from app.services.publish_scheduler import PublishScheduler


def test_build_7_day_plan() -> None:
    engine = ChannelEngine()
    result = engine.generate_plan(ChannelPlanRequest(niche="fitness", days=7))
    assert len(result.series_plan) == 7


def test_build_publish_queue() -> None:
    engine = ChannelEngine()
    scheduler = PublishScheduler()
    result = engine.generate_plan(ChannelPlanRequest(niche="fitness", days=7))
    queue = scheduler.build_publish_queue([item.model_dump() for item in result.series_plan])
    assert queue


def test_queue_count_matches_plan_items() -> None:
    engine = ChannelEngine()
    scheduler = PublishScheduler()
    result = engine.generate_plan(ChannelPlanRequest(niche="fitness", days=7, posts_per_day=2))
    queue = scheduler.build_publish_queue([item.model_dump() for item in result.series_plan])
    assert len(queue) == len(result.series_plan)
