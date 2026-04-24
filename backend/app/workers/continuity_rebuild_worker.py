"""continuity_rebuild_worker — rebuilds drama state downstream when a scene is edited.

Section 18.2: continuity_rebuild_worker
-----------------------------------------
When a scene is edited mid-episode:
  1. Rebuild downstream states
  2. Recompute relationship drift
  3. Recompute arc consistency
  4. Flag continuity breaks if a scene causes character collapse but the
     next scene treats them as unaffected

This worker runs the DramaCompilerService for each downstream scene in
order, carrying the corrected state forward and detecting continuity breaks.
"""
from __future__ import annotations

import logging
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="drama.continuity_rebuild_worker", bind=True, max_retries=2)
def continuity_rebuild_task(
    self: Any,
    *,
    project_id: str,
    episode_id: str,
    edited_scene_index: int,
    scenes: list[dict[str, Any]],
    characters: list[dict[str, Any]],
    character_states_before_edit: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    memory_traces: list[dict[str, Any]] | None = None,
    arc_progresses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rebuild drama continuity from ``edited_scene_index`` forward.

    Parameters
    ----------
    project_id, episode_id:
        Scope identifiers.
    edited_scene_index:
        0-based index of the scene that was changed.  All scenes at this
        index and later will be reprocessed.
    scenes:
        Full ordered list of scene beat dicts for the episode.
    characters:
        List of CharacterProfileSchema-compatible dicts.
    character_states_before_edit:
        Character states as they were immediately *before* the edited scene.
    relationships, memory_traces, arc_progresses:
        Optional pre-loaded data.

    Returns
    -------
    dict with keys:
        rebuilt_scenes: list of compile results for each reprocessed scene
        continuity_breaks: list of continuity-break warnings
        final_character_states: character states after last scene
        arc_summary: arc progress after last scene
    """
    from app.services.drama.drama_compiler_service import DramaCompilerService

    logger.info(
        "continuity_rebuild_task START project=%s episode=%s from_scene_index=%d",
        project_id, episode_id, edited_scene_index,
    )

    compiler = DramaCompilerService()
    downstream_scenes = scenes[edited_scene_index:]

    current_states: list[dict[str, Any]] = list(character_states_before_edit)
    current_memory_traces: list[dict[str, Any]] = list(memory_traces or [])
    current_arc_progresses: list[dict[str, Any]] = list(arc_progresses or [])
    current_relationships: list[dict[str, Any]] = list(relationships or [])

    rebuilt_scenes: list[dict[str, Any]] = []
    continuity_breaks: list[dict[str, Any]] = []

    # Track previous scene state per character for continuity check
    prev_state_map: dict[str, dict[str, Any]] = {
        s["character_id"]: s for s in current_states if "character_id" in s
    }

    try:
        for i, scene in enumerate(downstream_scenes):
            global_idx = edited_scene_index + i
            beat = scene.get("beat") or scene
            scene_id = str(
                scene.get("scene_id") or scene.get("id") or f"scene_{global_idx}"
            )

            result = compiler.compile(
                project_id=project_id,
                scene_id=scene_id,
                episode_id=episode_id,
                beat=beat,
                characters=characters,
                character_states=current_states,
                relationships=current_relationships,
                memory_traces=current_memory_traces,
                arc_progresses=current_arc_progresses,
            )
            rebuilt_scenes.append(result)

            # ── Continuity check ──────────────────────────────────────────
            for isu in result.get("inner_state_updates") or []:
                cid = isu.get("character_id")
                updated = isu.get("updated_state") or {}
                prev = prev_state_map.get(cid, {})

                # Flag collapse without carry-forward
                prev_collapse = float(prev.get("vulnerability_level") or 0.0) > 0.7
                curr_normal = float(updated.get("vulnerability_level") or 0.0) < 0.3
                if prev_collapse and curr_normal:
                    continuity_breaks.append({
                        "scene_id": scene_id,
                        "scene_index": global_idx,
                        "character_id": cid,
                        "break_type": "collapse_without_recovery",
                        "detail": (
                            f"Character {cid} was collapsed in previous scene "
                            f"(vulnerability={prev.get('vulnerability_level'):.2f}) "
                            f"but appears normal in scene {scene_id} "
                            f"(vulnerability={updated.get('vulnerability_level'):.2f})"
                        ),
                    })

                # Flag trust collapse without relational event
                prev_trust = float(prev.get("trust_level") or 0.5)
                curr_trust = float(updated.get("trust_level") or 0.5)
                if prev_trust > 0.7 and curr_trust < 0.3 and isu.get("outcome_type") == "neutral":
                    continuity_breaks.append({
                        "scene_id": scene_id,
                        "scene_index": global_idx,
                        "character_id": cid,
                        "break_type": "trust_collapse_without_trigger",
                        "detail": (
                            f"Character {cid} trust dropped from {prev_trust:.2f} to "
                            f"{curr_trust:.2f} with neutral outcome — missing betrayal event?"
                        ),
                    })

                # Update tracking state
                prev_state_map[cid] = updated

            # ── Carry forward state ───────────────────────────────────────
            for isu in result.get("inner_state_updates") or []:
                cid = isu.get("character_id")
                updated = isu.get("updated_state") or {}
                if cid:
                    current_states = [
                        s for s in current_states if s.get("character_id") != cid
                    ]
                    current_states.append({"character_id": cid, **updated})
                if isu.get("memory_trace"):
                    current_memory_traces.append(isu["memory_trace"])

            current_arc_progresses = [
                {**au, "character_id": au.get("character_id")}
                for au in result.get("arc_updates") or []
            ]

    except Exception as exc:
        logger.exception(
            "continuity_rebuild_task FAILED project=%s episode=%s: %s",
            project_id, episode_id, exc,
        )
        raise self.retry(exc=exc, countdown=10)

    if continuity_breaks:
        logger.warning(
            "continuity_rebuild_task found %d break(s) in project=%s episode=%s",
            len(continuity_breaks), project_id, episode_id,
        )
    else:
        logger.info(
            "continuity_rebuild_task OK project=%s episode=%s no breaks",
            project_id, episode_id,
        )

    return {
        "ok": True,
        "project_id": project_id,
        "episode_id": episode_id,
        "rebuilt_scene_count": len(rebuilt_scenes),
        "rebuilt_scenes": rebuilt_scenes,
        "continuity_breaks": continuity_breaks,
        "final_character_states": current_states,
        "arc_summary": current_arc_progresses,
    }
