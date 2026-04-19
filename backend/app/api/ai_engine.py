from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ai_engine_service import (
    get_ai_engine_config,
    save_ai_engine_config,
    test_openrouter_key,
)

router = APIRouter(tags=["ai-engine"])


class AiEngineConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    openrouter_api_key: str | None = None
    default_model: str | None = None


class OpenRouterKeyTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr
    model: str | None = None


def _mask_key(key: str | None) -> str | None:
    """Return a masked version of the API key for safe frontend display."""
    if not key:
        return None
    if len(key) <= 12:
        return "****"
    return key[:8] + "****" + key[-4:]


@router.get("/api/v1/ai-engine/config")
async def get_config(db: Session = Depends(get_db)):
    row = get_ai_engine_config(db)
    return {
        "has_openrouter_api_key": bool(row.openrouter_api_key),
        "openrouter_api_key_masked": _mask_key(row.openrouter_api_key),
        "default_model": row.default_model,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.patch("/api/v1/ai-engine/config")
async def update_config(payload: AiEngineConfigUpdateRequest, db: Session = Depends(get_db)):
    config_data = payload.model_dump(exclude_unset=True)
    if not config_data:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    row = save_ai_engine_config(db, config_data)
    return {
        "has_openrouter_api_key": bool(row.openrouter_api_key),
        "openrouter_api_key_masked": _mask_key(row.openrouter_api_key),
        "default_model": row.default_model,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/api/v1/ai-engine/test-key")
async def test_key(payload: OpenRouterKeyTestRequest):
    api_key = payload.api_key.get_secret_value().strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    result = test_openrouter_key(api_key)
    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result.get("detail", "Invalid key"))
    return {"ok": True}
