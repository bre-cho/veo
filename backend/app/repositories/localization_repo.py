from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarMarketFit, AvatarTemplateFit, LocalizationProfile


class LocalizationRepo:
    def get_profile(self, db: Session, market_code: str) -> Optional[LocalizationProfile]:
        return (
            db.query(LocalizationProfile)
            .filter(LocalizationProfile.market_code == market_code)
            .first()
        )

    def list_profiles(self, db: Session) -> list[LocalizationProfile]:
        return db.query(LocalizationProfile).order_by(LocalizationProfile.country_name).all()

    def upsert_profile(self, db: Session, market_code: str, data: dict) -> LocalizationProfile:
        row = self.get_profile(db, market_code)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = LocalizationProfile(market_code=market_code, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    # --- AvatarMarketFit ---

    def get_market_fit(self, db: Session, avatar_id: str, market_code: str) -> Optional[AvatarMarketFit]:
        return (
            db.query(AvatarMarketFit)
            .filter(
                AvatarMarketFit.avatar_id == avatar_id,
                AvatarMarketFit.market_code == market_code,
            )
            .first()
        )

    def list_market_fits(self, db: Session, avatar_id: str) -> list[AvatarMarketFit]:
        return (
            db.query(AvatarMarketFit)
            .filter(AvatarMarketFit.avatar_id == avatar_id)
            .all()
        )

    def upsert_market_fit(
        self, db: Session, avatar_id: str, market_code: str, data: dict
    ) -> AvatarMarketFit:
        row = self.get_market_fit(db, avatar_id, market_code)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = AvatarMarketFit(avatar_id=avatar_id, market_code=market_code, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def avatars_for_market(
        self, db: Session, market_code: str, min_score: float = 0.5, limit: int = 20
    ) -> list[AvatarMarketFit]:
        return (
            db.query(AvatarMarketFit)
            .filter(
                AvatarMarketFit.market_code == market_code,
                AvatarMarketFit.fit_score >= min_score,
            )
            .order_by(AvatarMarketFit.fit_score.desc())
            .limit(limit)
            .all()
        )

    # --- AvatarTemplateFit ---

    def get_template_fit(
        self, db: Session, avatar_id: str, template_family_id: str
    ) -> Optional[AvatarTemplateFit]:
        return (
            db.query(AvatarTemplateFit)
            .filter(
                AvatarTemplateFit.avatar_id == avatar_id,
                AvatarTemplateFit.template_family_id == template_family_id,
            )
            .first()
        )

    def list_template_fits(self, db: Session, avatar_id: str) -> list[AvatarTemplateFit]:
        return (
            db.query(AvatarTemplateFit)
            .filter(AvatarTemplateFit.avatar_id == avatar_id)
            .order_by(AvatarTemplateFit.fit_score.desc())
            .all()
        )
