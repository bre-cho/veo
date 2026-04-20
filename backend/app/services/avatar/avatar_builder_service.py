from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna
from app.repositories.avatar_repo import AvatarRepo
from app.schemas.avatar_builder import AvatarBuilderStartRequest, AvatarBuilderStartResponse

_repo = AvatarRepo()


class AvatarBuilderService:
    def start(self, db: Session, req: AvatarBuilderStartRequest) -> AvatarBuilderStartResponse:
        data = {
            "name": req.name,
            "role_id": req.role_id,
            "niche_code": req.niche_code,
            "market_code": req.market_code,
            "owner_user_id": req.owner_user_id,
            "is_published": False,
        }
        avatar = _repo.create_avatar(db, data)
        return AvatarBuilderStartResponse(avatar_id=avatar.id, name=avatar.name)

    def save_dna(self, db: Session, avatar_id: str, visual: dict | None, voice: dict | None, motion: dict | None) -> dict:
        results: dict = {"avatar_id": avatar_id}
        if visual:
            _repo.upsert_visual(db, avatar_id, visual)
            results["visual"] = "saved"
        if voice:
            _repo.upsert_voice(db, avatar_id, voice)
            results["voice"] = "saved"
        if motion:
            _repo.upsert_motion(db, avatar_id, motion)
            results["motion"] = "saved"
        return results
