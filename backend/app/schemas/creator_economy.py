from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel


class CreatorCreate(BaseModel):
    creator_id: str
    display_name: str
    bio: Optional[str] = None
    market_code: Optional[str] = None


class CreatorRead(BaseModel):
    creator_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    market_code: Optional[str] = None
    rank_score: Optional[Decimal] = None
    total_earnings_usd: Optional[Decimal] = None
    avatar_count: int = 0


class CreatorEarningsResponse(BaseModel):
    creator_id: str
    earnings: list[dict[str, Any]]
    total_usd: Decimal


class PayoutRequestIn(BaseModel):
    amount_usd: Decimal
    payout_method: Optional[str] = None


class PayoutRequestOut(BaseModel):
    creator_id: str
    amount_usd: Decimal
    status: str
    reference_id: Optional[str] = None


class CreatorStoreRead(BaseModel):
    creator_id: str
    display_name: Optional[str] = None
    avatars: list[dict[str, Any]] = []
    total_items: int = 0
