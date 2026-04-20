from __future__ import annotations

_LICENSED_AVATARS: set[str] = set()  # In production, query license table


class LicensingService:
    def check_license(self, avatar_id: str, user_id: str) -> dict:
        # Placeholder: in production, query a licenses table
        is_licensed = avatar_id in _LICENSED_AVATARS
        return {
            "avatar_id": avatar_id,
            "user_id": user_id,
            "licensed": is_licensed,
            "license_type": "standard" if is_licensed else None,
        }

    def grant_license(self, avatar_id: str, user_id: str) -> dict:
        _LICENSED_AVATARS.add(avatar_id)
        return {"avatar_id": avatar_id, "user_id": user_id, "licensed": True}
