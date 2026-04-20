"""Unit tests for the publish_providers package (1.1)."""
from __future__ import annotations

import json
import os
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, call, patch

import pytest

from app.services.publish_providers import (
    ConfigurationError,
    HttpPublishProvider,
    SimulatedPublishProvider,
)


def _mock_job(job_id: str = "abcdef1234567890") -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.platform = "shorts"
    job.publish_mode = "SIMULATED"
    job.payload = {"format": "short", "content_goal": "engagement"}
    return job


def _make_http_provider() -> HttpPublishProvider:
    """Return a provider with a fake URL, no real network calls."""
    with patch.dict(os.environ, {"PUBLISH_PROVIDER_URL": "https://example.com/pub"}):
        return HttpPublishProvider()


def _urlopen_ok(body: dict) -> MagicMock:
    """Return a context-manager mock that yields a successful HTTP response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(body).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://example.com/pub", code=code, msg="err", hdrs=MagicMock(), fp=None
    )


class TestSimulatedPublishProvider:
    def test_execute_returns_ok(self) -> None:
        provider = SimulatedPublishProvider()
        result = provider.execute(_mock_job())
        assert result["ok"] is True

    def test_execute_mode_is_simulated(self) -> None:
        provider = SimulatedPublishProvider()
        result = provider.execute(_mock_job())
        assert result["mode"] == "SIMULATED"

    def test_execute_includes_provider_publish_id(self) -> None:
        provider = SimulatedPublishProvider()
        result = provider.execute(_mock_job("deadbeef12345678"))
        assert result["provider_publish_id"] == "sim-deadbeef"

    def test_execute_includes_note(self) -> None:
        provider = SimulatedPublishProvider()
        result = provider.execute(_mock_job())
        assert "SIMULATED publish" in result["note"]


class TestHttpPublishProvider:
    def test_raises_configuration_error_when_url_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PUBLISH_PROVIDER_URL", None)
            with pytest.raises(ConfigurationError, match="PUBLISH_PROVIDER_URL"):
                HttpPublishProvider()

    def test_raises_configuration_error_when_url_empty(self) -> None:
        with patch.dict(os.environ, {"PUBLISH_PROVIDER_URL": "  "}, clear=False):
            with pytest.raises(ConfigurationError, match="PUBLISH_PROVIDER_URL"):
                HttpPublishProvider()

    def test_instantiates_when_url_set(self) -> None:
        with patch.dict(os.environ, {"PUBLISH_PROVIDER_URL": "https://example.com/publish"}, clear=False):
            provider = HttpPublishProvider()
            assert provider._url == "https://example.com/publish"

    def test_token_optional(self) -> None:
        env = {"PUBLISH_PROVIDER_URL": "https://example.com/publish"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("PUBLISH_PROVIDER_TOKEN", None)
            provider = HttpPublishProvider()
            assert provider._token == ""


class TestHttpPublishProviderRetry:
    """Tests for retry / backoff behaviour (A-layer)."""

    def test_success_on_first_attempt_no_retry(self) -> None:
        provider = _make_http_provider()
        ok_resp = _urlopen_ok({"ok": True, "provider_publish_id": "pub-001"})

        with patch.object(provider, "_do_request", return_value={"ok": True, "provider_publish_id": "pub-001"}) as mock_req, \
             patch.object(provider, "_sleep") as mock_sleep:
            result = provider.execute(_mock_job())

        assert result["ok"] is True
        assert mock_req.call_count == 1
        mock_sleep.assert_not_called()

    def test_retries_on_500_then_succeeds(self) -> None:
        provider = _make_http_provider()
        responses = [_http_error(500), _http_error(503), {"ok": True, "provider_publish_id": "pub-002"}]
        call_count = 0

        def _side_effect(body, headers):
            nonlocal call_count
            call_count += 1
            r = responses[call_count - 1]
            if isinstance(r, Exception):
                raise r
            return r

        with patch.object(provider, "_do_request", side_effect=_side_effect), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job())

        assert result["ok"] is True
        assert call_count == 3

    def test_no_retry_on_400(self) -> None:
        provider = _make_http_provider()

        with patch.object(provider, "_do_request", side_effect=_http_error(400)), \
             patch.object(provider, "_sleep") as mock_sleep:
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                provider.execute(_mock_job())

        assert exc_info.value.code == 400
        mock_sleep.assert_not_called()

    def test_no_retry_on_422(self) -> None:
        provider = _make_http_provider()

        with patch.object(provider, "_do_request", side_effect=_http_error(422)), \
             patch.object(provider, "_sleep") as mock_sleep:
            with pytest.raises(urllib.error.HTTPError):
                provider.execute(_mock_job())

        mock_sleep.assert_not_called()

    def test_exhausts_retries_and_raises(self) -> None:
        provider = _make_http_provider()

        with patch.object(provider, "_do_request", side_effect=_http_error(503)), \
             patch.object(provider, "_sleep"):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                provider.execute(_mock_job())

        assert exc_info.value.code == 503

    def test_retries_on_network_error(self) -> None:
        provider = _make_http_provider()
        url_err = urllib.error.URLError("connection refused")
        responses = [url_err, url_err, {"ok": True, "provider_publish_id": "pub-net"}]
        call_count = 0

        def _side_effect(body, headers):
            nonlocal call_count
            call_count += 1
            r = responses[call_count - 1]
            if isinstance(r, Exception):
                raise r
            return r

        with patch.object(provider, "_do_request", side_effect=_side_effect), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job())

        assert result["ok"] is True

    def test_sleep_called_with_exponential_backoff(self) -> None:
        provider = _make_http_provider()
        from app.core.config import settings

        base = float(settings.provider_retry_base_seconds)
        call_count = 0

        def _side_effect(body, headers):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise _http_error(500)
            return {"ok": True, "provider_publish_id": "pub-exp"}

        sleep_calls: list[float] = []

        def _fake_sleep(s: float) -> None:
            sleep_calls.append(s)

        with patch.object(provider, "_do_request", side_effect=_side_effect), \
             patch.object(provider, "_sleep", side_effect=_fake_sleep):
            provider.execute(_mock_job())

        assert len(sleep_calls) == 2
        # First sleep = base * 2^0 = base; second = base * 2^1 = 2*base
        assert sleep_calls[0] == pytest.approx(base, rel=0.01)
        assert sleep_calls[1] == pytest.approx(base * 2, rel=0.01)

    def test_result_includes_mode_real(self) -> None:
        provider = _make_http_provider()

        with patch.object(provider, "_do_request", return_value={"ok": True, "provider_publish_id": "x"}), \
             patch.object(provider, "_sleep"):
            result = provider.execute(_mock_job())

        assert result["mode"] == "REAL"

