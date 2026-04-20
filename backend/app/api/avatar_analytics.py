from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analytics.avatar_analytics_service import AvatarAnalyticsService
from app.services.analytics.creator_analytics_service import CreatorAnalyticsService
from app.repositories.marketplace_repo import MarketplaceRepo

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_avatar_analytics = AvatarAnalyticsService()
_creator_analytics = CreatorAnalyticsService()
_mp_repo = MarketplaceRepo()


@router.get("/avatars/{avatar_id}")
def get_avatar_analytics(avatar_id: str, db: Session = Depends(get_db)):
    return _avatar_analytics.get_avatar_dashboard(db, avatar_id)


@router.get("/creators/{creator_id}")
def get_creator_analytics(creator_id: str, db: Session = Depends(get_db)):
    return _creator_analytics.get_creator_dashboard(db, creator_id)


@router.get("/templates/{template_id}")
def get_template_analytics(template_id: str, db: Session = Depends(get_db)):
    from app.models.autovis import TemplateFamily, AvatarTemplateFit
    family = db.query(TemplateFamily).filter(TemplateFamily.id == template_id).first()
    if not family:
        return {"template_family_id": template_id, "name": None, "content_goal": None, "avatar_fit_count": 0, "usage_count": 0}
    fit_count = db.query(AvatarTemplateFit).filter(AvatarTemplateFit.template_family_id == template_id).count()
    return {
        "template_family_id": template_id,
        "name": family.name,
        "content_goal": family.content_goal,
        "avatar_fit_count": fit_count,
        "usage_count": 0,
    }


@router.get("/marketplace/trending")
def get_marketplace_trending(limit: int = 10, db: Session = Depends(get_db)):
    rankings = _mp_repo.trending_avatars(db, limit=limit)
    from app.repositories.avatar_repo import AvatarRepo
    _avatar_repo = AvatarRepo()
    trending = []
    for r in rankings:
        avatar = _avatar_repo.get_avatar(db, r.avatar_id)
        if avatar:
            trending.append({
                "avatar_id": r.avatar_id,
                "name": avatar.name,
                "trending_score": float(r.trending_score or 0),
                "usage_count_7d": r.usage_count_7d,
            })
    return {"trending": trending, "period": "7d"}
