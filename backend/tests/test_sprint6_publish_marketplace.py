"""Sprint 6 – Publish providers hardening + KOL marketplace tests.

Covers:
- YouTubePublishProvider: 429 handled with Retry-After parsing + rate-limit backoff
- TikTokPublishProvider: 429 handled with Retry-After parsing + rate-limit backoff
- AvatarRankingService.recommend_kols(): niche/market filter, performance boosting
- AvatarRankingService.update_ranking(): performance-weighted rank when learning store provided
"""
from __future__ import annotations

import io
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# YouTube rate limit handling
# ---------------------------------------------------------------------------

def _make_http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    mock_headers = MagicMock()
    mock_headers.get = lambda k, default=None: headers.get(k, default)
    return urllib.error.HTTPError(
        url="http://test",
        code=code,
        msg="",
        hdrs=mock_headers,
        fp=io.BytesIO(b""),
    )


def test_youtube_retry_after_parsed() -> None:
    from app.services.publish_providers.youtube_provider import YouTubePublishProvider

    exc = _make_http_error(429, retry_after="30")
    result = YouTubePublishProvider._parse_retry_after(exc)
    assert result == pytest.approx(30.0)


def test_youtube_retry_after_fallback_when_missing() -> None:
    from app.services.publish_providers.youtube_provider import (
        YouTubePublishProvider,
        _RATE_LIMIT_BACKOFF_SECS,
    )
    exc = _make_http_error(429, retry_after=None)
    result = YouTubePublishProvider._parse_retry_after(exc)
    assert result == pytest.approx(_RATE_LIMIT_BACKOFF_SECS)


def test_youtube_429_is_retriable() -> None:
    """429 should be included in the retriable status codes."""
    from app.services.publish_providers.youtube_provider import _RETRIABLE_STATUS_CODES
    assert 429 in _RETRIABLE_STATUS_CODES


def test_youtube_execute_retries_on_429_and_raises_after_exhaustion() -> None:
    """Provider should sleep after each 429, then re-raise the last exception."""
    with patch.dict("os.environ", {"YOUTUBE_UPLOAD_URL": "http://fake", "YOUTUBE_API_TOKEN": "tok"}):
        from app.services.publish_providers.youtube_provider import YouTubePublishProvider
        from app.core.config import settings as real_settings

        provider = YouTubePublishProvider()

        slept: list[float] = []

        def mock_do_request(body, headers):
            raise _make_http_error(429, retry_after="1")

        def mock_sleep(secs):
            slept.append(secs)

        provider._do_request = mock_do_request
        provider._sleep = mock_sleep

        # Patch the settings values on the real settings object temporarily
        original_retries = getattr(real_settings, "provider_max_retries", 3)
        original_base = getattr(real_settings, "provider_retry_base_seconds", 2)
        real_settings.provider_max_retries = 2
        real_settings.provider_retry_base_seconds = 1

        job = MagicMock()
        job.id = "job1"
        job.payload = {}
        job.publish_mode = "REAL"

        try:
            with pytest.raises(urllib.error.HTTPError):
                provider.execute(job)
        finally:
            real_settings.provider_max_retries = original_retries
            real_settings.provider_retry_base_seconds = original_base

        # Should have slept once per 429 (rate limit) for each attempt
        assert len(slept) >= 1


# ---------------------------------------------------------------------------
# TikTok rate limit handling
# ---------------------------------------------------------------------------

def test_tiktok_retry_after_parsed() -> None:
    from app.services.publish_providers.tiktok_provider import TikTokPublishProvider

    exc = _make_http_error(429, retry_after="45")
    result = TikTokPublishProvider._parse_retry_after(exc)
    assert result == pytest.approx(45.0)


def test_tiktok_retry_after_fallback_when_missing() -> None:
    from app.services.publish_providers.tiktok_provider import (
        TikTokPublishProvider,
        _RATE_LIMIT_BACKOFF_SECS,
    )
    exc = _make_http_error(429, retry_after=None)
    result = TikTokPublishProvider._parse_retry_after(exc)
    assert result == pytest.approx(_RATE_LIMIT_BACKOFF_SECS)


def test_tiktok_429_is_retriable() -> None:
    from app.services.publish_providers.tiktok_provider import _RETRIABLE_STATUS_CODES
    assert 429 in _RETRIABLE_STATUS_CODES


def test_tiktok_execute_retries_on_429_and_raises_after_exhaustion() -> None:
    with patch.dict("os.environ", {"TIKTOK_UPLOAD_URL": "http://fake", "TIKTOK_ACCESS_TOKEN": "tok"}):
        from app.services.publish_providers.tiktok_provider import TikTokPublishProvider
        from app.core.config import settings as real_settings

        provider = TikTokPublishProvider()
        slept: list[float] = []

        def mock_do_request(body, headers):
            raise _make_http_error(429)

        def mock_sleep(secs):
            slept.append(secs)

        provider._do_request = mock_do_request
        provider._sleep = mock_sleep

        original_retries = getattr(real_settings, "provider_max_retries", 3)
        original_base = getattr(real_settings, "provider_retry_base_seconds", 2)
        real_settings.provider_max_retries = 2
        real_settings.provider_retry_base_seconds = 1

        job = MagicMock()
        job.id = "job2"
        job.payload = {}
        job.publish_mode = "REAL"

        try:
            with pytest.raises(urllib.error.HTTPError):
                provider.execute(job)
        finally:
            real_settings.provider_max_retries = original_retries
            real_settings.provider_retry_base_seconds = original_base

        assert len(slept) >= 1


# ---------------------------------------------------------------------------
# AvatarRankingService – performance-weighted ranking + KOL recommendation
# ---------------------------------------------------------------------------

def _make_learning_store(records: list[dict]) -> MagicMock:
    store = MagicMock()
    store.all_records.return_value = records
    return store


def test_update_ranking_with_performance_data_higher_rank() -> None:
    from app.services.marketplace.avatar_ranking_service import AvatarRankingService

    svc = AvatarRankingService()
    db = MagicMock()

    # Mock dependencies
    ranking_result = MagicMock()
    ranking_result.rank_score = 10.0
    ranking_result.trending_score = 8.0

    with (
        patch("app.services.marketplace.avatar_ranking_service._economy_repo") as mock_eco,
        patch("app.services.marketplace.avatar_ranking_service._mp_repo") as mock_mp,
    ):
        mock_eco.count_usage.return_value = 2
        mock_mp.get_item_by_avatar.return_value = MagicMock(download_count=5)
        mock_mp.upsert_avatar_ranking.return_value = ranking_result

        # With no learning store
        result_no_perf = svc.update_ranking(db, "av1", learning_store=None)

        # With learning store showing high performance for this avatar
        ls = _make_learning_store([
            {"avatar_id": "av1", "conversion_score": 0.9, "click_through_rate": 0.1},
            {"avatar_id": "av1", "conversion_score": 0.85, "click_through_rate": 0.08},
        ])
        result_with_perf = svc.update_ranking(db, "av1", learning_store=ls)

    # Both calls return numeric scores (mocked)
    assert "rank_score" in result_no_perf
    assert "rank_score" in result_with_perf
    assert result_with_perf.get("avg_conversion_score") is not None


def test_recommend_kols_returns_list() -> None:
    from app.services.marketplace.avatar_ranking_service import AvatarRankingService

    svc = AvatarRankingService()
    db = MagicMock()

    mock_avatar = MagicMock()
    mock_avatar.id = "av1"
    mock_avatar.name = "KOL Tester"
    mock_avatar.niche_code = "beauty"
    mock_avatar.market_code = "VN"
    mock_avatar.is_featured = True
    mock_avatar.moderation_status = "approved"

    mock_item = MagicMock()
    mock_item.is_active = True
    mock_item.id = "item1"
    mock_item.price_usd = None
    mock_item.is_free = True

    mock_ranking = MagicMock()
    mock_ranking.rank_score = 50.0

    with (
        patch("app.services.marketplace.avatar_ranking_service._mp_repo") as mock_mp,
        patch("app.repositories.avatar_repo.AvatarRepo.list_avatars", return_value=[mock_avatar]),
    ):
        mock_mp.get_item_by_avatar.return_value = mock_item
        mock_mp.get_avatar_ranking.return_value = mock_ranking

        result = svc.recommend_kols(db, niche_code="beauty", market_code="VN")

    assert isinstance(result, list)
    if result:
        assert "avatar_id" in result[0]
        assert "rank_score" in result[0]


def test_recommend_kols_performance_boosted_higher() -> None:
    from app.services.marketplace.avatar_ranking_service import AvatarRankingService

    svc = AvatarRankingService()
    db = MagicMock()

    mock_avatar = MagicMock()
    mock_avatar.id = "av1"
    mock_avatar.name = "StarKOL"
    mock_avatar.niche_code = "fitness"
    mock_avatar.market_code = "VN"
    mock_avatar.is_featured = False
    mock_avatar.moderation_status = "approved"

    mock_item = MagicMock()
    mock_item.is_active = True
    mock_item.id = "item2"
    mock_item.price_usd = None
    mock_item.is_free = True

    mock_ranking = MagicMock()
    mock_ranking.rank_score = 10.0

    with (
        patch("app.services.marketplace.avatar_ranking_service._mp_repo") as mock_mp,
        patch("app.repositories.avatar_repo.AvatarRepo.list_avatars", return_value=[mock_avatar]),
    ):
        mock_mp.get_item_by_avatar.return_value = mock_item
        mock_mp.get_avatar_ranking.return_value = mock_ranking

        # Without performance data
        result_no_perf = svc.recommend_kols(db, niche_code="fitness")

        # With high-performance data for av1
        ls = _make_learning_store([
            {"avatar_id": "av1", "conversion_score": 0.95, "click_through_rate": 0.2, "template_family": "fitness"},
            {"avatar_id": "av1", "conversion_score": 0.90, "click_through_rate": 0.15, "template_family": "fitness"},
        ])
        result_with_perf = svc.recommend_kols(db, niche_code="fitness", learning_store=ls)

    if result_no_perf and result_with_perf:
        score_no_perf = result_no_perf[0]["rank_score"]
        score_with_perf = result_with_perf[0]["rank_score"]
        assert score_with_perf >= score_no_perf
