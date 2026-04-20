from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import TemplateFamily
from app.services.commerce.content_goal_classifier import ContentGoalClassifier

_classifier = ContentGoalClassifier()


class ProductToTemplateRouter:
    def route(self, db: Session, product_brief: str, market_code: Optional[str] = None) -> dict:
        content_goal = _classifier.classify(product_brief)

        q = db.query(TemplateFamily).filter(
            TemplateFamily.is_active.is_(True),
            TemplateFamily.content_goal == content_goal,
        )
        if market_code:
            # Filter by market_codes JSON if available (best effort)
            families = q.all()
            market_families = [
                f for f in families
                if f.market_codes and market_code in (f.market_codes or [])
            ]
            family = market_families[0] if market_families else (families[0] if families else None)
        else:
            family = q.first()

        if family:
            return {
                "template_family_id": family.id,
                "template_name": family.name,
                "content_goal": content_goal,
                "rationale": f"Matched '{content_goal}' goal for brief keywords.",
            }

        return {
            "template_family_id": None,
            "template_name": None,
            "content_goal": content_goal,
            "rationale": f"No template found for '{content_goal}' – create one in Template Studio.",
        }
