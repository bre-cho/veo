from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.analytics_repo import AnalyticsRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_analytics_repo = AnalyticsRepo()
_mp_repo = MarketplaceRepo()


class AvatarAnalyticsService:
    def get_avatar_dashboard(self, db: Session, avatar_id: str) -> dict:
        totals = _analytics_repo.aggregate_totals(db, avatar_id)
        recent = _analytics_repo.recent_snapshots(db, avatar_id, days=30)
        ranking = _mp_repo.get_avatar_ranking(db, avatar_id)

        return {
            "avatar_id": avatar_id,
            **totals,
            "rank_score": float(ranking.rank_score) if ranking else None,
            "trending_score": float(ranking.trending_score) if ranking else None,
            "recent_snapshots": [
                {
                    "id": s.id,
                    "avatar_id": s.avatar_id,
                    "snapshot_date": s.snapshot_date.isoformat(),
                    "views_count": s.views_count,
                    "uses_count": s.uses_count,
                    "downloads_count": s.downloads_count,
                    "earnings_usd": float(s.earnings_usd),
                    "conversion_rate": float(s.conversion_rate) if s.conversion_rate else None,
                }
                for s in recent
            ],
        }
