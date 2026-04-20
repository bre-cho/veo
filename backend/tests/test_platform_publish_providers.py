"""Unit tests for platform-specific publish providers (YouTube, TikTok, Meta)."""
from __future__ import annotations

import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from app.services.publish_providers.youtube_provider import YouTubePublishProvider
from app.services.publish_providers.tiktok_provider import TikTokPublishProvider
from app.services.publish_providers.meta_provider import MetaPublishProvider


def _mock_job(
    job_id: str = "abc123",
    platform: str = "youtube",
    payload: dict | None = None,
) -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.platform = platform
    job.publish_mode = "REAL"
    job.payload = payload or {
        "format": "short",
        "content_goal": "conversion",
        "title_angle": "Test Video",
        "metadata": {"channel_name": "TestChan", "market_code": "VN"},
    }
    return job


# ---------------------------------------------------------------------------
# YouTubePublishProvider
# ---------------------------------------------------------------------------

class TestYouTubePublishProvider:
    def _make(self) -> YouTubePublishProvider:
        with patch.dict(os.environ, {"YOUTUBE_UPLOAD_URL": "https://yt.example.com/upload"}):
            return YouTubePublishProvider()

    def test_raises_when_url_missing(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("YOUTUBE_UPLOAD_URL", "PUBLISH_PROVIDER_URL")}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(Exception, match="YOUTUBE_UPLOAD_URL"):
                YouTubePublishProvider()

    def test_execute_returns_ok(self) -> None:
        provider = self._make()
        with patch.object(provider, "_do_request", return_value={"ok": True, "provider_publish_id": "yt-pub-001"}), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job(platform="youtube"))
        assert result["ok"] is True
        assert result["platform"] == "youtube"
        assert result["mode"] == "REAL"

    def test_payload_has_snippet(self) -> None:
        job = _mock_job()
        payload = YouTubePublishProvider._build_payload(job)
        assert "snippet" in payload
        assert "title" in payload["snippet"]

    def test_payload_has_status(self) -> None:
        job = _mock_job()
        payload = YouTubePublishProvider._build_payload(job)
        assert "status" in payload
        assert "privacyStatus" in payload["status"]

    def test_retries_on_5xx(self) -> None:
        provider = self._make()
        call_count = 0

        def _side_effect(body, headers):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError("url", 503, "error", MagicMock(), None)
            return {"ok": True, "provider_publish_id": "yt-retry-001"}

        with patch.object(provider, "_do_request", side_effect=_side_effect), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job())
        assert result["ok"] is True
        assert call_count == 2

    def test_no_retry_on_4xx(self) -> None:
        provider = self._make()
        with patch.object(provider, "_do_request", side_effect=urllib.error.HTTPError("url", 400, "bad", MagicMock(), None)), \
             patch.object(provider, "_sleep") as mock_sleep:
            with pytest.raises(urllib.error.HTTPError):
                provider.execute(_mock_job())
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# TikTokPublishProvider
# ---------------------------------------------------------------------------

class TestTikTokPublishProvider:
    def _make(self) -> TikTokPublishProvider:
        with patch.dict(os.environ, {"TIKTOK_UPLOAD_URL": "https://tt.example.com/upload"}):
            return TikTokPublishProvider()

    def test_raises_when_url_missing(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("TIKTOK_UPLOAD_URL", "PUBLISH_PROVIDER_URL")}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(Exception, match="TIKTOK_UPLOAD_URL"):
                TikTokPublishProvider()

    def test_execute_returns_ok(self) -> None:
        provider = self._make()
        with patch.object(provider, "_do_request", return_value={"ok": True, "provider_publish_id": "tt-001"}), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job(platform="tiktok"))
        assert result["ok"] is True
        assert result["platform"] == "tiktok"

    def test_payload_has_post_info(self) -> None:
        job = _mock_job(platform="tiktok")
        payload = TikTokPublishProvider._build_payload(job)
        assert "post_info" in payload
        assert "privacy_level" in payload["post_info"]

    def test_payload_privacy_level_mapping(self) -> None:
        job = _mock_job(platform="tiktok")
        job.payload["metadata"]["privacy_status"] = "private"
        payload = TikTokPublishProvider._build_payload(job)
        assert payload["post_info"]["privacy_level"] == "SELF_ONLY"

    def test_payload_has_source_info(self) -> None:
        job = _mock_job(platform="tiktok")
        payload = TikTokPublishProvider._build_payload(job)
        assert "source_info" in payload


# ---------------------------------------------------------------------------
# MetaPublishProvider
# ---------------------------------------------------------------------------

class TestMetaPublishProvider:
    def _make(self) -> MetaPublishProvider:
        with patch.dict(os.environ, {"META_UPLOAD_URL": "https://meta.example.com/upload"}):
            return MetaPublishProvider()

    def test_raises_when_url_missing(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("META_UPLOAD_URL", "PUBLISH_PROVIDER_URL")}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(Exception, match="META_UPLOAD_URL"):
                MetaPublishProvider()

    def test_execute_returns_ok(self) -> None:
        provider = self._make()
        with patch.object(provider, "_do_request", return_value={"ok": True, "provider_publish_id": "meta-001"}), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job(platform="meta"))
        assert result["ok"] is True
        assert result["platform"] == "meta"

    def test_payload_has_media_type(self) -> None:
        job = _mock_job(platform="meta")
        payload = MetaPublishProvider._build_payload(job)
        assert "media_type" in payload

    def test_carousel_format_maps_to_carousel_media_type(self) -> None:
        job = _mock_job(platform="meta")
        job.payload["format"] = "carousel"
        payload = MetaPublishProvider._build_payload(job)
        assert payload["media_type"] == "CAROUSEL"

    def test_short_format_maps_to_reels(self) -> None:
        job = _mock_job(platform="meta")
        job.payload["format"] = "short"
        payload = MetaPublishProvider._build_payload(job)
        assert payload["media_type"] == "REELS"


# ---------------------------------------------------------------------------
# Platform routing in PublishScheduler
# ---------------------------------------------------------------------------

class TestPublishSchedulerPlatformRouting:
    def test_simulated_mode_returns_simulated_provider(self) -> None:
        from app.services.publish_scheduler import _get_provider
        from app.services.publish_providers.simulated import SimulatedPublishProvider
        import unittest.mock as mock

        with mock.patch("app.services.publish_scheduler._PUBLISH_MODE", "SIMULATED"):
            provider = _get_provider(platform="youtube")
        assert isinstance(provider, SimulatedPublishProvider)

    def test_real_mode_youtube_platform_returns_youtube_provider(self) -> None:
        from app.services.publish_scheduler import _get_provider
        import unittest.mock as mock

        env = {"YOUTUBE_UPLOAD_URL": "https://yt.example.com/upload"}
        with mock.patch("app.services.publish_scheduler._PUBLISH_MODE", "REAL"), \
             mock.patch.dict(os.environ, env):
            provider = _get_provider(platform="youtube")
        assert isinstance(provider, YouTubePublishProvider)

    def test_real_mode_tiktok_platform_returns_tiktok_provider(self) -> None:
        from app.services.publish_scheduler import _get_provider
        import unittest.mock as mock

        env = {"TIKTOK_UPLOAD_URL": "https://tt.example.com/upload"}
        with mock.patch("app.services.publish_scheduler._PUBLISH_MODE", "REAL"), \
             mock.patch.dict(os.environ, env):
            provider = _get_provider(platform="tiktok")
        assert isinstance(provider, TikTokPublishProvider)

    def test_real_mode_meta_platform_returns_meta_provider(self) -> None:
        from app.services.publish_scheduler import _get_provider
        import unittest.mock as mock

        env = {"META_UPLOAD_URL": "https://meta.example.com/upload"}
        with mock.patch("app.services.publish_scheduler._PUBLISH_MODE", "REAL"), \
             mock.patch.dict(os.environ, env):
            provider = _get_provider(platform="reels")
        assert isinstance(provider, MetaPublishProvider)

    def test_real_mode_fallback_to_http_when_no_platform(self) -> None:
        from app.services.publish_scheduler import _get_provider
        from app.services.publish_providers.http_provider import HttpPublishProvider
        import unittest.mock as mock

        env = {"PUBLISH_PROVIDER_URL": "https://generic.example.com/pub"}
        with mock.patch("app.services.publish_scheduler._PUBLISH_MODE", "REAL"), \
             mock.patch.dict(os.environ, env):
            provider = _get_provider(platform=None)
        assert isinstance(provider, HttpPublishProvider)
