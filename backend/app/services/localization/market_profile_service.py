from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import LocalizationProfile
from app.repositories.localization_repo import LocalizationRepo

_repo = LocalizationRepo()


class MarketProfileService:
    def get_profile(self, db: Session, market_code: str) -> Optional[LocalizationProfile]:
        return _repo.get_profile(db, market_code)

    def list_profiles(self, db: Session) -> list[LocalizationProfile]:
        return _repo.list_profiles(db)
