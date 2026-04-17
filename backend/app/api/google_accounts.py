from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.google_accounts_service import (
    list_google_accounts,
    create_google_account,
    update_google_account,
    delete_google_account,
)

router = APIRouter(tags=["google-accounts"])


@router.get("/api/v1/google-accounts")
async def get_google_accounts(db: Session = Depends(get_db)):
    return {"items": list_google_accounts(db)}


@router.post("/api/v1/google-accounts")
async def post_google_account(payload: dict, db: Session = Depends(get_db)):
    if not payload.get("label"):
        raise HTTPException(status_code=400, detail="label is required")
    return create_google_account(db, payload)


@router.patch("/api/v1/google-accounts/{account_id}")
async def patch_google_account(account_id: str, payload: dict, db: Session = Depends(get_db)):
    result = update_google_account(db, account_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.delete("/api/v1/google-accounts/{account_id}")
async def delete_google_account_route(account_id: str, db: Session = Depends(get_db)):
    ok = delete_google_account(db, account_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"deleted": True}
