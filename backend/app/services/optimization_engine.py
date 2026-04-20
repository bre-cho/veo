from __future__ import annotations

from typing import Any

from app.schemas.optimization import OptimizationInput, OptimizationResponse, OptimizationSuggestion


class OptimizationEngine:
    def analyze(self, data: OptimizationInput) -> OptimizationResponse:
        metrics = data.metrics or {}
        suggestions: list[OptimizationSuggestion] = []
        scene_priority_changes: list[dict[str, Any]] = []
        score_delta = 0.0

        hook_score = self._metric(metrics, "hook_strength")
        cta_score = self._metric(metrics, "cta_quality")
        clarity_score = self._metric(metrics, "clarity")
        trust_score = self._metric(metrics, "trust")

        if hook_score < 0.55:
            suggestions.append(
                OptimizationSuggestion(
                    type="hook",
                    priority="high",
                    message="Hook is weak; use a curiosity-led opener with concrete stakes.",
                    target_scene_index=1,
                    replacement_text="What if you could fix this in under 60 seconds?",
                    metadata={"trigger_score": hook_score},
                )
            )
            scene_priority_changes.append({"scene_index": 1, "priority": "high"})
            score_delta += 0.12

        if cta_score < 0.6:
            suggestions.append(
                OptimizationSuggestion(
                    type="cta",
                    priority="high",
                    message="CTA lacks urgency and value framing.",
                    target_scene_index=None,
                    replacement_text="Tap now to unlock the limited launch offer.",
                    metadata={"trigger_score": cta_score},
                )
            )
            score_delta += 0.10

        if clarity_score < 0.6:
            suggestions.append(
                OptimizationSuggestion(
                    type="clarity",
                    priority="medium",
                    message="Message is dense; shorten lines and isolate one claim per scene.",
                    metadata={"trigger_score": clarity_score},
                )
            )
            score_delta += 0.06

        if trust_score < 0.6:
            suggestions.append(
                OptimizationSuggestion(
                    type="trust",
                    priority="medium",
                    message="Add social proof and concrete validation signal.",
                    metadata={"trigger_score": trust_score},
                )
            )
            score_delta += 0.05

        new_hook = (
            "Did you know most creators lose conversions in the first 3 seconds?"
            if hook_score < 0.7
            else None
        )
        new_cta = (
            "Start now and claim your bonus before midnight."
            if cta_score < 0.7
            else None
        )

        return OptimizationResponse(
            rewrite_suggestions=suggestions,
            new_hook_variant=new_hook,
            new_cta_variant=new_cta,
            scene_priority_changes=scene_priority_changes,
            score_delta_estimate=round(score_delta, 3) if suggestions else 0.0,
        )

    def rewrite_preview_payload(
        self,
        preview_payload: dict[str, Any],
        optimization: OptimizationResponse | dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(optimization, dict):
            optimization = OptimizationResponse(**optimization)
        updated = {**preview_payload}
        scenes = [dict(scene) for scene in (updated.get("scenes") or [])]

        for suggestion in optimization.rewrite_suggestions:
            idx = suggestion.target_scene_index
            if idx and 1 <= idx <= len(scenes) and suggestion.replacement_text:
                scene = scenes[idx - 1]
                scene["script_text"] = suggestion.replacement_text
                meta = dict(scene.get("metadata") or {})
                meta.setdefault("optimization_applied", []).append(suggestion.type)
                scene["metadata"] = meta

        if optimization.new_hook_variant and scenes:
            scenes[0]["script_text"] = optimization.new_hook_variant

        if optimization.new_cta_variant and scenes:
            scenes[-1]["script_text"] = optimization.new_cta_variant

        updated["scenes"] = scenes
        updated["optimization_response"] = optimization.model_dump()
        return updated

    @staticmethod
    def _metric(metrics: dict[str, Any], key: str) -> float:
        try:
            return float(metrics.get(key, 0.0))
        except (TypeError, ValueError):
            return 0.0
