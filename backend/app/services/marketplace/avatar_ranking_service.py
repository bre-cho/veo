from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.creator_economy_repo import CreatorEconomyRepo
from app.repositories.marketplace_repo import MarketplaceRepo

_economy_repo = CreatorEconomyRepo()
_mp_repo = MarketplaceRepo()

# ---------------------------------------------------------------------------
# Performance-weighted ranking constants
# ---------------------------------------------------------------------------
# Weight for 7-day usage (trending signal)
_USAGE_7D_WEIGHT = 3.0
# Weight for 30-day usage (stability signal)
_USAGE_30D_WEIGHT = 2.0
# Weight for download count (popularity signal)
_DOWNLOAD_WEIGHT = 1.0
# Weight for average conversion score from learning store
_CONVERSION_SCORE_WEIGHT = 50.0
# Weight for avg CTR from learning store
_CTR_WEIGHT = 30.0


class AvatarRankingService:
    def update_ranking(
        self,
        db: Session,
        avatar_id: str,
        learning_store: Any | None = None,
    ) -> dict:
        """Update avatar ranking scores.

        When ``learning_store`` is provided, injects performance signals
        (avg conversion score, avg CTR) to produce a performance-weighted rank.
        """
        usage_7d = _economy_repo.count_usage(db, avatar_id, days=7)
        usage_30d = _economy_repo.count_usage(db, avatar_id, days=30)

        item = _mp_repo.get_item_by_avatar(db, avatar_id)
        download_count = item.download_count if item else 0

        # Base engagement-driven scores
        trending_score = usage_7d * _USAGE_7D_WEIGHT + download_count * _DOWNLOAD_WEIGHT
        rank_score = usage_30d * _USAGE_30D_WEIGHT + download_count * _DOWNLOAD_WEIGHT

        # Inject performance boost from learning store
        performance_boost = 0.0
        avg_conversion = None
        avg_ctr = None
        if learning_store is not None:
            try:
                records = [
                    r for r in learning_store.all_records()
                    if r.get("avatar_id") == avatar_id
                ]
                if records:
                    avg_conversion = sum(float(r["conversion_score"]) for r in records) / len(records)
                    ctrs = [float(r.get("click_through_rate") or 0) for r in records]
                    avg_ctr = sum(ctrs) / len(ctrs) if ctrs else None
                    if avg_conversion is not None:
                        performance_boost += avg_conversion * _CONVERSION_SCORE_WEIGHT
                    if avg_ctr is not None:
                        performance_boost += avg_ctr * _CTR_WEIGHT
            except Exception:
                pass

        trending_score += performance_boost
        rank_score += performance_boost

        ranking = _mp_repo.upsert_avatar_ranking(
            db,
            avatar_id,
            {
                "usage_count_7d": usage_7d,
                "usage_count_30d": usage_30d,
                "download_count": download_count,
                "trending_score": trending_score,
                "rank_score": rank_score,
                "last_computed_at": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )
        result = {
            "avatar_id": avatar_id,
            "rank_score": float(ranking.rank_score),
            "trending_score": float(ranking.trending_score),
        }
        if avg_conversion is not None:
            result["avg_conversion_score"] = round(avg_conversion, 3)
        if avg_ctr is not None:
            result["avg_ctr"] = round(avg_ctr, 4)
        return result

    def recommend_kols(
        self,
        db: Session,
        *,
        niche_code: str | None = None,
        market_code: str | None = None,
        product_category: str | None = None,
        learning_store: Any | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recommend KOL avatars ranked by niche/product fit + performance.

        Filters marketplace avatars by niche/market, then ranks them by
        their rank_score supplemented by conversion performance from
        the learning store when available.
        """
        from app.repositories.avatar_repo import AvatarRepo
        avatar_repo = AvatarRepo()

        avatars = avatar_repo.list_avatars(
            db,
            market_code=market_code,
            niche_code=niche_code,
            published_only=True,
            limit=limit * 3,
            offset=0,
        )

        candidates: list[dict[str, Any]] = []
        for avatar in avatars:
            if avatar.moderation_status != "approved":
                continue
            item = _mp_repo.get_item_by_avatar(db, avatar.id)
            if not item or not item.is_active:
                continue
            ranking = _mp_repo.get_avatar_ranking(db, avatar.id)
            rank_score = float(ranking.rank_score) if ranking else 0.0

            # Boost by performance data when available
            perf_boost = 0.0
            if learning_store is not None:
                try:
                    records = [
                        r for r in learning_store.all_records()
                        if r.get("avatar_id") == avatar.id
                    ]
                    if records:
                        avg_conv = sum(float(r["conversion_score"]) for r in records) / len(records)
                        perf_boost = avg_conv * 20.0
                        # Extra boost for product-category match
                        if product_category:
                            matched = [
                                r for r in records
                                if product_category.lower() in str(r.get("template_family") or "").lower()
                            ]
                            if matched:
                                perf_boost += len(matched) * 2.0
                except Exception:
                    pass

            candidates.append({
                "avatar_id": avatar.id,
                "name": avatar.name,
                "niche_code": avatar.niche_code,
                "market_code": avatar.market_code,
                "rank_score": round(rank_score + perf_boost, 2),
                "is_featured": avatar.is_featured,
                "marketplace_item_id": item.id if item else None,
                "price_usd": float(item.price_usd) if item and item.price_usd else None,
                "is_free": item.is_free if item else None,
            })

        candidates.sort(key=lambda c: c["rank_score"], reverse=True)
        return candidates[:limit]
