from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo

_repo = AvatarRepo()


class AvatarCloneService:
    def clone(self, db: Session, source_avatar_id: str, new_name: str | None = None, owner_user_id: str | None = None) -> dict:
        source = _repo.get_avatar(db, source_avatar_id)
        if not source:
            return {"ok": False, "error": "source_avatar_not_found"}

        clone_data = {
            "name": new_name or f"{source.name} (clone)",
            "role_id": source.role_id,
            "niche_code": source.niche_code,
            "market_code": source.market_code,
            "owner_user_id": owner_user_id or source.owner_user_id,
            "creator_id": source.creator_id,
            "tags": source.tags,
            "meta": source.meta,
            "is_published": False,
        }
        clone = _repo.create_avatar(db, clone_data)

        # Clone visual DNA if exists
        visual = _repo.get_visual(db, source_avatar_id)
        if visual:
            visual_data = {
                k: getattr(visual, k)
                for k in ["skin_tone", "hair_style", "hair_color", "eye_color",
                          "outfit_code", "background_code", "age_range",
                          "gender_expression", "accessories", "reference_image_url"]
            }
            _repo.upsert_visual(db, clone.id, visual_data)

        # Clone voice DNA if exists
        voice = _repo.get_voice(db, source_avatar_id)
        if voice:
            voice_data = {
                k: getattr(voice, k)
                for k in ["voice_profile_id", "language_code", "accent_code",
                          "tone", "pitch", "speed", "meta"]
            }
            _repo.upsert_voice(db, clone.id, voice_data)

        # Clone motion DNA if exists
        motion = _repo.get_motion(db, source_avatar_id)
        if motion:
            motion_data = {
                k: getattr(motion, k)
                for k in ["motion_style", "gesture_set", "idle_animation",
                          "lipsync_mode", "blink_rate", "meta"]
            }
            _repo.upsert_motion(db, clone.id, motion_data)

        return {"ok": True, "clone_id": clone.id, "source_id": source_avatar_id}
