"""brain_feedback_service — write render/publish outcomes back to memory.

After render: writes EpisodeMemory, updates series continuity.
After publish: if metrics are good, writes PatternMemory (winner DNA, hooks,
               thumbnails, CTAs).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MIN_PUBLISH_SCORE_FOR_WINNER = 0.6


class BrainFeedbackService:
    """Record render and publish outcomes back to Brain memory stores."""

    # ------------------------------------------------------------------
    # Render outcome
    # ------------------------------------------------------------------
    def record_render_outcome(
        self,
        db,
        *,
        project_id: str | None = None,
        render_job_id: str | None = None,
        final_video_url: str | None = None,
        scene_statuses: list[dict[str, Any]] | None = None,
        continuity_context: dict[str, Any] | None = None,
        brain_plan: dict[str, Any] | None = None,
        winner_dna_summary: dict[str, Any] | None = None,
    ) -> None:
        """Persist render outcome to EpisodeMemory and update series continuity."""
        if db is None:
            return

        plan = brain_plan or {}
        continuity = continuity_context or {}
        series_id = plan.get("selected_series_id") or continuity.get("series_id")
        episode_index = plan.get("selected_episode_index") or continuity.get("episode_index")

        if not series_id or episode_index is None:
            logger.debug(
                "BrainFeedbackService.record_render_outcome: no series_id/episode_index, skipping"
            )
            return

        try:
            self._write_episode_memory(
                db,
                series_id=series_id,
                episode_index=int(episode_index),
                brain_plan=plan,
                continuity_context=continuity,
                scene_statuses=scene_statuses or [],
                final_video_url=final_video_url,
            )
        except Exception as exc:
            logger.warning("BrainFeedbackService.record_render_outcome: write failed: %s", exc)

    def _write_episode_memory(
        self,
        db,
        *,
        series_id: str,
        episode_index: int,
        brain_plan: dict[str, Any],
        continuity_context: dict[str, Any],
        scene_statuses: list[dict[str, Any]],
        final_video_url: str | None,
    ) -> None:
        from app.models.episode_memory import EpisodeMemory

        scene_strategy = brain_plan.get("scene_strategy") or []
        winning_sequence = [
            {"scene_goal": s.get("scene_goal"), "pacing_weight": s.get("pacing_weight")}
            for s in scene_strategy
        ]

        open_loops = list(brain_plan.get("open_loop_targets") or [])
        callback_targets = list(brain_plan.get("callback_targets") or [])
        episode_role = brain_plan.get("episode_role")

        row = EpisodeMemory(
            series_id=series_id,
            episode_index=episode_index,
            character_state={
                "episode_role": episode_role,
                "final_video_url": final_video_url,
            },
            open_loops=open_loops,
            resolved_loops=list(continuity_context.get("resolved_loops") or []),
            winning_scene_sequence=winning_sequence,
            series_arc={
                "episode_number": episode_index,
                "arc_position": episode_role,
            },
            character_callbacks=callback_targets,
        )
        db.add(row)
        db.commit()
        logger.info(
            "BrainFeedbackService: EpisodeMemory written series=%s episode=%d",
            series_id,
            episode_index,
        )

    # ------------------------------------------------------------------
    # Publish outcome
    # ------------------------------------------------------------------
    def record_publish_outcome(
        self,
        db,
        *,
        project_id: str | None = None,
        publish_job_id: str | None = None,
        platform: str | None = None,
        title: str | None = None,
        description: str | None = None,
        thumbnail_url: str | None = None,
        signal_metrics: dict[str, Any] | None = None,
    ) -> None:
        """If publish signal is strong enough, write winner patterns to PatternMemory."""
        if db is None:
            return

        metrics = signal_metrics or {}
        score = self._compute_publish_score(metrics)

        if score < _MIN_PUBLISH_SCORE_FOR_WINNER:
            logger.debug(
                "BrainFeedbackService.record_publish_outcome: score %.2f below threshold, skipping pattern write",
                score,
            )
            return

        try:
            self._write_winner_patterns(
                db,
                project_id=project_id,
                publish_job_id=publish_job_id,
                platform=platform,
                title=title,
                description=description,
                thumbnail_url=thumbnail_url,
                metrics=metrics,
                score=score,
            )
        except Exception as exc:
            logger.warning("BrainFeedbackService.record_publish_outcome: write failed: %s", exc)

    def _write_winner_patterns(
        self,
        db,
        *,
        project_id: str | None,
        publish_job_id: str | None,
        platform: str | None,
        title: str | None,
        description: str | None,
        thumbnail_url: str | None,
        metrics: dict[str, Any],
        score: float,
    ) -> None:
        from app.services.pattern_library import PatternLibrary
        from app.schemas.patterns import PatternMemoryIn

        lib = PatternLibrary()

        pattern_payload: dict[str, Any] = {
            "project_id": project_id,
            "publish_job_id": publish_job_id,
            "platform": platform,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "metrics": metrics,
        }
        if title:
            pattern_payload["title_pattern"] = title
        if description:
            # Extract rough hook (first sentence)
            hook = description.split(".")[0].strip()
            pattern_payload["hook_pattern"] = hook

        lib.save(
            db,
            PatternMemoryIn(
                pattern_type="winner_dna",
                source_id=publish_job_id or project_id,
                score=score,
                payload=pattern_payload,
            ),
        )
        logger.info(
            "BrainFeedbackService: winner_dna pattern written (score=%.2f, project=%s)",
            score,
            project_id,
        )

    @staticmethod
    def _compute_publish_score(metrics: dict[str, Any]) -> float:
        """Compute a 0-1 score from available publish metrics."""
        ctr = float(metrics.get("ctr") or 0.0)
        retention = float(metrics.get("retention_rate") or 0.0)
        engagement = float(metrics.get("engagement_rate") or 0.0)
        # Weighted blend: retention (50%), CTR (30%), engagement (20%)
        score = retention * 0.5 + ctr * 0.3 + engagement * 0.2
        return min(1.0, max(0.0, score))
