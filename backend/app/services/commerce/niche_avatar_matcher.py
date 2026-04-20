from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna
from app.repositories.avatar_repo import AvatarRepo
from app.repositories.localization_repo import LocalizationRepo

if TYPE_CHECKING:
    pass

_avatar_repo = AvatarRepo()
_loc_repo = LocalizationRepo()

# Minimum performance records required to activate data-driven persona inference
_PERSONA_MIN_RECORDS = 10


class NicheAvatarMatcher:
    def match(
        self,
        db: Session,
        niche_code: str,
        market_code: Optional[str] = None,
        limit: int = 10,
    ) -> list[AvatarDna]:
        # Try market-fit filtered first
        if market_code:
            fits = _loc_repo.avatars_for_market(db, market_code, min_score=0.4, limit=limit * 3)
            if fits:
                avatar_ids = [f.avatar_id for f in fits]
                avatars = [_avatar_repo.get_avatar(db, aid) for aid in avatar_ids]
                avatars = [
                    a for a in avatars
                    if a and a.is_published and a.niche_code == niche_code
                ]
                if avatars:
                    return avatars[:limit]

        return _avatar_repo.list_avatars(
            db,
            niche_code=niche_code,
            market_code=market_code,
            published_only=True,
            limit=limit,
        )


class PersonaInferenceEngine:
    """Infer the top-performing persona for a niche+platform combination.

    When ≥10 performance records exist for the niche+platform pair, returns the
    ``avatar_id`` with the highest average time-weighted ``conversion_score``.
    Falls back to ``None`` when insufficient data is available; callers should
    fall back to keyword-based persona selection in that case.
    """

    def top_persona_avatar_id(
        self,
        db: Session,
        *,
        niche_code: str,
        platform: Optional[str] = None,
        market_code: Optional[str] = None,
    ) -> Optional[str]:
        """Return the avatar_id with the best historical conversion for this niche+platform."""
        try:
            from app.models.performance_record import PerformanceRecord
            import math
            import time

            query = (
                db.query(PerformanceRecord)
                .filter(PerformanceRecord.conversion_score.isnot(None))
            )
            if platform:
                query = query.filter(PerformanceRecord.platform == platform)
            if market_code:
                query = query.filter(PerformanceRecord.market_code == market_code)

            rows = query.all()
            if len(rows) < _PERSONA_MIN_RECORDS:
                return None

            # Group by avatar_id (stored in PerformanceLearningEngine JSON records
            # but not in DB PerformanceRecord table — fall back to template_family proxy)
            from collections import defaultdict
            now = time.time()
            _HALF_LIFE_DAYS = 90.0
            family_scores: dict[str, list[float]] = defaultdict(list)
            for row in rows:
                age_days = max(0.0, (now - row.recorded_at.timestamp()) / 86400.0)
                weight = math.pow(0.5, age_days / _HALF_LIFE_DAYS)
                family_scores[row.template_family].append(row.conversion_score * weight)

            if not family_scores:
                return None

            best_family = max(family_scores, key=lambda k: sum(family_scores[k]))
            return best_family  # Returns template_family as persona proxy when avatar_id unavailable
        except Exception:
            return None

    def infer_persona_label(
        self,
        db: Session,
        *,
        niche_code: str,
        platform: Optional[str] = None,
        market_code: Optional[str] = None,
        fallback: str = "customer",
    ) -> str:
        """Return best persona label string, falling back to keyword-inferred label."""
        result = self.top_persona_avatar_id(
            db,
            niche_code=niche_code,
            platform=platform,
            market_code=market_code,
        )
        if result:
            # Map template_family (used as proxy) to a persona label
            _FAMILY_TO_PERSONA = {
                "testimonial": "verified customer",
                "product_demo": "power user",
                "education": "learner",
                "sales": "deal seeker",
                "brand_awareness": "brand enthusiast",
                "entertainment": "casual viewer",
                "lead_generation": "prospect",
            }
            return _FAMILY_TO_PERSONA.get(result, result)
        return _infer_keyword_persona(niche_code, fallback)


def _infer_keyword_persona(niche_code: str, fallback: str) -> str:
    """Simple keyword-based persona inference from niche_code."""
    mapping = {
        "fitness": "fitness enthusiast",
        "skincare": "beauty conscious consumer",
        "tech": "early adopter",
        "food": "food lover",
        "fashion": "style-conscious shopper",
        "education": "lifelong learner",
        "finance": "value-conscious investor",
    }
    niche_lower = niche_code.lower()
    for key, label in mapping.items():
        if key in niche_lower:
            return label
    return fallback

