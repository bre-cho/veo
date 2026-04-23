"""brain_feedback_service — write render/publish outcomes back to memory."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.episode_memory import EpisodeMemory
from app.schemas.patterns import PatternMemoryIn
from app.services.pattern_library import PatternLibrary


class BrainFeedbackService:
    def __init__(self) -> None:
        self._pattern_library = PatternLibrary()

    def record_render_outcome(
        self,
        db: Session | None,
        *,
        project: dict[str, Any] | None,
        render_job_id: str,
        final_video_url: str | None,
        status: str,
    ) -> None:
        if db is None or not project:
            return

        series_id = project.get("series_id")
        episode_index = project.get("episode_index")
        continuity_context = project.get("continuity_context") or {}

        if not series_id or episode_index is None:
            return

        row = EpisodeMemory(
            series_id=str(series_id),
            episode_index=int(episode_index),
            open_loops=continuity_context.get("unresolved_loops") or [],
            resolved_loops=continuity_context.get("resolved_loops") or [],
            winning_scene_sequence=((project.get("brain_plan") or {}).get("scene_strategy") or []),
            series_arc={
                "episode_role": continuity_context.get("episode_role"),
                "render_job_id": render_job_id,
                "status": status,
                "final_video_url": final_video_url,
            },
            character_callbacks=continuity_context.get("callback_targets") or [],
        )
        db.add(row)
        db.commit()

    def record_publish_outcome(
        self,
        db: Session | None,
        *,
        payload: dict[str, Any],
        score: float = 0.5,
    ) -> None:
        if db is None:
            return

        winner_dna = payload.get("winner_dna_summary") or {}
        pattern_payload = {
            "hook_core": winner_dna.get("hook_core"),
            "title_pattern": winner_dna.get("title_pattern"),
            "thumbnail_logic": winner_dna.get("thumbnail_logic"),
            "source_payload": payload,
        }

        self._pattern_library.save(
            db,
            PatternMemoryIn(
                pattern_type="winner_dna",
                market_code=payload.get("market_code"),
                content_goal=payload.get("content_goal"),
                source_id=payload.get("project_id"),
                score=score,
                payload=pattern_payload,
            ),
        )

        # Record which template produced this winner
        selected_template_id = payload.get("selected_template_id")
        if score >= 0.6 and selected_template_id:
            self._pattern_library.save(
                db,
                PatternMemoryIn(
                    pattern_type="template_winner",
                    market_code=payload.get("market_code"),
                    content_goal=payload.get("content_goal"),
                    source_id=payload.get("project_id"),
                    score=score,
                    payload={
                        "template_id": selected_template_id,
                        "template_family": payload.get("selected_template_family"),
                        "winner_dna_summary": winner_dna,
                        "metrics": payload.get("metrics") or {},
                        "episode_role": (payload.get("continuity_context") or {}).get("episode_role"),
                    },
                ),
            )
