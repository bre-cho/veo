from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.creator_economy_repo import CreatorEconomyRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_economy_repo = CreatorEconomyRepo()
_mp_repo = MarketplaceRepo()


class AvatarRankingService:
    def update_ranking(self, db: Session, avatar_id: str) -> dict:
        usage_7d = _economy_repo.count_usage(db, avatar_id, days=7)
        usage_30d = _economy_repo.count_usage(db, avatar_id, days=30)

        item = _mp_repo.get_item_by_avatar(db, avatar_id)
        download_count = item.download_count if item else 0

        # Simple scoring: trending = 7d usage * 3 + download_count, rank = 30d usage * 2 + download_count
        trending_score = usage_7d * 3 + download_count
        rank_score = usage_30d * 2 + download_count

        ranking = _mp_repo.upsert_avatar_ranking(
            db,
            avatar_id,
            {
                "usage_count_7d": usage_7d,
                "usage_count_30d": usage_30d,
                "download_count": download_count,
                "trending_score": trending_score,
                "rank_score": rank_score,
                "last_computed_at": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )
        return {
            "avatar_id": avatar_id,
            "rank_score": float(ranking.rank_score),
            "trending_score": float(ranking.trending_score),
        }
