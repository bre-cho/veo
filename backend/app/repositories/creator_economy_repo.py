from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarUsageEvent, CreatorEarning


class CreatorEconomyRepo:
    def list_earnings(
        self,
        db: Session,
        creator_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorEarning]:
        return (
            db.query(CreatorEarning)
            .filter(CreatorEarning.creator_id == creator_id)
            .order_by(CreatorEarning.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def create_earning(self, db: Session, data: dict) -> CreatorEarning:
        row = CreatorEarning(**data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def total_earnings(self, db: Session, creator_id: str) -> float:
        from sqlalchemy import func

        result = (
            db.query(func.sum(CreatorEarning.amount_usd))
            .filter(CreatorEarning.creator_id == creator_id)
            .scalar()
        )
        return float(result or 0)

    def pending_earnings(self, db: Session, creator_id: str) -> list[CreatorEarning]:
        return (
            db.query(CreatorEarning)
            .filter(
                CreatorEarning.creator_id == creator_id,
                CreatorEarning.payout_status == "pending",
            )
            .all()
        )

    def mark_paid(self, db: Session, creator_id: str, amount_usd: float) -> int:
        rows = self.pending_earnings(db, creator_id)
        remaining = amount_usd
        paid = 0
        for row in rows:
            if remaining <= 0:
                break
            row.payout_status = "paid"
            remaining -= float(row.amount_usd)
            paid += 1
        db.commit()
        return paid

    # --- AvatarUsageEvent ---

    def record_usage_event(self, db: Session, data: dict) -> AvatarUsageEvent:
        event = AvatarUsageEvent(**data)
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def list_usage_events(
        self,
        db: Session,
        avatar_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AvatarUsageEvent]:
        q = db.query(AvatarUsageEvent)
        if avatar_id:
            q = q.filter(AvatarUsageEvent.avatar_id == avatar_id)
        if user_id:
            q = q.filter(AvatarUsageEvent.user_id == user_id)
        return q.order_by(AvatarUsageEvent.occurred_at.desc()).limit(limit).all()

    def count_usage(self, db: Session, avatar_id: str, days: int = 7) -> int:
        from datetime import datetime, timedelta, timezone

        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        return (
            db.query(AvatarUsageEvent)
            .filter(
                AvatarUsageEvent.avatar_id == avatar_id,
                AvatarUsageEvent.occurred_at >= since,
            )
            .count()
        )
