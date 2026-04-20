from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna, AvatarMarketFit, AvatarRanking, CreatorProfile, CreatorRanking, MarketplaceItem


class MarketplaceRepo:
    def get_creator_profile(self, db: Session, creator_id: str) -> Optional[CreatorProfile]:
        return db.query(CreatorProfile).filter(CreatorProfile.creator_id == creator_id).first()

    def upsert_creator_profile(
        self,
        db: Session,
        creator_id: str,
        user_id: str,
        display_name: str,
        bio: str | None,
        market_code: str | None,
    ) -> CreatorProfile:
        row = self.get_creator_profile(db, creator_id) or CreatorProfile(creator_id=creator_id, user_id=user_id)
        row.user_id = user_id
        row.display_name = display_name
        row.bio = bio
        row.market_code = market_code
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def is_creator_owner(self, db: Session, creator_id: str, user_id: str) -> bool:
        row = self.get_creator_profile(db, creator_id)
        return bool(row and str(row.user_id) == str(user_id))

    def is_avatar_market_compatible(self, db: Session, avatar_id: str, market_code: str) -> bool:
        avatar = db.query(AvatarDna).filter(AvatarDna.id == avatar_id).first()
        if not avatar:
            return False
        if avatar.market_code and avatar.market_code == market_code:
            return True
        fit = (
            db.query(AvatarMarketFit)
            .filter(AvatarMarketFit.avatar_id == avatar_id, AvatarMarketFit.market_code == market_code)
            .first()
        )
        return bool(fit and float(fit.fit_score or 0) >= 0.5)

    def is_avatar_publicly_listable(self, db: Session, avatar_id: str) -> bool:
        avatar = db.query(AvatarDna).filter(AvatarDna.id == avatar_id).first()
        item = self.get_item_by_avatar(db, avatar_id)
        return bool(avatar and avatar.is_published and avatar.moderation_status == "approved" and item and item.is_active)

    def list_items(
        self,
        db: Session,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MarketplaceItem]:
        q = db.query(MarketplaceItem)
        if active_only:
            q = q.filter(MarketplaceItem.is_active.is_(True))
        return q.order_by(MarketplaceItem.created_at.desc()).limit(limit).offset(offset).all()

    def get_item_by_avatar(self, db: Session, avatar_id: str) -> Optional[MarketplaceItem]:
        return db.query(MarketplaceItem).filter(MarketplaceItem.avatar_id == avatar_id).first()

    def create_item(self, db: Session, data: dict) -> MarketplaceItem:
        item = MarketplaceItem(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def increment_view(self, db: Session, avatar_id: str) -> None:
        item = self.get_item_by_avatar(db, avatar_id)
        if item:
            item.view_count = (item.view_count or 0) + 1
            db.commit()

    def increment_download(self, db: Session, avatar_id: str) -> None:
        item = self.get_item_by_avatar(db, avatar_id)
        if item:
            item.download_count = (item.download_count or 0) + 1
            db.commit()

    # --- AvatarRanking ---

    def get_avatar_ranking(self, db: Session, avatar_id: str) -> Optional[AvatarRanking]:
        return db.query(AvatarRanking).filter(AvatarRanking.avatar_id == avatar_id).first()

    def upsert_avatar_ranking(self, db: Session, avatar_id: str, data: dict) -> AvatarRanking:
        row = self.get_avatar_ranking(db, avatar_id)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = AvatarRanking(avatar_id=avatar_id, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def top_ranked_avatars(self, db: Session, limit: int = 10) -> list[AvatarRanking]:
        return (
            db.query(AvatarRanking)
            .order_by(AvatarRanking.rank_score.desc())
            .limit(limit)
            .all()
        )

    def trending_avatars(self, db: Session, limit: int = 10) -> list[AvatarRanking]:
        return (
            db.query(AvatarRanking)
            .order_by(AvatarRanking.trending_score.desc())
            .limit(limit)
            .all()
        )

    # --- CreatorRanking ---

    def get_creator_ranking(self, db: Session, creator_id: str) -> Optional[CreatorRanking]:
        return db.query(CreatorRanking).filter(CreatorRanking.creator_id == creator_id).first()

    def upsert_creator_ranking(self, db: Session, creator_id: str, data: dict) -> CreatorRanking:
        row = self.get_creator_ranking(db, creator_id)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = CreatorRanking(creator_id=creator_id, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def top_creators(self, db: Session, limit: int = 10) -> list[CreatorRanking]:
        return (
            db.query(CreatorRanking)
            .order_by(CreatorRanking.rank_score.desc())
            .limit(limit)
            .all()
        )
