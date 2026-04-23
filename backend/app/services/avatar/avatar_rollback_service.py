from __future__ import annotations

from datetime import datetime, timezone


class AvatarRollbackService:
    def should_rollback(self, *, actual_publish_score: float | None, actual_retention: float | None, baseline_retention: float | None) -> bool:
        if actual_publish_score is not None and actual_publish_score < 0.40:
            return True
        if actual_retention is not None and baseline_retention is not None and actual_retention < baseline_retention - 0.12:
            return True
        return False

    def build_rollback_payload(self, *, avatar_id, reason_code: str) -> dict:
        return {
            "avatar_id": str(avatar_id),
            "reason_code": reason_code,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        }
