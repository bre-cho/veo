from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo
from app.repositories.creator_economy_repo import CreatorEconomyRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_avatar_repo = AvatarRepo()
_economy_repo = CreatorEconomyRepo()
_mp_repo = MarketplaceRepo()


class CreatorStoreService:
    def get_store(self, db: Session, creator_id: str) -> dict:
        avatars = _avatar_repo.list_avatars(db, published_only=True, limit=100)
        creator_avatars = [a for a in avatars if a.creator_id == creator_id]
        total_earnings = _economy_repo.total_earnings(db, creator_id)
        ranking = _mp_repo.get_creator_ranking(db, creator_id)

        return {
            "creator_id": creator_id,
            "avatars": [
                {"id": a.id, "name": a.name, "niche_code": a.niche_code}
                for a in creator_avatars
            ],
            "total_items": len(creator_avatars),
            "total_earnings_usd": total_earnings,
            "rank_score": float(ranking.rank_score) if ranking else 0.0,
        }
