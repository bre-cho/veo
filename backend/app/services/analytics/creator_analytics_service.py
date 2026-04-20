from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo
from app.repositories.creator_economy_repo import CreatorEconomyRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_avatar_repo = AvatarRepo()
_economy_repo = CreatorEconomyRepo()
_mp_repo = MarketplaceRepo()


class CreatorAnalyticsService:
    def get_creator_dashboard(self, db: Session, creator_id: str) -> dict:
        all_avatars = _avatar_repo.list_avatars(db, limit=1000)
        creator_avatars = [a for a in all_avatars if a.creator_id == creator_id]
        total_earnings = _economy_repo.total_earnings(db, creator_id)
        ranking = _mp_repo.get_creator_ranking(db, creator_id)

        top_avatars = []
        for avatar in creator_avatars[:5]:
            item = _mp_repo.get_item_by_avatar(db, avatar.id)
            top_avatars.append({
                "id": avatar.id,
                "name": avatar.name,
                "download_count": item.download_count if item else 0,
            })

        return {
            "creator_id": creator_id,
            "total_avatars": len(creator_avatars),
            "total_earnings_usd": total_earnings,
            "rank_score": float(ranking.rank_score) if ranking else None,
            "top_avatars": top_avatars,
        }
