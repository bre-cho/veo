from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.avatar_repo import AvatarRepo
from app.services.marketplace.avatar_listing_service import AvatarListingService
from app.services.marketplace.avatar_usage_service import AvatarUsageService
from app.services.marketplace.marketplace_service import MarketplaceService

router = APIRouter(prefix="/api/v1", tags=["marketplace"])

_mp_service = MarketplaceService()
_listing_service = AvatarListingService()
_usage_service = AvatarUsageService()
_avatar_repo = AvatarRepo()


@router.get("/avatars")
def list_avatars(
    market_code: Optional[str] = None,
    niche_code: Optional[str] = None,
    role_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    items = _mp_service.list_avatars(db, market_code=market_code, niche_code=niche_code, role_id=role_id, limit=limit, offset=offset)
    return {"items": items, "total": len(items), "page": offset // limit + 1, "page_size": limit}


@router.get("/avatars/recommended")
def recommended_avatars(limit: int = 10, db: Session = Depends(get_db)):
    return {"items": _listing_service.recommended(db, limit=limit)}


@router.get("/avatars/trending")
def trending_avatars(limit: int = 10, db: Session = Depends(get_db)):
    return {"items": _listing_service.trending(db, limit=limit)}


@router.get("/avatars/recently-used")
def recently_used_avatars(user_id: Optional[str] = None, limit: int = 10, db: Session = Depends(get_db)):
    from app.repositories.creator_economy_repo import CreatorEconomyRepo
    _eco_repo = CreatorEconomyRepo()
    events = _eco_repo.list_usage_events(db, user_id=user_id, limit=limit)
    seen = []
    result = []
    for event in events:
        if event.avatar_id not in seen:
            seen.append(event.avatar_id)
            avatar = _avatar_repo.get_avatar(db, event.avatar_id)
            if avatar:
                result.append({"id": avatar.id, "name": avatar.name, "niche_code": avatar.niche_code})
    return {"items": result}


@router.get("/avatars/{avatar_id}")
def get_avatar(avatar_id: str, db: Session = Depends(get_db)):
    avatar = _avatar_repo.get_avatar(db, avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return {"id": avatar.id, "name": avatar.name, "role_id": avatar.role_id, "niche_code": avatar.niche_code, "market_code": avatar.market_code, "is_published": avatar.is_published}


@router.post("/avatars/{avatar_id}/use")
def use_avatar(avatar_id: str, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    return _usage_service.track_use(db, avatar_id, user_id)


@router.post("/avatars/{avatar_id}/add-to-collection")
def add_to_collection(avatar_id: str, collection_id: str, db: Session = Depends(get_db)):
    result = _avatar_repo.add_avatar_to_collection(db, collection_id, avatar_id)
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"ok": True, "collection_id": collection_id, "avatar_id": avatar_id}
