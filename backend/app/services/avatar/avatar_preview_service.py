from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo
from app.services.avatar.avatar_identity_service import AvatarIdentityService

_repo = AvatarRepo()
_identity_svc = AvatarIdentityService()


class AvatarPreviewService:
    def preview_static(
        self,
        db: Session,
        avatar_id: str,
        output_traits: dict[str, Any] | None = None,
    ) -> dict:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            return {"ok": False, "error": "avatar_not_found"}
        preview_url = f"/storage/avatars/{avatar_id}/preview_static.png"
        result: dict[str, Any] = {
            "ok": True,
            "avatar_id": avatar_id,
            "preview_url": preview_url,
            "mode": "static",
        }
        # Drift detection: check consistency when output_traits are provided
        if output_traits:
            consistency = _identity_svc.score_consistency(db, avatar_id, output_traits)
            result["consistency"] = consistency
            if consistency.get("should_reject"):
                result["ok"] = False
                result["rejected"] = True
                result["rejection_reason"] = "avatar_drift_detected"
                result["drift_flags"] = consistency.get("drift_flags", [])
        return result

    def preview_animated(
        self,
        db: Session,
        avatar_id: str,
        script_text: str | None = None,
        output_traits: dict[str, Any] | None = None,
    ) -> dict:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            return {"ok": False, "error": "avatar_not_found"}
        preview_url = f"/storage/avatars/{avatar_id}/preview_animated.mp4"
        result: dict[str, Any] = {
            "ok": True,
            "avatar_id": avatar_id,
            "preview_url": preview_url,
            "mode": "animated",
        }
        # Drift detection
        if output_traits:
            consistency = _identity_svc.score_consistency(db, avatar_id, output_traits)
            result["consistency"] = consistency
            if consistency.get("should_reject"):
                result["ok"] = False
                result["rejected"] = True
                result["rejection_reason"] = "avatar_drift_detected"
                result["drift_flags"] = consistency.get("drift_flags", [])
        return result

    def get_identity_vector(self, db: Session, avatar_id: str) -> dict[str, Any]:
        """Return the avatar's identity vector for downstream systems."""
        return _identity_svc.get_identity_vector(db, avatar_id)

    def get_reference_frames(self, avatar_id: str) -> list[dict[str, Any]]:
        """Return canonical reference frames for the avatar."""
        return _identity_svc.get_reference_frames(avatar_id)
