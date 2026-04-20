"""Unit tests for PerformanceLearningEngine governance methods."""
from __future__ import annotations

import time

import pytest

from app.services.learning_engine import PerformanceLearningEngine


def _engine(tmp_path) -> PerformanceLearningEngine:
    return PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))


def _seed(eng: PerformanceLearningEngine, n: int = 10, score: float = 0.75) -> None:
    for i in range(n):
        eng.record(
            video_id=f"v{i}",
            hook_pattern="hook-a",
            cta_pattern="cta-b",
            template_family="ugc",
            conversion_score=score,
            platform="tiktok",
            market_code="VN",
        )


# ---------------------------------------------------------------------------
# data_quality_report()
# ---------------------------------------------------------------------------


class TestDataQualityReport:
    def test_empty_store_returns_ok(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        report = eng.data_quality_report()
        assert report["ok"] is True
        assert report["total_records"] == 0

    def test_clean_data_returns_ok(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=10)
        report = eng.data_quality_report()
        assert report["ok"] is True
        assert report["total_records"] == 10
        assert report["duplicate_video_ids"] == 0

    def test_missing_platform_detected(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        # Add records without platform (all missing)
        for i in range(10):
            eng.record(
                video_id=f"v{i}",
                hook_pattern="h",
                cta_pattern="c",
                template_family="f",
                conversion_score=0.6,
                platform=None,
                market_code=None,
            )
        report = eng.data_quality_report()
        assert report["missing_platform_pct"] == pytest.approx(1.0)
        assert report["ok"] is False
        assert any("platform" in issue for issue in report["issues"])

    def test_invalid_score_not_counted_for_in_range_scores(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=5, score=0.7)
        report = eng.data_quality_report()
        assert report["invalid_score_pct"] == 0.0

    def test_duplicate_detection(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=5)
        # Manually inject a duplicate (same video_id as v0)
        eng._records.append({
            "video_id": "v0",
            "hook_pattern": "hook-dup",
            "cta_pattern": "c",
            "template_family": "f",
            "conversion_score": 0.5,
            "view_count": 0,
            "click_through_rate": 0.0,
            "platform": "tiktok",
            "market_code": "VN",
            "recorded_at": time.time(),
        })
        eng._save()
        report = eng.data_quality_report()
        assert report["duplicate_video_ids"] >= 1


# ---------------------------------------------------------------------------
# score_drift_summary()
# ---------------------------------------------------------------------------


class TestScoreDriftSummary:
    def test_empty_store_returns_no_drift(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        result = eng.score_drift_summary()
        assert result["drift"] is None
        assert result["alert"] is False

    def test_stable_recent_scores_no_alert(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        now = time.time()
        for i in range(5):
            eng._records.append({
                "video_id": f"rec-{i}",
                "hook_pattern": "h",
                "cta_pattern": "c",
                "template_family": "f",
                "conversion_score": 0.75,
                "view_count": 0,
                "click_through_rate": 0.0,
                "platform": "tiktok",
                "market_code": "VN",
                "recorded_at": now - i * 86400,  # 0–4 days ago
            })
        eng._save()
        result = eng.score_drift_summary(window_days=7, baseline_days=30)
        assert result["alert"] is False

    def test_large_negative_drift_triggers_alert(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        now = time.time()
        # Baseline: 20 days ago, high scores
        for i in range(5):
            eng._records.append({
                "video_id": f"old-{i}",
                "hook_pattern": "h",
                "cta_pattern": "c",
                "template_family": "f",
                "conversion_score": 0.90,
                "view_count": 0,
                "click_through_rate": 0.0,
                "platform": "tiktok",
                "market_code": "VN",
                "recorded_at": now - 20 * 86400,
            })
        # Recent: very low scores
        for i in range(5):
            eng._records.append({
                "video_id": f"new-{i}",
                "hook_pattern": "h",
                "cta_pattern": "c",
                "template_family": "f",
                "conversion_score": 0.20,
                "view_count": 0,
                "click_through_rate": 0.0,
                "platform": "tiktok",
                "market_code": "VN",
                "recorded_at": now - 1 * 86400,
            })
        eng._save()
        result = eng.score_drift_summary(window_days=7, baseline_days=30)
        assert result["drift"] is not None
        assert result["drift"] < -0.14  # large negative drift
        assert result["alert"] is True

    def test_drift_summary_contains_expected_keys(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        result = eng.score_drift_summary()
        assert "recent_window_days" in result
        assert "baseline_days" in result
        assert "recent" in result
        assert "baseline" in result
        assert "drift" in result
        assert "alert" in result


# ---------------------------------------------------------------------------
# /learning/health endpoint
# ---------------------------------------------------------------------------

class TestLearningHealthEndpoint:
    def test_health_endpoint_returns_200(self, api_client) -> None:
        response = api_client.get("/api/v1/commerce/learning/health")
        assert response.status_code == 200

    def test_health_endpoint_has_expected_keys(self, api_client) -> None:
        response = api_client.get("/api/v1/commerce/learning/health")
        data = response.json()
        assert "data_quality" in data
        assert "score_drift" in data

    def test_health_data_quality_has_ok_field(self, api_client) -> None:
        response = api_client.get("/api/v1/commerce/learning/health")
        dq = response.json()["data_quality"]
        assert "ok" in dq
        assert "total_records" in dq
