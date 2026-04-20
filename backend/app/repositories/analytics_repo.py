from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import PerformanceSnapshot


class AnalyticsRepo:
    def get_snapshot(
        self, db: Session, avatar_id: str, snapshot_date: date
    ) -> Optional[PerformanceSnapshot]:
        return (
            db.query(PerformanceSnapshot)
            .filter(
                PerformanceSnapshot.avatar_id == avatar_id,
                PerformanceSnapshot.snapshot_date == snapshot_date,
            )
            .first()
        )

    def upsert_snapshot(
        self, db: Session, avatar_id: str, snapshot_date: date, data: dict
    ) -> PerformanceSnapshot:
        row = self.get_snapshot(db, avatar_id, snapshot_date)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = PerformanceSnapshot(avatar_id=avatar_id, snapshot_date=snapshot_date, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def recent_snapshots(
        self, db: Session, avatar_id: str, days: int = 30
    ) -> list[PerformanceSnapshot]:
        since = date.today() - timedelta(days=days)
        return (
            db.query(PerformanceSnapshot)
            .filter(
                PerformanceSnapshot.avatar_id == avatar_id,
                PerformanceSnapshot.snapshot_date >= since,
            )
            .order_by(PerformanceSnapshot.snapshot_date.desc())
            .all()
        )

    def aggregate_totals(self, db: Session, avatar_id: str) -> dict:
        from sqlalchemy import func

        row = (
            db.query(
                func.sum(PerformanceSnapshot.views_count).label("views"),
                func.sum(PerformanceSnapshot.uses_count).label("uses"),
                func.sum(PerformanceSnapshot.downloads_count).label("downloads"),
                func.sum(PerformanceSnapshot.earnings_usd).label("earnings"),
            )
            .filter(PerformanceSnapshot.avatar_id == avatar_id)
            .one()
        )
        return {
            "total_views": int(row.views or 0),
            "total_uses": int(row.uses or 0),
            "total_downloads": int(row.downloads or 0),
            "total_earnings_usd": float(row.earnings or 0),
        }
