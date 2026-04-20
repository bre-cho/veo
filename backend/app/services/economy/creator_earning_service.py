from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.creator_economy_repo import CreatorEconomyRepo

_repo = CreatorEconomyRepo()


class CreatorEarningService:
    def list_earnings(self, db: Session, creator_id: str) -> dict:
        earnings = _repo.list_earnings(db, creator_id)
        total = _repo.total_earnings(db, creator_id)
        return {
            "creator_id": creator_id,
            "earnings": [
                {
                    "id": e.id,
                    "amount_usd": float(e.amount_usd),
                    "earning_type": e.earning_type,
                    "payout_status": e.payout_status,
                    "period_start": e.period_start.isoformat() if e.period_start else None,
                    "period_end": e.period_end.isoformat() if e.period_end else None,
                }
                for e in earnings
            ],
            "total_usd": total,
        }
