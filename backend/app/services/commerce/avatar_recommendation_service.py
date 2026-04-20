from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna
from app.repositories.avatar_repo import AvatarRepo
from app.repositories.localization_repo import LocalizationRepo

_avatar_repo = AvatarRepo()
_loc_repo = LocalizationRepo()

# Goal → preferred niche tags mapping
_GOAL_NICHE_MAP: dict[str, list[str]] = {
    "product_demo": ["ecommerce", "tech", "saas"],
    "brand_awareness": ["lifestyle", "fashion", "beauty"],
    "lead_generation": ["finance", "real_estate", "insurance"],
    "education": ["edtech", "health", "coaching"],
    "entertainment": ["entertainment", "gaming", "sports"],
    "sales": ["ecommerce", "retail", "cpg"],
    "testimonial": ["health", "fitness", "beauty"],
}


class AvatarRecommendationService:
    def recommend(
        self,
        db: Session,
        content_goal: str,
        niche_code: Optional[str] = None,
        market_code: Optional[str] = None,
        limit: int = 5,
    ) -> list[AvatarDna]:
        # Try market-fit based recommendation first
        if market_code:
            fits = _loc_repo.avatars_for_market(db, market_code, min_score=0.5, limit=limit * 2)
            if fits:
                avatar_ids = [f.avatar_id for f in fits]
                avatars = [_avatar_repo.get_avatar(db, aid) for aid in avatar_ids]
                avatars = [a for a in avatars if a and a.is_published]
                if avatars:
                    return avatars[:limit]

        # Fall back to niche-based recommendation
        effective_niche = niche_code
        if not effective_niche:
            preferred_niches = _GOAL_NICHE_MAP.get(content_goal, [])
            effective_niche = preferred_niches[0] if preferred_niches else None

        return _avatar_repo.list_avatars(
            db,
            niche_code=effective_niche,
            market_code=market_code,
            published_only=True,
            limit=limit,
        )
