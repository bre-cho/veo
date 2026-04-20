from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories.marketplace_repo import MarketplaceRepo
from app.schemas.creator_economy import (
    CreatorCreate,
    CreatorEarningsResponse,
    PayoutRequestIn,
    PayoutRequestOut,
)
from app.services.economy.creator_earning_service import CreatorEarningService
from app.services.economy.payout_service import PayoutService
from app.services.marketplace.creator_store_service import CreatorStoreService

router = APIRouter(prefix="/api/v1", tags=["creator-economy"])

_earning_service = CreatorEarningService()
_payout_service = PayoutService()
_store_service = CreatorStoreService()
_mp_repo = MarketplaceRepo()


@router.post("/creators")
def create_creator(req: CreatorCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    profile = _mp_repo.upsert_creator_profile(
        db,
        creator_id=req.creator_id,
        user_id=str(current_user.id),
        display_name=req.display_name,
        bio=req.bio,
        market_code=req.market_code,
    )
    ranking = _mp_repo.upsert_creator_ranking(
        db,
        req.creator_id,
        {"avatar_count": 0},
    )
    return {
        "ok": True,
        "creator": {
            "creator_id": profile.creator_id,
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "bio": profile.bio,
            "market_code": profile.market_code,
        },
        "ranking": {
            "creator_id": ranking.creator_id,
            "rank_score": float(ranking.rank_score),
            "total_earnings_usd": float(ranking.total_earnings_usd),
            "avatar_count": ranking.avatar_count,
        },
    }


@router.get("/creators/top")
def top_creators(limit: int = 10, db: Session = Depends(get_db)):
    rankings = _mp_repo.top_creators(db, limit=limit)
    return {
        "creators": [
            {
                "creator_id": r.creator_id,
                "rank_score": float(r.rank_score),
                "total_earnings_usd": float(r.total_earnings_usd),
                "avatar_count": r.avatar_count,
            }
            for r in rankings
        ]
    }


@router.get("/creators/{creator_id}")
def get_creator(creator_id: str, db: Session = Depends(get_db)):
    profile = _mp_repo.get_creator_profile(db, creator_id)
    ranking = _mp_repo.get_creator_ranking(db, creator_id)
    return {
        "creator_id": creator_id,
        "display_name": profile.display_name if profile else None,
        "bio": profile.bio if profile else None,
        "market_code": profile.market_code if profile else None,
        "rank_score": float(ranking.rank_score) if ranking else 0.0,
        "total_earnings_usd": float(ranking.total_earnings_usd) if ranking else 0.0,
        "avatar_count": ranking.avatar_count if ranking else 0,
    }


@router.get("/creators/{creator_id}/store")
def get_creator_store(creator_id: str, db: Session = Depends(get_db)):
    return _store_service.get_store(db, creator_id)


@router.get("/creators/{creator_id}/earnings")
def get_creator_earnings(creator_id: str, db: Session = Depends(get_db)):
    return _earning_service.list_earnings(db, creator_id)


@router.post("/creators/{creator_id}/request-payout", response_model=PayoutRequestOut)
def request_payout(
    creator_id: str,
    req: PayoutRequestIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not _mp_repo.is_creator_owner(db, creator_id=creator_id, user_id=str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not allowed for this creator")
    result = _payout_service.request_payout(db, creator_id, float(req.amount_usd))
    return PayoutRequestOut(**result)
