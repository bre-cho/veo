from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditService:
    """Lightweight audit service.

    Keeps API compatibility for template audit calls while avoiding
    hard dependency on a specific audit table in this code path.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        actor_user_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str,
        payload_json: dict[str, Any] | None = None,
    ) -> None:
        logger.info(
            "audit action=%s resource_type=%s resource_id=%s actor_user_id=%s actor_email=%s payload=%s",
            action,
            resource_type,
            resource_id,
            actor_user_id,
            actor_email,
            payload_json or {},
        )
