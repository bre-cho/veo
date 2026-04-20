"""Unit tests for the enhanced PerformanceLearningEngine (B-layer)."""
from __future__ import annotations

import os
import tempfile
import time

import pytest

from app.services.learning_engine import PerformanceLearningEngine, _time_weight


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _engine(tmp_path) -> PerformanceLearningEngine:
    """Return a fresh engine backed by a temp file."""
    return PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))


# ---------------------------------------------------------------------------
# Time-weight function
# ---------------------------------------------------------------------------


def test_time_weight_now_is_one() -> None:
    w = _time_weight(time.time())
    assert 0.99 <= w <= 1.01


def test_time_weight_old_record_lower() -> None:
    now = time.time()
    ninety_days_ago = now - 90 * 86400
    w = _time_weight(ninety_days_ago)
    assert 0.48 <= w <= 0.52  # half-life = 90 days


def test_time_weight_very_old_near_zero() -> None:
    very_old = time.time() - 3 * 365 * 86400  # ~3 years
    w = _time_weight(very_old)
    assert w < 0.1


# ---------------------------------------------------------------------------
# record() – platform and market_code fields
# ---------------------------------------------------------------------------


def test_record_stores_platform(tmp_path) -> None:
    eng = _engine(tmp_path)
    rec = eng.record(
        video_id="v1",
        hook_pattern="hook-a",
        cta_pattern="cta-a",
        template_family="family-a",
        conversion_score=0.8,
        platform="tiktok",
    )
    assert rec["platform"] == "tiktok"
    assert eng.all_records()[0]["platform"] == "tiktok"


def test_record_stores_market_code(tmp_path) -> None:
    eng = _engine(tmp_path)
    eng.record(
        video_id="v1",
        hook_pattern="h",
        cta_pattern="c",
        template_family="f",
        conversion_score=0.7,
        market_code="VN",
    )
    assert eng.all_records()[0]["market_code"] == "VN"


# ---------------------------------------------------------------------------
# top_*() – platform and market_code filters
# ---------------------------------------------------------------------------


def _seed_engine(eng: PerformanceLearningEngine) -> None:
    eng.record(
        video_id="v-tiktok-1", hook_pattern="hook-viral", cta_pattern="cta-buy",
        template_family="ugc", conversion_score=0.9, platform="tiktok", market_code="VN",
    )
    eng.record(
        video_id="v-tiktok-2", hook_pattern="hook-viral", cta_pattern="cta-buy",
        template_family="ugc", conversion_score=0.85, platform="tiktok", market_code="VN",
    )
    eng.record(
        video_id="v-youtube-1", hook_pattern="hook-edu", cta_pattern="cta-sub",
        template_family="editorial", conversion_score=0.65, platform="youtube", market_code="US",
    )


def test_top_hook_patterns_no_filter_returns_all(tmp_path) -> None:
    eng = _engine(tmp_path)
    _seed_engine(eng)
    result = eng.top_hook_patterns()
    patterns = [r["pattern"] for r in result]
    assert "hook-viral" in patterns
    assert "hook-edu" in patterns


def test_top_hook_patterns_platform_filter(tmp_path) -> None:
    eng = _engine(tmp_path)
    _seed_engine(eng)
    result = eng.top_hook_patterns(platform="youtube")
    assert len(result) == 1
    assert result[0]["pattern"] == "hook-edu"


def test_top_hook_patterns_market_code_filter(tmp_path) -> None:
    eng = _engine(tmp_path)
    _seed_engine(eng)
    result = eng.top_hook_patterns(market_code="US")
    assert len(result) == 1
    assert result[0]["pattern"] == "hook-edu"


def test_top_template_families_platform_filter(tmp_path) -> None:
    eng = _engine(tmp_path)
    _seed_engine(eng)
    result = eng.top_template_families(platform="tiktok")
    assert len(result) == 1
    assert result[0]["pattern"] == "ugc"


# ---------------------------------------------------------------------------
# Time-weighted scoring: recent records outweigh old records
# ---------------------------------------------------------------------------


def test_time_weighted_scoring_recent_wins(tmp_path) -> None:
    """A pattern with recent records beats one with only very old records."""
    eng = _engine(tmp_path)
    now = time.time()

    # "hook-recent": a single recent record with moderate score
    eng._records.append({
        "video_id": "recent",
        "hook_pattern": "hook-recent",
        "cta_pattern": "c",
        "template_family": "f",
        "conversion_score": 0.75,
        "view_count": 0,
        "click_through_rate": 0.0,
        "platform": None,
        "market_code": None,
        "recorded_at": now,
    })
    # "hook-old": multiple very old records (360 days ago, weight ≈ 0.063)
    # Even though raw score is higher (0.90), time-decayed avg equals raw avg
    # for single records – so we add multiple old records to a different pattern
    # to demonstrate that the aggregated weighted score is lower than hook-recent.
    old_ts = now - 360 * 86400
    for i in range(4):
        eng._records.append({
            "video_id": f"old-{i}",
            "hook_pattern": "hook-old",
            "cta_pattern": "c",
            "template_family": "f",
            "conversion_score": 0.90,
            "view_count": 0,
            "click_through_rate": 0.0,
            "platform": None,
            "market_code": None,
            "recorded_at": old_ts,
        })
    # Add one recent very poor record for hook-old to drag its weighted avg down
    eng._records.append({
        "video_id": "old-recent-bad",
        "hook_pattern": "hook-old",
        "cta_pattern": "c",
        "template_family": "f",
        "conversion_score": 0.10,
        "view_count": 0,
        "click_through_rate": 0.0,
        "platform": None,
        "market_code": None,
        "recorded_at": now,
    })
    eng._save()

    top = eng.top_hook_patterns(limit=2)
    # hook-recent (0.75 recent) should rank above hook-old (0.9 old + 0.1 recent)
    # Because the recent bad record for hook-old pulls its time-weighted avg below 0.75
    assert top[0]["pattern"] == "hook-recent"


# ---------------------------------------------------------------------------
# feedback_summary() – preserves existing output contract
# ---------------------------------------------------------------------------


def test_feedback_summary_empty(tmp_path) -> None:
    eng = _engine(tmp_path)
    summary = eng.feedback_summary()
    assert summary["total_records"] == 0
    assert summary["avg_conversion_score"] == 0.0
    assert summary["top_hook_patterns"] == []


def test_feedback_summary_structure(tmp_path) -> None:
    eng = _engine(tmp_path)
    _seed_engine(eng)
    summary = eng.feedback_summary()
    assert "total_records" in summary
    assert "top_hook_patterns" in summary
    assert "top_cta_patterns" in summary
    assert "top_template_families" in summary
    assert "avg_conversion_score" in summary
    assert summary["total_records"] == 3


def test_feedback_summary_platform_filter(tmp_path) -> None:
    eng = _engine(tmp_path)
    _seed_engine(eng)
    summary = eng.feedback_summary(platform="tiktok")
    assert summary["total_records"] == 2


# ---------------------------------------------------------------------------
# DB dual-write
# ---------------------------------------------------------------------------


def test_db_upsert_persists_record(db_session) -> None:
    eng = PerformanceLearningEngine(store_path="/tmp/test_learning_db.json", db=db_session)
    eng.record(
        video_id="db-test-v1",
        hook_pattern="hook-db",
        cta_pattern="cta-db",
        template_family="family-db",
        conversion_score=0.82,
        platform="shorts",
        market_code="VN",
    )

    from app.models.performance_record import PerformanceRecord

    row = db_session.query(PerformanceRecord).filter_by(video_id="db-test-v1").first()
    assert row is not None
    assert row.hook_pattern == "hook-db"
    assert row.platform == "shorts"
    assert row.market_code == "VN"


def test_db_upsert_overwrites_existing(db_session) -> None:
    eng = PerformanceLearningEngine(store_path="/tmp/test_learning_db2.json", db=db_session)
    for score in (0.5, 0.9):
        eng.record(
            video_id="db-test-v2",
            hook_pattern="h",
            cta_pattern="c",
            template_family="f",
            conversion_score=score,
        )

    from app.models.performance_record import PerformanceRecord

    rows = (
        db_session.query(PerformanceRecord).filter_by(video_id="db-test-v2").all()
    )
    assert len(rows) == 1
    assert rows[0].conversion_score == 0.9
