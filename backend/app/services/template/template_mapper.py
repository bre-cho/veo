"""template_mapper — translate a TemplateDefinition into scene strategy and
prompt bias dicts that the render pipeline can consume directly.
"""
from __future__ import annotations

from typing import Any


class TemplateMapper:
    def map_to_scene_strategy(
        self,
        *,
        template_payload: dict[str, Any],
        episode_role: str | None = None,
        brain_plan: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return one entry per scene in the template's scene_sequence.

        Accepts either ``episode_role`` directly or extracts it from the
        legacy ``brain_plan`` dict for backward compatibility.
        """
        if episode_role is None and brain_plan is not None:
            episode_role = brain_plan.get("episode_role")

        sequence = template_payload.get("scene_sequence") or []
        pacing = template_payload.get("pacing_profile") or {}
        shot_profile = template_payload.get("shot_profile") or {}

        mapped: list[dict[str, Any]] = []
        for idx, scene_goal in enumerate(sequence, start=1):
            mapped.append(
                {
                    "scene_index": idx,
                    "scene_goal": scene_goal,
                    "pacing_weight": pacing.get(scene_goal, 1.0),
                    "shot_hint": shot_profile.get(scene_goal),
                    "series_role": episode_role,
                    "template_id": template_payload.get("template_id"),
                    "template_family": template_payload.get("template_family"),
                }
            )
        return mapped

    def map_to_prompt_bias(self, *, template_payload: dict[str, Any]) -> dict[str, Any]:
        """Return the prompt-shaping context that _prepend_context_prompt can use."""
        return {
            "template_id": template_payload.get("template_id"),
            "template_family": template_payload.get("template_family"),
            "narrative_mode": template_payload.get("narrative_mode"),
            "hook_strategy": template_payload.get("hook_strategy"),
            "cta_style": template_payload.get("cta_style"),
            "prompt_bias": template_payload.get("prompt_bias") or {},
        }
