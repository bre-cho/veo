"""template_candidate_store — persist evolution candidates via PatternMemory.

Candidates are stored with pattern_type="template_candidate" so they are
isolated from "template_winner" and "template_reject" records.
The selector reads only *promoted* candidates; status lifecycle is tracked
inside the payload dict until a dedicated DB column exists.

Status lifecycle
----------------
candidate → testing → promoted | rejected
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.patterns import PatternMemoryIn
from app.services.pattern_library import PatternLibrary


class TemplateCandidateStore:
    def __init__(self) -> None:
        self._pattern_library = PatternLibrary()

    def save_candidate(
        self,
        db: Session,
        *,
        candidate_payload: dict[str, Any],
        market_code: str | None,
        content_goal: str | None,
        source_id: str | None,
    ) -> None:
        """Write a new evolution candidate record to PatternMemory."""
        self._pattern_library.save(
            db,
            PatternMemoryIn(
                pattern_type="template_candidate",
                market_code=market_code,
                content_goal=content_goal,
                source_id=source_id,
                score=0.0,
                payload={
                    **candidate_payload,
                    "status": candidate_payload.get("status") or "candidate",
                },
            ),
        )
