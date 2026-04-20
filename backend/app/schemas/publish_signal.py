from __future__ import annotations

from pydantic import BaseModel, Field


class PublishSignalRequest(BaseModel):
    """Real-world performance metrics reported after a publish goes live.

    Callers supply whatever signals are available; omitted fields default to
    sentinels that indicate the engine should not penalise the record for
    missing data.
    """

    view_count: int = Field(default=0, ge=0, description="Total views / impressions")
    click_through_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Click-through rate [0, 1]"
    )
    conversion_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Normalised conversion signal [0, 1]"
    )
    platform: str | None = Field(default=None, description="Platform where the video went live")
    market_code: str | None = Field(default=None, description="Market / locale code")


class PublishSignalResponse(BaseModel):
    ok: bool
    job_id: str
    signal_status: str
    video_id: str
    conversion_score: float
