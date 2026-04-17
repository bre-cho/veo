from __future__ import annotations

import logging

from app.providers.veo.adapter import VeoAdapter
from .base import DispatchResult

_adapter = VeoAdapter()
_log = logging.getLogger(__name__)


def _cred_from_account(account: object) -> dict:
    return {
        "gemini_api_key": getattr(account, "gemini_api_key", None),
        "google_cloud_project": getattr(account, "google_cloud_project", None),
        "google_cloud_location": getattr(account, "google_cloud_location", None) or "global",
        "gcs_output_uri": getattr(account, "gcs_output_uri", None),
        "use_vertex": getattr(account, "use_vertex", False),
    }


async def dispatch_veo_video(payload: dict, db: object | None = None) -> DispatchResult:
    """Dispatch a video generation request to the real Veo API via VeoAdapter.

    When ``db`` is provided and at least one active Google account with
    rotation enabled exists, the adapter picks that account's credentials
    (round-robin by oldest ``last_used_at``) instead of the global env vars.
    """
    cred_override: dict | None = None
    if db is not None:
        try:
            from app.services.google_accounts_service import (
                pick_next_account_for_rotation,
                mark_account_used,
            )
            account = pick_next_account_for_rotation(db)
            if account is not None:
                cred_override = _cred_from_account(account)
                mark_account_used(db, account)
        except Exception as exc:
            _log.warning("Account rotation lookup failed, falling back to global settings: %s", exc)

    result = await _adapter.submit(
        scene_payload=payload,
        callback_url=payload.get("callback_url"),
        cred_override=cred_override,
    )
    return DispatchResult(
        accepted=result.accepted,
        provider_operation_name=result.provider_operation_name,
        raw_response=result.raw_response,
        error_message=result.error_message,
    )
