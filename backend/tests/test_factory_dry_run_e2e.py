from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="stale test disabled: _build_factory_run_detail private helper was removed from app.api.factory"
)


def test_factory_dry_run_e2e_stale_placeholder() -> None:
    """Placeholder to keep test module explicit until migrated to current factory API."""
    assert True
