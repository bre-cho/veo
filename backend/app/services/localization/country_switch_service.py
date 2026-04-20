from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.localization_repo import LocalizationRepo

_repo = LocalizationRepo()


class CountrySwitchService:
    def switch_country(self, db: Session, market_code: str) -> dict:
        profile = _repo.get_profile(db, market_code)
        if not profile:
            return {
                "market_code": market_code,
                "country_name": market_code.upper(),
                "language_code": None,
                "currency_code": None,
                "rtl": False,
                "status": "switched_no_profile",
            }
        return {
            "market_code": profile.market_code,
            "country_name": profile.country_name,
            "language_code": profile.language_code,
            "currency_code": profile.currency_code,
            "rtl": profile.rtl,
            "status": "switched",
        }
