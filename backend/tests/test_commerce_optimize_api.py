"""Tests for POST /api/v1/commerce/optimize endpoint and budget_constraint integration."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_optimize_returns_valid_plan() -> None:
    resp = client.post(
        "/api/v1/commerce/optimize",
        json={"niche": "fitness", "days": 5, "posts_per_day": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "series_plan" in body
    assert "publish_queue_count" in body
    assert "winner_candidate_id" in body
    assert len(body["series_plan"]) == 5


def test_optimize_with_budget_constraint_caps_posts() -> None:
    resp = client.post(
        "/api/v1/commerce/optimize",
        json={
            "niche": "beauty",
            "days": 7,
            "posts_per_day": 2,
            "budget_constraint": 5.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # 5.0 budget / 1.0 cost_per_post = 5 posts max
    assert body["publish_queue_count"] == 5
    assert len(body["series_plan"]) == 5
    assert body["calendar_summary"]["budget_posts_cap"] == 5
    assert body["calendar_summary"]["budget_applied"] is True


def test_optimize_without_budget_returns_full_plan() -> None:
    resp = client.post(
        "/api/v1/commerce/optimize",
        json={"niche": "tech", "days": 3, "posts_per_day": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["publish_queue_count"] == 6
    assert "budget_applied" not in body["calendar_summary"]


def test_optimize_with_platform() -> None:
    resp = client.post(
        "/api/v1/commerce/optimize",
        json={
            "niche": "travel",
            "goal": "awareness",
            "days": 3,
            "platform": "tiktok",
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["series_plan"]) == 3


def test_optimize_with_objectives() -> None:
    resp = client.post(
        "/api/v1/commerce/optimize",
        json={
            "niche": "food",
            "days": 2,
            "objectives": {"conversion_score": 0.6, "view_count": 0.4},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["publish_queue_count"] == 2
