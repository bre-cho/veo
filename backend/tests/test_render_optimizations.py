"""Tests for the shared provider normalization utility and poll backoff logic."""
from __future__ import annotations

import pytest

from app.services.provider_normalize import normalize_provider_name
from app.workers.render_poll_worker import _poll_countdown, _POLL_BASE_SECONDS, _POLL_MAX_SECONDS


# ---------------------------------------------------------------------------
# normalize_provider_name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("veo", "veo"),
    ("VEO", "veo"),
    (" Veo_3 ", "veo"),
    ("veo_3_1", "veo"),
    ("google_veo", "veo"),
    # Unknown providers are returned lower-cased without modification.
    ("sora", "sora"),
    ("Pika", "pika"),
])
def test_normalize_provider_name(raw: str, expected: str) -> None:
    assert normalize_provider_name(raw) == expected


# ---------------------------------------------------------------------------
# _poll_countdown  (exponential back-off)
# ---------------------------------------------------------------------------

def test_poll_countdown_first_attempt() -> None:
    """First retry uses the base interval."""
    assert _poll_countdown(0) == _POLL_BASE_SECONDS


def test_poll_countdown_doubles_each_attempt() -> None:
    """Each successive retry doubles the countdown."""
    prev = _poll_countdown(0)
    for attempt in range(1, 5):
        current = _poll_countdown(attempt)
        assert current == prev * 2 or current == _POLL_MAX_SECONDS
        prev = current


def test_poll_countdown_is_capped() -> None:
    """Countdown never exceeds the configured maximum."""
    for attempt in range(20):
        assert _poll_countdown(attempt) <= _POLL_MAX_SECONDS


def test_poll_countdown_max_reached() -> None:
    """After enough retries the countdown equals the maximum."""
    # With base=15 and max=300, cap is hit at attempt 5 (15*2^5=480 > 300).
    assert _poll_countdown(100) == _POLL_MAX_SECONDS
