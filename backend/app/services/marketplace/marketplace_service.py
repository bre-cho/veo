from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna, MarketplaceItem
from app.repositories.avatar_repo import AvatarRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_avatar_repo = AvatarRepo()
_mp_repo = MarketplaceRepo()


class MarketplaceService:
    def list_avatars(
        self,
        db: Session,
        market_code: Optional[str] = None,
        niche_code: Optional[str] = None,
        role_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        avatars = _avatar_repo.list_avatars(
            db,
            market_code=market_code,
            niche_code=niche_code,
            role_id=role_id,
            published_only=True,
            limit=limit,
            offset=offset,
        )
        results = []
        for avatar in avatars:
            item = _mp_repo.get_item_by_avatar(db, avatar.id)
            results.append({
                "id": avatar.id,
                "name": avatar.name,
                "role_id": avatar.role_id,
                "niche_code": avatar.niche_code,
                "market_code": avatar.market_code,
                "is_featured": avatar.is_featured,
                "marketplace_item": {
                    "id": item.id,
                    "price_usd": float(item.price_usd) if item and item.price_usd else None,
                    "is_free": item.is_free if item else True,
                    "download_count": item.download_count if item else 0,
                    "rating_avg": float(item.rating_avg) if item and item.rating_avg else None,
                } if item else None,
            })
        return results
