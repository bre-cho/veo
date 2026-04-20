from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.localization_repo import LocalizationRepo

_repo = LocalizationRepo()


class CompatibilityService:
    def check_avatar_market_fit(self, db: Session, avatar_id: str, market_code: str) -> dict:
        fit = _repo.get_market_fit(db, avatar_id, market_code)
        if not fit:
            return {
                "avatar_id": avatar_id,
                "market_code": market_code,
                "fit_score": None,
                "compatible": False,
                "notes": "No market fit data available.",
            }
        score = float(fit.fit_score or 0)
        return {
            "avatar_id": avatar_id,
            "market_code": market_code,
            "fit_score": score,
            "compatible": score >= 0.5,
            "notes": fit.notes or "",
        }
