"""brain_decision_engine — deterministic planning pipeline."""
from __future__ import annotations

from typing import Any

from app.schemas.brain_manifest import BrainPlan, ContinuityContext


class BrainDecisionEngine:
    def build_plan(
        self,
        *,
        request: dict[str, Any],
        memory_bundle: dict[str, Any],
        continuity: dict[str, Any],
    ) -> tuple[BrainPlan, ContinuityContext]:
        winner_patterns = memory_bundle.get("winner_patterns") or []
        top_pattern = winner_patterns[0] if winner_patterns else None
        selected_series_id = continuity.get("series_id")
        selected_episode_index = continuity.get("episode_index")
        episode_role = continuity.get("episode_role")

        open_loop_targets = list(continuity.get("unresolved_loops") or [])[:3]
        callback_targets = list(continuity.get("callback_targets") or [])[:3]

        scene_strategy = [
            {
                "scene_index": 1,
                "scene_goal": "hook",
                "series_role": episode_role,
                "winner_pattern_ref": (top_pattern or {}).get("id"),
            },
            {
                "scene_index": 2,
                "scene_goal": "tension",
                "series_role": episode_role,
                "winner_pattern_ref": (top_pattern or {}).get("id"),
            },
            {
                "scene_index": 3,
                "scene_goal": "reveal",
                "series_role": episode_role,
                "winner_pattern_ref": (top_pattern or {}).get("id"),
            },
            {
                "scene_index": 4,
                "scene_goal": "cta",
                "series_role": episode_role,
                "winner_pattern_ref": (top_pattern or {}).get("id"),
            },
        ]

        plan = BrainPlan(
            selected_series_id=selected_series_id,
            selected_episode_index=selected_episode_index,
            episode_role=episode_role,
            winner_pattern_refs=[p["id"] for p in winner_patterns if p.get("id")],
            open_loop_targets=open_loop_targets,
            callback_targets=callback_targets,
            scene_strategy=scene_strategy,
            pacing_strategy={"mode": "winner_biased"},
            cta_strategy={"mode": request.get("conversion_mode") or "soft_series_binge"},
            notes={
                "source_type": request.get("source_type"),
                "market_code": request.get("market_code"),
                "content_goal": request.get("content_goal"),
            },
        )

        continuity_context = ContinuityContext(
            series_id=selected_series_id,
            episode_index=selected_episode_index,
            episode_role=episode_role,
            unresolved_loops=open_loop_targets,
            resolved_loops=list(continuity.get("resolved_loops") or []),
            callback_targets=callback_targets,
            continuity_constraints={
                "preserve_avatar_identity": True,
                "preserve_series_tone": True,
            },
        )

        return plan, continuity_context

    # backward-compat alias used by older callers
    def plan(
        self,
        *,
        source_type: str,
        topic: str | None,
        script_text: str | None,
        series_id: str | None,
        episode_index: int | None,
        content_goal: str | None,
        conversion_mode: str | None,
        memory_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        """Legacy interface — build a BrainPlan-shaped dict."""
        from app.services.brain.series_continuity_router import SeriesContinuityRouter
        continuity = SeriesContinuityRouter().resolve(
            series_id=series_id,
            episode_index=episode_index,
            latest_episode_memory=memory_bundle.get("latest_episode_memory"),
            source_type=source_type,
        )
        brain_plan, _ = self.build_plan(
            request={
                "source_type": source_type,
                "topic": topic,
                "script_text": script_text,
                "content_goal": content_goal,
                "conversion_mode": conversion_mode,
            },
            memory_bundle=memory_bundle,
            continuity=continuity,
        )
        return brain_plan.model_dump()
