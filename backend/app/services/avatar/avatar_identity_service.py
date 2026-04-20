from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna, AvatarMotionDna, AvatarVisualDna, AvatarVoiceDna
from app.repositories.avatar_repo import AvatarRepo

_repo = AvatarRepo()


class AvatarIdentityService:
    def upsert_identity(self, db: Session, avatar_id: str, data: dict) -> AvatarDna:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            data["id"] = avatar_id
            return _repo.create_avatar(db, data)
        return _repo.update_avatar(db, avatar_id, data)

    def upsert_visual(self, db: Session, avatar_id: str, data: dict) -> AvatarVisualDna:
        return _repo.upsert_visual(db, avatar_id, data)

    def upsert_voice(self, db: Session, avatar_id: str, data: dict) -> AvatarVoiceDna:
        return _repo.upsert_voice(db, avatar_id, data)

    def upsert_motion(self, db: Session, avatar_id: str, data: dict) -> AvatarMotionDna:
        return _repo.upsert_motion(db, avatar_id, data)
