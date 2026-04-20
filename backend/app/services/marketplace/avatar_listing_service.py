from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.avatar_repo import AvatarRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_avatar_repo = AvatarRepo()
_mp_repo = MarketplaceRepo()


class AvatarListingService:
    def recommended(self, db: Session, limit: int = 10) -> list[dict]:
        avatars = _avatar_repo.list_avatars(
            db, published_only=True, limit=limit
        )
        results = []
        for avatar in avatars:
            if avatar.is_featured:
                results.append({"id": avatar.id, "name": avatar.name, "niche_code": avatar.niche_code, "is_featured": True})
        # Pad with non-featured if needed
        if len(results) < limit:
            for avatar in avatars:
                if not avatar.is_featured and len(results) < limit:
                    results.append({"id": avatar.id, "name": avatar.name, "niche_code": avatar.niche_code, "is_featured": False})
        return results[:limit]

    def trending(self, db: Session, limit: int = 10) -> list[dict]:
        rankings = _mp_repo.trending_avatars(db, limit=limit)
        results = []
        for ranking in rankings:
            avatar = _avatar_repo.get_avatar(db, ranking.avatar_id)
            if avatar:
                results.append({
                    "id": avatar.id,
                    "name": avatar.name,
                    "niche_code": avatar.niche_code,
                    "trending_score": float(ranking.trending_score or 0),
                    "usage_count_7d": ranking.usage_count_7d,
                })
        return results
