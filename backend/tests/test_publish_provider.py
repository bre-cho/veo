"""Unit tests for the publish_providers package (1.1)."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

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
