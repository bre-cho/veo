"""brain_decision_engine — deterministic planning pipeline.

Step sequence inside build_plan():
  1. Recall winner patterns + continuity from memory_bundle
  2. Select template via TemplateSelector
  3. Map template → scene strategy via TemplateMapper
  4. Run A/B variant selection via TemplateABService
  5. Merge winner-pattern refs + open-loop / callback targets
  6. Build final BrainPlan + ContinuityContext
"""
from __future__ import annotations

from typing import Any

from app.schemas.brain_manifest import BrainPlan, ContinuityContext
from app.services.template.template_ab_service import TemplateABService
from app.services.template.template_mapper import TemplateMapper
from app.services.template.template_selector import TemplateSelector


class BrainDecisionEngine:
    def __init__(self) -> None:
        self._template_selector = TemplateSelector()
        self._template_mapper = TemplateMapper()
        self._template_ab = TemplateABService()

    def build_plan(
        self,
        *,
        request: dict[str, Any],
        memory_bundle: dict[str, Any],
        continuity: dict[str, Any],
    ) -> tuple[BrainPlan, ContinuityContext]:
        winner_patterns = memory_bundle.get("winner_patterns") or []
        top_pattern = winner_patterns[0] if winner_patterns else None

        template_result = self._template_selector.select(
            request=request,
            memory_bundle=memory_bundle,
            continuity=continuity,
        )

        scene_strategy = self._template_mapper.map_to_scene_strategy(
            template_payload=template_result.template_payload,
            episode_role=continuity.get("episode_role"),
        )

        # Inject winner pattern ref into every scene entry
        winner_pattern_ref = (top_pattern or {}).get("id")
        for entry in scene_strategy:
            if winner_pattern_ref:
                entry.setdefault("winner_pattern_ref", winner_pattern_ref)

        prompt_bias = self._template_mapper.map_to_prompt_bias(
            template_payload=template_result.template_payload,
        )

        has_recent_winner = bool((memory_bundle.get("winner_dna_summary") or {}).get("pattern_id"))
        run_ab = self._template_ab.should_run_ab(
            primary_score=template_result.score,
            has_recent_winner=has_recent_winner,
        )
        secondary_template_id = self._template_ab.choose_secondary_template(
            primary_template_id=template_result.template_id,
        )
        template_variants = self._template_ab.pick_variants(
            primary_template_id=template_result.template_id,
            secondary_template_id=secondary_template_id if run_ab else None,
        )

        open_loop_targets = list(continuity.get("unresolved_loops") or [])[:3]
        callback_targets = list(continuity.get("callback_targets") or [])[:3]

        plan = BrainPlan(
            selected_series_id=continuity.get("series_id"),
            selected_episode_index=continuity.get("episode_index"),
            episode_role=continuity.get("episode_role"),
            winner_pattern_refs=[p["id"] for p in winner_patterns if p.get("id")],
            open_loop_targets=open_loop_targets,
            callback_targets=callback_targets,
            scene_strategy=scene_strategy,
            pacing_strategy={
                "mode": "template_driven",
                "template_id": template_result.template_id,
            },
            cta_strategy={
                "mode": template_result.template_payload.get("cta_style"),
            },
            notes={
                "source_type": request.get("source_type"),
                "market_code": request.get("market_code"),
                "content_goal": request.get("content_goal"),
                "selected_template_id": template_result.template_id,
                "selected_template_family": template_result.template_family,
                "template_reasons": template_result.reasons,
                "template_score": template_result.score,
                "template_prompt_bias": prompt_bias,
                "template_ab_enabled": run_ab,
                "template_variants": template_variants,
                "top_winner_pattern_id": (top_pattern or {}).get("id"),
            },
        )

        continuity_context = ContinuityContext(
            series_id=continuity.get("series_id"),
            episode_index=continuity.get("episode_index"),
            episode_role=continuity.get("episode_role"),
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
