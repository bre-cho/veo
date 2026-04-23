"""brain_manifest_builder — convert brain plan into an enriched preview payload.

For topic input, converts the topic into a draft script then uses the same
helpers as script_ingestion.py (no duplication).

For script input, passes the already-parsed scenes through with brain enrichment.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel topic-to-script template: expand topic into brief scene-per-paragraph blocks.
_TOPIC_SCENE_PROMPTS = [
    "Hook: {topic} — what most people don't realize.",
    "The hidden truth about {topic} that changes everything.",
    "Here's the specific pattern behind {topic} nobody talks about.",
    "What this means for you — and what to do next about {topic}.",
    "The one thing you need to remember about {topic}.",
]


class BrainManifestBuilder:
    """Build enriched ScriptPreviewPayload-shaped dicts."""

    def build(
        self,
        *,
        source_type: str,
        topic: str | None,
        script_text: str | None,
        filename: str | None,
        aspect_ratio: str,
        target_platform: str,
        style_preset: str | None,
        avatar_id: str | None,
        market_code: str | None,
        content_goal: str | None,
        conversion_mode: str | None,
        memory_bundle: dict[str, Any],
        brain_plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a dict compatible with ScriptPreviewPayload + brain enrichment."""
        from app.services.script_ingestion import build_preview_payload

        if source_type == "topic" and topic and not script_text:
            script_text = self._topic_to_script(topic)
            filename = filename or f"{topic[:40].replace(' ', '_')}.txt"

        if not script_text:
            raise ValueError("script_text is required to build manifest")

        # Build the base preview (scenes + subtitles + storyboard)
        base = build_preview_payload(
            filename=filename,
            script_text=script_text,
            aspect_ratio=aspect_ratio,
            target_platform=target_platform,
            style_preset=style_preset,
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
        )

        # Override source_mode for topic intake
        if source_type == "topic":
            base["source_mode"] = "topic_intake"

        # Enrich scenes with brain strategy
        base["scenes"] = self._enrich_scenes(base.get("scenes") or [], brain_plan, memory_bundle)

        # Attach brain fields
        base["series_id"] = brain_plan.get("selected_series_id")
        base["episode_index"] = brain_plan.get("selected_episode_index")
        base["brain_plan"] = brain_plan
        base["continuity_context"] = (memory_bundle.get("continuity_context") or {})
        base["winner_dna_summary"] = (memory_bundle.get("winner_dna_summary") or {})
        base["winner_patterns"] = memory_bundle.get("winner_patterns") or []
        base["memory_refs"] = memory_bundle.get("memory_refs") or {}

        return base

    # ------------------------------------------------------------------

    @staticmethod
    def _topic_to_script(topic: str) -> str:
        """Convert a topic string into a multi-paragraph draft script."""
        lines = [prompt.format(topic=topic) for prompt in _TOPIC_SCENE_PROMPTS]
        return "\n\n".join(lines)

    @staticmethod
    def _enrich_scenes(
        scenes: list[dict[str, Any]],
        brain_plan: dict[str, Any],
        memory_bundle: dict[str, Any],
    ) -> list[dict[str, Any]]:
        scene_strategy = brain_plan.get("scene_strategy") or []
        winner_dna = memory_bundle.get("winner_dna_summary") or {}
        series_id = brain_plan.get("selected_series_id")
        episode_index = brain_plan.get("selected_episode_index")
        episode_role = brain_plan.get("episode_role")
        open_loops = brain_plan.get("open_loop_targets") or []
        callbacks = brain_plan.get("callback_targets") or []
        winner_refs = brain_plan.get("winner_pattern_refs") or []

        enriched = []
        for i, scene in enumerate(scenes):
            updated = dict(scene)
            meta = dict(updated.get("metadata") or {})

            # Inject execution_context with brain fields
            exec_ctx = dict(meta.get("execution_context") or {})
            if series_id is not None:
                exec_ctx["series_id"] = series_id
            if episode_index is not None:
                exec_ctx["episode_index"] = episode_index
            meta["execution_context"] = exec_ctx

            # Inject scene-level brain strategy
            strategy = scene_strategy[i] if i < len(scene_strategy) else {}
            if strategy.get("scene_goal"):
                meta["scene_goal"] = strategy["scene_goal"]
            if strategy.get("pacing_weight") is not None:
                meta["pacing_weight"] = strategy["pacing_weight"]

            # Series/episode role
            if episode_role:
                meta["series_role"] = episode_role
            if open_loops:
                meta["open_loop_seed"] = open_loops[0]
            if callbacks:
                meta["callback_to_previous_episode"] = callbacks[0]
            if winner_refs:
                meta["winner_pattern_ref"] = winner_refs[0]
            if winner_dna.get("top_pattern_id"):
                meta["continuity_constraints"] = {
                    "preserve_avatar_identity": True,
                    "winner_dna_ref": winner_dna.get("top_pattern_id"),
                }
            meta["brain_plan_ref"] = "inline"

            updated["metadata"] = meta
            enriched.append(updated)

        return enriched
