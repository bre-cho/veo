"""brain_manifest_builder — convert brain plan into an enriched preview payload.

For topic input, converts the topic into a draft script then uses the same
helpers as script_ingestion.py (no duplication).

For script input, passes the already-parsed scenes through with brain enrichment.
"""
from __future__ import annotations

from typing import Any

from app.services.avatar.avatar_continuity_engine import AvatarContinuityEngine
from app.services.avatar.avatar_scene_mapper import AvatarSceneMapper
from app.services.avatar.avatar_voice_engine import AvatarVoiceEngine
from app.services.execution_bridge_service import ExecutionBridgeService
from app.services.script_ingestion import (
    build_subtitle_segments_from_scenes,
    normalize_script_text,
    split_script_into_scenes,
)
from app.services.storyboard_engine import StoryboardEngine


class BrainManifestBuilder:
    """Build enriched ScriptPreviewPayload-shaped dicts."""

    def __init__(self) -> None:
        self._execution_bridge = ExecutionBridgeService()
        self._storyboard_engine = StoryboardEngine()
        self._avatar_voice = AvatarVoiceEngine()
        self._avatar_continuity = AvatarContinuityEngine()
        self._avatar_scene_mapper = AvatarSceneMapper()

    def _topic_to_script(self, topic: str, plan: dict[str, Any]) -> str:
        topic = (topic or "").strip()
        role = plan.get("episode_role") or "continuation"
        template_id = ((plan.get("notes") or {}).get("selected_template_id")) or "default_template"
        return "\n".join(
            [
                f"Hook: {topic}",
                f"Escalation: explain why this matters now in a {role} episode.",
                f"Reveal: shape this using template {template_id}.",
                "CTA: tease the next unresolved secret in the series.",
            ]
        ).strip()

    def build_preview_payload(
        self,
        *,
        request: dict[str, Any],
        memory_bundle: dict[str, Any],
        brain_plan: dict[str, Any],
        continuity_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a dict compatible with ScriptPreviewPayload + brain enrichment."""
        source_type = request["source_type"]
        script_text = request.get("script_text")

        if source_type == "topic":
            script_text = self._topic_to_script(request.get("topic") or "", brain_plan)

        normalized = normalize_script_text(script_text or "")
        if not normalized:
            raise ValueError("Brain layer could not build a normalized script")

        scenes = split_script_into_scenes(normalized, max_scenes=12)
        storyboard = self._storyboard_engine.generate_from_script(
            script_text=normalized,
            conversion_mode=request.get("conversion_mode"),
            content_goal=request.get("content_goal"),
            platform=request.get("target_platform"),
            episode_memory={
                "series_id": continuity_context.get("series_id"),
                "episode_index": continuity_context.get("episode_index"),
                "open_loops": continuity_context.get("unresolved_loops"),
                "resolved_loops": continuity_context.get("resolved_loops"),
            },
        )

        storyboard_scenes = {scene.scene_index: scene for scene in storyboard.scenes}
        strategy_by_scene = {
            int(item["scene_index"]): item
            for item in brain_plan.get("scene_strategy") or []
            if item.get("scene_index") is not None
        }

        plan_notes = brain_plan.get("notes") or {}
        template_prompt_bias = plan_notes.get("template_prompt_bias") or {}

        avatar_identity = plan_notes.get("avatar_identity") or request.get("avatar_identity") or {}
        avatar_voice = self._avatar_voice.resolve_voice_context(
            voice_profile=(plan_notes.get("avatar_voice") or request.get("avatar_voice") or {}),
            episode_role=continuity_context.get("episode_role"),
        )
        avatar_continuity = self._avatar_continuity.build_state(
            avatar_id=avatar_identity.get("avatar_id") or request.get("avatar_id"),
            series_id=continuity_context.get("series_id"),
            episode_index=continuity_context.get("episode_index"),
            episode_role=continuity_context.get("episode_role"),
            callback_targets=continuity_context.get("callback_targets") or [],
        ).model_dump()

        enriched_scenes: list[dict[str, Any]] = []
        for scene in scenes:
            scene_index = int(scene.get("scene_index", 0))
            beat = storyboard_scenes.get(scene_index)
            strategy = strategy_by_scene.get(scene_index, {})

            metadata = dict(scene.get("metadata") or {})
            if beat:
                metadata.update(
                    {
                        "scene_goal": beat.scene_goal,
                        "pacing_weight": beat.pacing_weight,
                        "shot_hint": beat.shot_hint,
                        "cta_flag": beat.cta_flag,
                    }
                )
            metadata.update(
                {
                    "series_role": strategy.get("series_role"),
                    "winner_pattern_ref": strategy.get("winner_pattern_ref"),
                    "open_loop_seed": (brain_plan.get("open_loop_targets") or [None])[0],
                    "callback_to_previous_episode": (brain_plan.get("callback_targets") or [None])[0],
                    "continuity_constraints": continuity_context.get("continuity_constraints") or {},
                    # Template-driven hints from scene strategy
                    "template_id": strategy.get("template_id"),
                    "template_family": strategy.get("template_family"),
                    "template_prompt_bias": template_prompt_bias,
                }
            )

            enriched = dict(scene)
            enriched["metadata"] = metadata
            if strategy.get("scene_goal"):
                enriched["scene_goal"] = strategy.get("scene_goal")
            if strategy.get("pacing_weight") is not None:
                enriched["pacing_weight"] = strategy.get("pacing_weight")
            if strategy.get("shot_hint"):
                enriched["shot_hint"] = strategy.get("shot_hint")
            enriched = self._avatar_scene_mapper.apply_to_scene(
                scene=enriched,
                avatar_identity=avatar_identity,
                avatar_voice=avatar_voice,
                avatar_continuity=avatar_continuity,
            )
            # Inject director context if available
            plan_notes_director = brain_plan.get("notes", {}).get("director_plan") or {}
            beats_by_index = {b["scene_index"]: b for b in (plan_notes_director.get("beats") or []) if b.get("scene_index") is not None}
            beat = beats_by_index.get(scene_index) or {}
            if beat:
                enriched["metadata"]["director_intent"] = beat.get("director_intent")
                enriched["metadata"]["dramatic_intent"] = beat.get("dramatic_intent")
                enriched["metadata"]["conflict_type"] = beat.get("conflict_type")
                enriched["metadata"]["emotional_tone"] = beat.get("emotional_tone")
                enriched["metadata"]["beat_type"] = beat.get("beat_type")
            enriched_scenes.append(enriched)

        ctx = self._execution_bridge.resolve_context(
            None,
            avatar_id=request.get("avatar_id"),
            market_code=request.get("market_code"),
            content_goal=request.get("content_goal"),
            conversion_mode=request.get("conversion_mode"),
            storyboard=storyboard.model_dump(),
            winner_patterns=memory_bundle.get("winner_patterns") or [],
            series_id=continuity_context.get("series_id"),
            episode_index=continuity_context.get("episode_index"),
            continuity_context=continuity_context,
            winner_dna_summary=memory_bundle.get("winner_dna_summary"),
            brain_plan=brain_plan,
        )

        bridged_scenes = [
            self._execution_bridge.apply_to_project_scene(scene, ctx)
            for scene in enriched_scenes
        ]
        subtitle_segments = build_subtitle_segments_from_scenes(bridged_scenes)

        return {
            "avatar_id": avatar_identity.get("avatar_id") or request.get("avatar_id"),
            "market_code": request.get("market_code"),
            "content_goal": request.get("content_goal"),
            "conversion_mode": request.get("conversion_mode"),
            "source_mode": "topic_intake" if source_type == "topic" else "script_upload",
            "aspect_ratio": request.get("aspect_ratio"),
            "target_platform": request.get("target_platform"),
            "style_preset": request.get("style_preset"),
            "original_filename": request.get("filename"),
            "script_text": normalized,
            "scenes": bridged_scenes,
            "subtitle_segments": subtitle_segments,
            "storyboard": storyboard.model_dump(),
            "winner_patterns": memory_bundle.get("winner_patterns") or [],
            "series_id": continuity_context.get("series_id"),
            "episode_index": continuity_context.get("episode_index"),
            "brain_plan": brain_plan,
            "continuity_context": continuity_context,
            "winner_dna_summary": memory_bundle.get("winner_dna_summary"),
            "memory_refs": memory_bundle.get("memory_refs") or {},
            "selected_template_id": plan_notes.get("selected_template_id"),
            "selected_template_family": plan_notes.get("selected_template_family"),
            "avatar_identity": avatar_identity,
            "avatar_voice": avatar_voice,
            "avatar_continuity": avatar_continuity,
        }

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
        """Backward-compat wrapper that calls build_preview_payload."""
        continuity_context = {
            "series_id": brain_plan.get("selected_series_id"),
            "episode_index": brain_plan.get("selected_episode_index"),
            "episode_role": brain_plan.get("episode_role"),
            "unresolved_loops": brain_plan.get("open_loop_targets") or [],
            "resolved_loops": [],
            "callback_targets": brain_plan.get("callback_targets") or [],
            "continuity_constraints": {"preserve_avatar_identity": True, "preserve_series_tone": True},
        }
        return self.build_preview_payload(
            request={
                "source_type": source_type,
                "topic": topic,
                "script_text": script_text,
                "filename": filename,
                "aspect_ratio": aspect_ratio,
                "target_platform": target_platform,
                "style_preset": style_preset,
                "avatar_id": avatar_id,
                "market_code": market_code,
                "content_goal": content_goal,
                "conversion_mode": conversion_mode,
            },
            memory_bundle=memory_bundle,
            brain_plan=brain_plan,
            continuity_context=continuity_context,
        )

