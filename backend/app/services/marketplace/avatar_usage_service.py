from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.creator_economy_repo import CreatorEconomyRepo

_repo = CreatorEconomyRepo()


class AvatarUsageService:
    def record_usage(self, db: Session, event: dict) -> dict:
        row = _repo.record_usage_event(db, event)
        return {"ok": True, "event_id": row.id}

    def track_use(self, db: Session, avatar_id: str, user_id: str | None = None) -> dict:
        event = {
            "avatar_id": avatar_id,
            "user_id": user_id,
            "event_type": "use",
        }
        row = _repo.record_usage_event(db, event)
        return {"ok": True, "event_id": row.id, "avatar_id": avatar_id}
