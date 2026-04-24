"""scene_drama_worker — processes the full drama pipeline for a scene.

Section 18.1: scene_drama_worker
----------------------------------
Input:  scene_id
Process:
  1. Load current character states
  2. Load relationship graph
  3. Calculate scene tension
  4. Generate dialogue subtext map
  5. Compute power shift (single-axis + multi-dimensional)
  6. Compute emotional outcome
  7. Update relation edges
  8. Write memory traces
  9. Update arc progress
  10. Output blocking + camera plan

This worker is a Celery task that runs the DramaCompilerService for one
scene.  All DB persistence is handled inside the task; the compiler itself
remains stateless (no DB calls).
"""
from __future__ import annotations

import logging
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="drama.scene_drama_worker", bind=True, max_retries=2)
def scene_drama_task(
    self: Any,
    *,
    scene_id: str,
    project_id: str,
    episode_id: str | None = None,
    beat: dict[str, Any],
    characters: list[dict[str, Any]],
    character_states: list[dict[str, Any]] | None = None,
    relationships: list[dict[str, Any]] | None = None,
    memory_traces: list[dict[str, Any]] | None = None,
    arc_progresses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full 10-step drama pipeline for a single scene.

    Parameters
    ----------
    scene_id:
        Scene identifier to process.
    project_id, episode_id:
        Scope identifiers.
    beat:
        Story beat dict (type, conflict_intensity, outcome_type, etc.).
    characters:
        List of CharacterProfileSchema-compatible dicts.
    character_states, relationships, memory_traces, arc_progresses:
        Optional pre-loaded data; if None the task should fetch from DB
        (stub: accepts empty lists).

    Returns
    -------
    dict — the full DramaCompileResponse payload.
    """
    from app.services.drama.drama_compiler_service import DramaCompilerService

    logger.info(
        "scene_drama_task START scene=%s project=%s episode=%s",
        scene_id, project_id, episode_id,
    )

    compiler = DramaCompilerService()

    try:
        result = compiler.compile(
            project_id=project_id,
            scene_id=scene_id,
            episode_id=episode_id,
            beat=beat,
            characters=characters,
            character_states=character_states or [],
            relationships=relationships or [],
            memory_traces=memory_traces or [],
            arc_progresses=arc_progresses or [],
        )
    except Exception as exc:
        logger.exception("scene_drama_task FAILED scene=%s: %s", scene_id, exc)
        raise self.retry(exc=exc, countdown=5)

    _log_result_summary(scene_id, result)
    return result


def _log_result_summary(scene_id: str, result: dict[str, Any]) -> None:
    tension = result.get("tension_analysis") or {}
    metadata = result.get("metadata") or {}
    flat = metadata.get("flat_scene", False)
    score = metadata.get("tension_score", 0.0)
    violations = result.get("scene_law_violations") or []

    logger.info(
        "scene_drama_task DONE scene=%s tension=%.1f flat=%s violations=%d",
        scene_id, score, flat, len(violations),
    )
    if flat:
        logger.warning("scene=%s flagged as flat_scene — consider revising beat", scene_id)
    for v in violations:
        logger.warning("scene=%s law_violation: %s", scene_id, v)
