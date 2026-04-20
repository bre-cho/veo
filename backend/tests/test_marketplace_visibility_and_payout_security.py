from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.autovis import (
    AvatarDna,
    AvatarMarketFit,
    AvatarRanking,
    AvatarUsageEvent,
    CreatorEarning,
    CreatorProfile,
    MarketplaceItem,
)


def _build_client_and_session() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    seed_db = SessionLocal()
    return client, seed_db


def _cleanup(client: TestClient, seed_db: Session) -> None:
    seed_db.close()
    app.dependency_overrides.clear()
    client.close()


def _seed_avatar(
    db: Session,
    *,
    avatar_id: str,
    name: str,
    market_code: str | None = "US",
    is_published: bool = True,
    moderation_status: str = "approved",
    is_featured: bool = False,
    item_active: bool = True,
) -> None:
    db.add(
        AvatarDna(
            id=avatar_id,
            name=name,
            niche_code="demo",
            market_code=market_code,
            is_published=is_published,
            moderation_status=moderation_status,
            is_featured=is_featured,
        )
    )
    db.add(MarketplaceItem(avatar_id=avatar_id, is_active=item_active, is_free=True))


def test_trending_excludes_unpublished_avatar() -> None:
    client, db = _build_client_and_session()
    try:
        _seed_avatar(db, avatar_id="a-pub", name="Published", is_published=True)
        _seed_avatar(db, avatar_id="a-unpub", name="Unpublished", is_published=False)
        db.add(AvatarRanking(avatar_id="a-unpub", trending_score=Decimal("200"), rank_score=Decimal("200")))
        db.add(AvatarRanking(avatar_id="a-pub", trending_score=Decimal("100"), rank_score=Decimal("100")))
        db.commit()

        res = client.get("/api/v1/avatars/trending?limit=10")
        assert res.status_code == 200
        ids = {item["id"] for item in res.json()["items"]}
        assert "a-pub" in ids
        assert "a-unpub" not in ids
    finally:
        _cleanup(client, db)


def test_recommended_excludes_inactive_item() -> None:
    client, db = _build_client_and_session()
    try:
        _seed_avatar(db, avatar_id="a-active", name="Active Item", item_active=True)
        _seed_avatar(db, avatar_id="a-inactive", name="Inactive Item", item_active=False)
        db.commit()

        res = client.get("/api/v1/avatars/recommended?limit=10")
        assert res.status_code == 200
        ids = {item["id"] for item in res.json()["items"]}
        assert "a-active" in ids
        assert "a-inactive" not in ids
    finally:
        _cleanup(client, db)


def test_recommended_excludes_pending_and_rejected_moderation() -> None:
    client, db = _build_client_and_session()
    try:
        _seed_avatar(db, avatar_id="a-approved", name="Approved", moderation_status="approved")
        _seed_avatar(db, avatar_id="a-pending", name="Pending", moderation_status="pending")
        _seed_avatar(db, avatar_id="a-rejected", name="Rejected", moderation_status="rejected")
        db.commit()

        res = client.get("/api/v1/avatars/recommended?limit=10")
        assert res.status_code == 200
        ids = {item["id"] for item in res.json()["items"]}
        assert "a-approved" in ids
        assert "a-pending" not in ids
        assert "a-rejected" not in ids
    finally:
        _cleanup(client, db)


def test_recently_used_excludes_market_incompatible_avatar() -> None:
    client, db = _build_client_and_session()
    try:
        _seed_avatar(db, avatar_id="a-us", name="US Avatar", market_code="US")
        db.add(AvatarUsageEvent(avatar_id="a-us", user_id="u-1", event_type="render_dispatched"))
        db.commit()

        res = client.get("/api/v1/avatars/recently-used?user_id=u-1&market_code=VN")
        assert res.status_code == 200
        assert res.json()["items"] == []
    finally:
        _cleanup(client, db)


def test_payout_rejects_anonymous_request() -> None:
    client, db = _build_client_and_session()
    try:
        res = client.post("/api/v1/creators/c-anon/request-payout", json={"amount_usd": "1.0"})
        assert res.status_code == 401
    finally:
        _cleanup(client, db)


def test_payout_rejects_wrong_owner() -> None:
    client, db = _build_client_and_session()
    try:
        db.add(
            CreatorProfile(
                creator_id="creator-1",
                user_id="owner-1",
                display_name="Owner",
                bio="bio",
                market_code="US",
            )
        )
        db.add(CreatorEarning(creator_id="creator-1", amount_usd=Decimal("10.0000"), payout_status="pending"))
        db.commit()

        res = client.post(
            "/api/v1/creators/creator-1/request-payout",
            json={"amount_usd": "5.0"},
            headers={"X-User-Id": "not-owner"},
        )
        assert res.status_code == 403
    finally:
        _cleanup(client, db)


def test_payout_uses_path_creator_id_when_body_has_no_creator_id() -> None:
    client, db = _build_client_and_session()
    try:
        db.add(
            CreatorProfile(
                creator_id="creator-2",
                user_id="owner-2",
                display_name="Owner 2",
                bio=None,
                market_code="US",
            )
        )
        db.add(CreatorEarning(creator_id="creator-2", amount_usd=Decimal("10.0000"), payout_status="pending"))
        db.commit()

        res = client.post(
            "/api/v1/creators/creator-2/request-payout",
            json={"amount_usd": "5.0"},
            headers={"X-User-Id": "owner-2"},
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["creator_id"] == "creator-2"
        assert payload["status"] == "requested"
    finally:
        _cleanup(client, db)
