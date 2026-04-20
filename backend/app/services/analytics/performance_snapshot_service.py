from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.repositories.analytics_repo import AnalyticsRepo
from app.repositories.creator_economy_repo import CreatorEconomyRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_analytics_repo = AnalyticsRepo()
_economy_repo = CreatorEconomyRepo()
_mp_repo = MarketplaceRepo()


class PerformanceSnapshotService:
    def capture(self, db: Session, avatar_id: str) -> dict:
        today = date.today()
        item = _mp_repo.get_item_by_avatar(db, avatar_id)
        uses_count = _economy_repo.count_usage(db, avatar_id, days=1)

        data = {
            "views_count": item.view_count if item else 0,
            "uses_count": uses_count,
            "downloads_count": item.download_count if item else 0,
            "earnings_usd": 0,
        }
        snapshot = _analytics_repo.upsert_snapshot(db, avatar_id, today, data)
        return {"ok": True, "snapshot_id": snapshot.id, "date": today.isoformat()}

    def get_recent(self, db: Session, avatar_id: str, days: int = 30) -> list[dict]:
        snapshots = _analytics_repo.recent_snapshots(db, avatar_id, days=days)
        return [
            {
                "id": s.id,
                "avatar_id": s.avatar_id,
                "snapshot_date": s.snapshot_date.isoformat(),
                "views_count": s.views_count,
                "uses_count": s.uses_count,
                "downloads_count": s.downloads_count,
                "earnings_usd": float(s.earnings_usd),
            }
            for s in snapshots
        ]
