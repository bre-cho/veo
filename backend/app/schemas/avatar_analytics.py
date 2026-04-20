from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel


class PerformanceSnapshotRead(BaseModel):
    id: str
    avatar_id: str
    snapshot_date: date
    views_count: int
    uses_count: int
    downloads_count: int
    earnings_usd: Decimal
    conversion_rate: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class AvatarAnalyticsDashboard(BaseModel):
    avatar_id: str
    total_views: int
    total_uses: int
    total_downloads: int
    total_earnings_usd: Decimal
    rank_score: Optional[Decimal] = None
    trending_score: Optional[Decimal] = None
    recent_snapshots: list[PerformanceSnapshotRead] = []


class CreatorAnalyticsDashboard(BaseModel):
    creator_id: str
    total_avatars: int
    total_earnings_usd: Decimal
    rank_score: Optional[Decimal] = None
    top_avatars: list[dict[str, Any]] = []


class TemplateAnalyticsDashboard(BaseModel):
    template_family_id: str
    name: str
    content_goal: Optional[str] = None
    avatar_fit_count: int
    usage_count: int


class MarketplaceTrendingResponse(BaseModel):
    trending: list[dict[str, Any]]
    period: str = "7d"
