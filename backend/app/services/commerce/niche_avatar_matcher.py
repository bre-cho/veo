from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna
from app.repositories.avatar_repo import AvatarRepo
from app.repositories.localization_repo import LocalizationRepo

_avatar_repo = AvatarRepo()
_loc_repo = LocalizationRepo()


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
