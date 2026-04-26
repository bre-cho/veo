from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.state import timeline_service


class FactoryPublishControl:
    """Approval gate for live publishing."""

    def __init__(self, _db: Any | None = None) -> None:
        self._db = _db

    def approve(self, run_id: str, approved_by: str | None = None) -> dict[str, Any]:
        run = timeline_service.repository.get_run(run_id)
        if run is None:
            raise ValueError("factory_run_not_found")

        metadata = run.get("metadata_json") or {}
        if isinstance(metadata, str):
            import json

            metadata = json.loads(metadata)

        metadata["publish_approved"] = True
        metadata["publish_approved_by"] = approved_by or "system"
        metadata["publish_approved_at"] = datetime.now(timezone.utc).isoformat()

        run["metadata_json"] = metadata
        timeline_service.repository.upsert_run(run)
        return metadata

    def is_approved(self, run: Any) -> bool:
        if run is None:
            return False
        metadata = run.get("metadata_json") or {}
        if isinstance(metadata, str):
            import json

            metadata = json.loads(metadata)
        return bool(metadata.get("publish_approved"))
