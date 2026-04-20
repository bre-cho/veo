from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo

_repo = AvatarRepo()


class AvatarPublishService:
    def publish(self, db: Session, avatar_id: str) -> dict:
        avatar = _repo.update_avatar(db, avatar_id, {"is_published": True})
        if not avatar:
            return {"ok": False, "error": "avatar_not_found"}
        return {"ok": True, "avatar_id": avatar_id, "status": "published"}

    def unpublish(self, db: Session, avatar_id: str) -> dict:
        avatar = _repo.update_avatar(db, avatar_id, {"is_published": False})
        if not avatar:
            return {"ok": False, "error": "avatar_not_found"}
        return {"ok": True, "avatar_id": avatar_id, "status": "unpublished"}
