from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna, LocalizationProfile
from app.repositories.localization_repo import LocalizationRepo

_repo = LocalizationRepo()


class LocalizationMatrixService:
    def get_matrix(self, db: Session) -> list[dict]:
        profiles = _repo.list_profiles(db)
        matrix = []
        for profile in profiles:
            fits = _repo.avatars_for_market(db, profile.market_code, min_score=0.0, limit=1000)
            matrix.append({
                "market_code": profile.market_code,
                "country_name": profile.country_name,
                "language_code": profile.language_code,
                "rtl": profile.rtl,
                "avatar_fit_count": len(fits),
                "preferred_niches": profile.preferred_niches or [],
            })
        return matrix
