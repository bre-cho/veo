from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.repositories.creator_economy_repo import CreatorEconomyRepo

_repo = CreatorEconomyRepo()


class PayoutService:
    def request_payout(self, db: Session, creator_id: str, amount_usd: float) -> dict:
        total_pending = sum(
            float(e.amount_usd) for e in _repo.pending_earnings(db, creator_id)
        )
        if amount_usd > total_pending:
            return {
                "creator_id": creator_id,
                "amount_usd": amount_usd,
                "status": "insufficient_balance",
                "reference_id": None,
            }
        paid_count = _repo.mark_paid(db, creator_id, amount_usd)
        reference_id = str(uuid.uuid4())
        return {
            "creator_id": creator_id,
            "amount_usd": amount_usd,
            "status": "requested",
            "reference_id": reference_id,
        }
