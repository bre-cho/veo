from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.ai_engine_config import AiEngineConfig

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_TEST_TIMEOUT = 10


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_ai_engine_config(db: Session) -> AiEngineConfig:
    """Return the single AI engine config row, creating it if absent."""
    row = db.query(AiEngineConfig).first()
    if row is None:
        row = AiEngineConfig()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def save_ai_engine_config(db: Session, payload: dict) -> AiEngineConfig:
    """Persist openrouter_api_key and/or default_model updates."""
    row = get_ai_engine_config(db)
    if "openrouter_api_key" in payload:
        row.openrouter_api_key = payload["openrouter_api_key"] or None
    if "default_model" in payload:
        row.default_model = payload["default_model"] or "openai/gpt-4o-mini"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return row


def test_openrouter_key(api_key: str) -> dict:
    """
    Validate an OpenRouter API key by calling /models.
    Returns {"ok": True} on success, {"ok": False, "detail": "..."} on failure.
    """
    if not api_key or not api_key.startswith("sk-or-"):
        return {"ok": False, "detail": "Key phải bắt đầu bằng sk-or-..."}
    try:
        resp = httpx.get(
            f"{OPENROUTER_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TEST_TIMEOUT,
        )
        if resp.status_code == 200:
            return {"ok": True}
        return {"ok": False, "detail": f"OpenRouter trả về HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"ok": False, "detail": "Request timed out khi kết nối OpenRouter"}
    except httpx.HTTPError as exc:
        logger.warning("OpenRouter key test HTTP error: %s", exc)
        return {"ok": False, "detail": str(exc)}
