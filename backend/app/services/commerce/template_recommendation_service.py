from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.autovis import TemplateFamily
from app.repositories.localization_repo import LocalizationRepo

_loc_repo = LocalizationRepo()


class TemplateRecommendationService:
    def recommend(
        self,
        db: Session,
        avatar_id: str,
        content_goal: str,
        limit: int = 5,
    ) -> list[dict]:
        # Find template fits for this avatar
        fits = _loc_repo.list_template_fits(db, avatar_id)
        if fits:
            results = []
            for fit in fits[:limit]:
                family = db.query(TemplateFamily).filter(TemplateFamily.id == fit.template_family_id).first()
                if family and family.is_active:
                    results.append({
                        "template_family_id": family.id,
                        "name": family.name,
                        "content_goal": family.content_goal,
                        "fit_score": float(fit.fit_score or 0),
                    })
            if results:
                return results

        # Fall back to content_goal based
        families = (
            db.query(TemplateFamily)
            .filter(
                TemplateFamily.is_active.is_(True),
                TemplateFamily.content_goal == content_goal,
            )
            .limit(limit)
            .all()
        )
        return [
            {
                "template_family_id": f.id,
                "name": f.name,
                "content_goal": f.content_goal,
                "fit_score": None,
            }
            for f in families
        ]
