from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.autovis import (
    AvatarCollection,
    AvatarDna,
    AvatarMotionDna,
    AvatarVisualDna,
    AvatarVoiceDna,
)


class AvatarRepo:
    # --- AvatarDna ---

    def get_avatar(self, db: Session, avatar_id: str) -> Optional[AvatarDna]:
        return db.query(AvatarDna).filter(AvatarDna.id == avatar_id).first()

    def list_avatars(
        self,
        db: Session,
        market_code: Optional[str] = None,
        niche_code: Optional[str] = None,
        role_id: Optional[str] = None,
        published_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AvatarDna]:
        q = db.query(AvatarDna)
        if market_code:
            q = q.filter(AvatarDna.market_code == market_code)
        if niche_code:
            q = q.filter(AvatarDna.niche_code == niche_code)
        if role_id:
            q = q.filter(AvatarDna.role_id == role_id)
        if published_only:
            q = q.filter(AvatarDna.is_published.is_(True))
        return q.order_by(AvatarDna.created_at.desc()).limit(limit).offset(offset).all()

    def create_avatar(self, db: Session, data: dict) -> AvatarDna:
        avatar = AvatarDna(**data)
        db.add(avatar)
        db.commit()
        db.refresh(avatar)
        return avatar

    def update_avatar(self, db: Session, avatar_id: str, data: dict) -> Optional[AvatarDna]:
        avatar = self.get_avatar(db, avatar_id)
        if not avatar:
            return None
        for k, v in data.items():
            setattr(avatar, k, v)
        db.commit()
        db.refresh(avatar)
        return avatar

    # --- AvatarVisualDna ---

    def get_visual(self, db: Session, avatar_id: str) -> Optional[AvatarVisualDna]:
        return db.query(AvatarVisualDna).filter(AvatarVisualDna.avatar_id == avatar_id).first()

    def upsert_visual(self, db: Session, avatar_id: str, data: dict) -> AvatarVisualDna:
        row = self.get_visual(db, avatar_id)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = AvatarVisualDna(avatar_id=avatar_id, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    # --- AvatarVoiceDna ---

    def get_voice(self, db: Session, avatar_id: str) -> Optional[AvatarVoiceDna]:
        return db.query(AvatarVoiceDna).filter(AvatarVoiceDna.avatar_id == avatar_id).first()

    def upsert_voice(self, db: Session, avatar_id: str, data: dict) -> AvatarVoiceDna:
        row = self.get_voice(db, avatar_id)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = AvatarVoiceDna(avatar_id=avatar_id, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    # --- AvatarMotionDna ---

    def get_motion(self, db: Session, avatar_id: str) -> Optional[AvatarMotionDna]:
        return db.query(AvatarMotionDna).filter(AvatarMotionDna.avatar_id == avatar_id).first()

    def upsert_motion(self, db: Session, avatar_id: str, data: dict) -> AvatarMotionDna:
        row = self.get_motion(db, avatar_id)
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = AvatarMotionDna(avatar_id=avatar_id, **data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    # --- AvatarCollection ---

    def get_collection(self, db: Session, collection_id: str) -> Optional[AvatarCollection]:
        return db.query(AvatarCollection).filter(AvatarCollection.id == collection_id).first()

    def list_collections(self, db: Session, owner_user_id: Optional[str] = None) -> list[AvatarCollection]:
        q = db.query(AvatarCollection)
        if owner_user_id:
            q = q.filter(AvatarCollection.owner_user_id == owner_user_id)
        return q.all()

    def create_collection(self, db: Session, data: dict) -> AvatarCollection:
        col = AvatarCollection(**data)
        db.add(col)
        db.commit()
        db.refresh(col)
        return col

    def add_avatar_to_collection(self, db: Session, collection_id: str, avatar_id: str) -> Optional[AvatarCollection]:
        col = self.get_collection(db, collection_id)
        if not col:
            return None
        ids: list = col.avatar_ids or []
        if avatar_id not in ids:
            ids.append(avatar_id)
            col.avatar_ids = ids
            db.commit()
            db.refresh(col)
        return col
