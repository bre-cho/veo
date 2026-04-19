from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.google_accounts_service import (
    list_google_accounts,
    create_google_account,
    update_google_account,
    delete_google_account,
)

router = APIRouter(tags=["google-accounts"])


class GoogleAccountCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    gemini_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str | None = "global"
    gcs_output_uri: str | None = None
    use_vertex: bool = False
    is_active: bool = True
    rotation_enabled: bool = True


class GoogleAccountPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    gemini_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str | None = None
    gcs_output_uri: str | None = None
    use_vertex: bool | None = None
    is_active: bool | None = None
    rotation_enabled: bool | None = None


@router.get("/api/v1/google-accounts")
async def get_google_accounts(db: Session = Depends(get_db)):
    return {"items": list_google_accounts(db)}


@router.post("/api/v1/google-accounts")
async def post_google_account(payload: GoogleAccountCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return create_google_account(db, data)


@router.patch("/api/v1/google-accounts/{account_id}")
async def patch_google_account(account_id: str, payload: GoogleAccountPatchRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    result = update_google_account(db, account_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.delete("/api/v1/google-accounts/{account_id}")
async def delete_google_account_route(account_id: str, db: Session = Depends(get_db)):
    ok = delete_google_account(db, account_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"deleted": True}
