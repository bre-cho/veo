from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.google_account import GoogleAccount


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize(account: GoogleAccount) -> dict:
    return {
        "id": str(account.id),
        "label": account.label,
        "has_gemini_api_key": bool(account.gemini_api_key),
        "google_cloud_project": account.google_cloud_project,
        "google_cloud_location": account.google_cloud_location,
        "gcs_output_uri": account.gcs_output_uri,
        "use_vertex": account.use_vertex,
        "is_active": account.is_active,
        "rotation_enabled": account.rotation_enabled,
        "last_used_at": account.last_used_at.isoformat() if account.last_used_at else None,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
    }


def list_google_accounts(db: Session) -> list[dict]:
    rows = db.query(GoogleAccount).order_by(GoogleAccount.created_at).all()
    return [_serialize(r) for r in rows]


def create_google_account(db: Session, payload: dict) -> dict:
    row = GoogleAccount(
        id=uuid.uuid4(),
        label=payload["label"],
        gemini_api_key=payload.get("gemini_api_key") or None,
        google_cloud_project=payload.get("google_cloud_project") or None,
        google_cloud_location=payload.get("google_cloud_location") or "global",
        gcs_output_uri=payload.get("gcs_output_uri") or None,
        use_vertex=bool(payload.get("use_vertex", False)),
        is_active=bool(payload.get("is_active", True)),
        rotation_enabled=bool(payload.get("rotation_enabled", True)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


def update_google_account(db: Session, account_id: str, payload: dict) -> dict | None:
    row = db.query(GoogleAccount).filter(GoogleAccount.id == account_id).first()
    if row is None:
        return None
    if "label" in payload:
        row.label = payload["label"]
    if "gemini_api_key" in payload:
        row.gemini_api_key = payload["gemini_api_key"] or None
    if "google_cloud_project" in payload:
        row.google_cloud_project = payload["google_cloud_project"] or None
    if "google_cloud_location" in payload:
        row.google_cloud_location = payload["google_cloud_location"] or "global"
    if "gcs_output_uri" in payload:
        row.gcs_output_uri = payload["gcs_output_uri"] or None
    if "use_vertex" in payload:
        row.use_vertex = bool(payload["use_vertex"])
    if "is_active" in payload:
        row.is_active = bool(payload["is_active"])
    if "rotation_enabled" in payload:
        row.rotation_enabled = bool(payload["rotation_enabled"])
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _serialize(row)


def delete_google_account(db: Session, account_id: str) -> bool:
    row = db.query(GoogleAccount).filter(GoogleAccount.id == account_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def pick_next_account_for_rotation(db: Session) -> GoogleAccount | None:
    """Return the active rotation-enabled account with the oldest last_used_at (round-robin)."""
    rows = (
        db.query(GoogleAccount)
        .filter(GoogleAccount.is_active.is_(True), GoogleAccount.rotation_enabled.is_(True))
        .order_by(GoogleAccount.last_used_at.asc().nullsfirst())
        .all()
    )
    return rows[0] if rows else None


def mark_account_used(db: Session, account: GoogleAccount) -> None:
    account.last_used_at = _now()
    account.updated_at = _now()
    db.commit()
