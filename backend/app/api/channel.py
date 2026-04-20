from __future__ import annotations

from fastapi import APIRouter

from app.schemas.channel import ChannelPlanRequest, ChannelPlanResponse
from app.services.channel_engine import ChannelEngine
from app.services.publish_scheduler import PublishScheduler

router = APIRouter(prefix="/api/v1/channel", tags=["channel"])

_engine = ChannelEngine()
_scheduler = PublishScheduler()


@router.post("/generate-plan", response_model=ChannelPlanResponse)
def generate_channel_plan(req: ChannelPlanRequest) -> ChannelPlanResponse:
    return _engine.generate_plan(req)


@router.post("/build-publish-queue")
def build_publish_queue(channel_plan: ChannelPlanResponse):
    queue = _scheduler.build_publish_queue([item.model_dump() for item in channel_plan.series_plan])
    return {"publish_jobs": queue, "publish_queue_count": len(queue)}
