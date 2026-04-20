from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo

_repo = AvatarRepo()


class AvatarPreviewService:
    def preview_static(self, db: Session, avatar_id: str) -> dict:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            return {"ok": False, "error": "avatar_not_found"}
        preview_url = f"/storage/avatars/{avatar_id}/preview_static.png"
        return {"ok": True, "avatar_id": avatar_id, "preview_url": preview_url, "mode": "static"}

    def preview_animated(self, db: Session, avatar_id: str, script_text: str | None = None) -> dict:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            return {"ok": False, "error": "avatar_not_found"}
        preview_url = f"/storage/avatars/{avatar_id}/preview_animated.mp4"
        return {"ok": True, "avatar_id": avatar_id, "preview_url": preview_url, "mode": "animated"}
