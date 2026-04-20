from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel


class MarketplaceItemCreate(BaseModel):
    avatar_id: str
    creator_id: Optional[str] = None
    price_usd: Optional[Decimal] = None
    license_type: Optional[str] = None
    is_free: bool = False
    tags: Optional[list[str]] = None


class MarketplaceItemRead(BaseModel):
    id: str
    avatar_id: str
    creator_id: Optional[str] = None
    price_usd: Optional[Decimal] = None
    license_type: Optional[str] = None
    is_free: bool
    is_active: bool
    download_count: int
    view_count: int
    rating_avg: Optional[Decimal] = None
    rating_count: int
    tags: Optional[Any] = None

    class Config:
        from_attributes = True


class AvatarListingRead(BaseModel):
    id: str
    name: str
    role_id: Optional[str] = None
    niche_code: Optional[str] = None
    market_code: Optional[str] = None
    is_published: bool
    is_featured: bool
    marketplace_item: Optional[MarketplaceItemRead] = None

    class Config:
        from_attributes = True


class MarketplaceListResponse(BaseModel):
    items: list[AvatarListingRead]
    total: int
    page: int
    page_size: int


class AvatarCollectionAdd(BaseModel):
    collection_id: str
    avatar_id: str
