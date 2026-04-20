from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.optimization_run import OptimizationRun
from app.schemas.optimization import OptimizationInput, OptimizationResponse, OptimizationSuggestion
from app.schemas.scoring import CandidateScore

# ---------------------------------------------------------------------------
# Scoring weights – centralised here so QA can audit what drives winner selection
# ---------------------------------------------------------------------------
_CANDIDATE_WEIGHTS: dict[str, dict[str, float]] = {
    "hook_cta_boost": {
        "hook_impact": 0.40,
        "cta_impact": 0.35,
        "clarity_impact": 0.15,
        "trust_impact": 0.10,
    },
    "clarity_trust_balance": {
        "hook_impact": 0.20,
        "cta_impact": 0.20,
        "clarity_impact": 0.35,
        "trust_impact": 0.25,
    },
    "aggressive_conversion_push": {
        "hook_impact": 0.30,
        "cta_impact": 0.50,
        "clarity_impact": 0.10,
        "trust_impact": 0.10,
    },
}

# Score multipliers per candidate (kept separately from weights for clarity)
_CANDIDATE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "hook_cta_boost": {
        "hook_impact": 1.0,
        "cta_impact": 1.0,
        "clarity_impact": 1.0,
        "trust_impact": 1.0,
    },
    "clarity_trust_balance": {
        "hook_impact": 0.7,
        "cta_impact": 0.7,
        "clarity_impact": 1.1,
        "trust_impact": 1.05,
    },
    "aggressive_conversion_push": {
        "hook_impact": 0.9,
        "cta_impact": 1.15,
        "clarity_impact": 0.6,
        "trust_impact": 0.6,
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OptimizationEngine:
    def analyze(self, data: OptimizationInput) -> OptimizationResponse:
        metrics = data.metrics or {}
        candidates = self._build_candidates(metrics)
        winner = max(candidates, key=lambda c: c.score_total)

        suggestions = self._candidate_to_suggestions(winner, metrics)
        scene_priority_changes = [{"scene_index": 1, "priority": "high"}] if any(s.type == "hook" for s in suggestions) else []

        return OptimizationResponse(
            rewrite_suggestions=suggestions,
            new_hook_variant="Did you know most creators lose conversions in the first 3 seconds?"
            if self._metric(metrics, "hook_strength") < 0.7
            else None,
            new_cta_variant="Start now and claim your bonus before midnight."
            if self._metric(metrics, "cta_quality") < 0.7
            else None,
            scene_priority_changes=scene_priority_changes,
            score_delta_estimate=round(max(winner.score_total - 0.5, 0.0), 3),
            candidates=candidates,
            winner_candidate_id=winner.candidate_id,
            winner_rationale=winner.rationale,
        )

    def analyze_and_persist(
        self,
        db: Session,
        data: OptimizationInput,
        parent_run_id: str | None = None,
        retry_count: int = 0,
    ) -> OptimizationResponse:
        run = OptimizationRun(
            project_id=data.project_id,
            render_job_id=data.render_job_id,
            status="pending",
            input_payload=data.model_dump(),
            metrics=data.metrics or {},
            output={},
            parent_run_id=parent_run_id,
            retry_count=retry_count,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        run.status = "running"
        run.started_at = _now()
        db.add(run)
        db.commit()

        try:
            result = self.analyze(data)
            result.run_id = run.id
            winner = next((c for c in result.candidates if c.winner_flag), None)
            run.status = "completed"
            run.completed_at = _now()
            run.output_payload = result.model_dump()
            run.score_summary = {
                "winner": winner.model_dump() if winner else None,
                "weights_used": _CANDIDATE_WEIGHTS,
                "winner_rationale": result.winner_rationale,
            }
            run.output = {
                "rewrite_suggestions": [s.model_dump() for s in result.rewrite_suggestions],
                "winner_candidate_id": result.winner_candidate_id,
            }
            db.add(run)
            db.commit()
            return result
        except Exception as exc:
            run.status = "failed"
            run.completed_at = _now()
            run.error_message = str(exc)
            db.add(run)
            db.commit()
            raise

    def rewrite_preview_payload(
        self,
        preview_payload: dict[str, Any],
        optimization: OptimizationResponse | dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(optimization, dict):
            optimization = OptimizationResponse(**optimization)

        # Build updated payload without mutating the original
        updated = {**preview_payload}
        scenes = [dict(scene) for scene in (updated.get("scenes") or [])]

        applied_patches: list[dict[str, Any]] = []

        for suggestion in optimization.rewrite_suggestions:
            idx = suggestion.target_scene_index
            if idx and 1 <= idx <= len(scenes) and suggestion.replacement_text:
                scene = scenes[idx - 1]
                previous_text = scene.get("script_text")
                scene["script_text"] = suggestion.replacement_text
                meta = dict(scene.get("metadata") or {})
                meta.setdefault("optimization_applied", []).append(suggestion.type)
                scene["metadata"] = meta
                applied_patches.append({
                    "scene_index": idx,
                    "suggestion_type": suggestion.type,
                    "previous_text": previous_text,
                    "replacement_text": suggestion.replacement_text,
                })

        if optimization.new_hook_variant and scenes:
            previous_hook = scenes[0].get("script_text")
            scenes[0]["script_text"] = optimization.new_hook_variant
            applied_patches.append({
                "scene_index": 1,
                "suggestion_type": "hook_variant",
                "previous_text": previous_hook,
                "replacement_text": optimization.new_hook_variant,
            })

        if optimization.new_cta_variant and scenes:
            previous_cta = scenes[-1].get("script_text")
            scenes[-1]["script_text"] = optimization.new_cta_variant
            applied_patches.append({
                "scene_index": len(scenes),
                "suggestion_type": "cta_variant",
                "previous_text": previous_cta,
                "replacement_text": optimization.new_cta_variant,
            })

        updated["scenes"] = scenes
        updated["optimization_response"] = optimization.model_dump()
        # Version metadata so downstream can track what was applied
        updated["optimization_patch_version"] = (updated.get("optimization_patch_version") or 0) + 1
        updated["optimization_patches"] = applied_patches
        return updated

    @staticmethod
    def _metric(metrics: dict[str, Any], key: str) -> float:
        try:
            return float(metrics.get(key, 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _build_candidates(self, metrics: dict[str, Any]) -> list[CandidateScore]:
        hook_gap = 1.0 - self._metric(metrics, "hook_strength")
        cta_gap = 1.0 - self._metric(metrics, "cta_quality")
        clarity_gap = 1.0 - self._metric(metrics, "clarity")
        trust_gap = 1.0 - self._metric(metrics, "trust")
        gaps = {
            "hook_impact": hook_gap,
            "cta_impact": cta_gap,
            "clarity_impact": clarity_gap,
            "trust_impact": trust_gap,
        }

        raw: list[CandidateScore] = []
        for candidate_id, weights in _CANDIDATE_WEIGHTS.items():
            multipliers = _CANDIDATE_MULTIPLIERS[candidate_id]
            breakdown = {
                dim: round(gaps[dim] * multipliers[dim], 3)
                for dim in weights
            }
            total = round(sum(breakdown[dim] * weights[dim] for dim in weights), 3)
            raw.append(
                CandidateScore(
                    candidate_id=candidate_id,
                    score_total=total,
                    score_breakdown=breakdown,
                    rationale=self._build_rationale(candidate_id, gaps),
                    metadata={
                        "weights_used": weights,
                        "gaps": {k: round(v, 3) for k, v in gaps.items()},
                    },
                )
            )

        winner_id = max(raw, key=lambda c: c.score_total).candidate_id
        for candidate in raw:
            candidate.winner_flag = candidate.candidate_id == winner_id
        return raw

    @staticmethod
    def _build_rationale(candidate_id: str, gaps: dict[str, float]) -> str:
        dominant = max(gaps, key=lambda k: gaps[k])
        dominant_pct = round(gaps[dominant] * 100)
        rationale_map = {
            "hook_cta_boost": f"Prioritise hook+CTA gains (dominant gap: {dominant} at {dominant_pct}%).",
            "clarity_trust_balance": f"Reduce ambiguity and increase trust before conversion push (dominant gap: {dominant} at {dominant_pct}%).",
            "aggressive_conversion_push": f"Push hard CTA framing and urgency (dominant gap: {dominant} at {dominant_pct}%).",
        }
        return rationale_map.get(candidate_id, "Scored by gap analysis.")

    def _candidate_to_suggestions(
        self,
        winner: CandidateScore,
        metrics: dict[str, Any],
    ) -> list[OptimizationSuggestion]:
        suggestions: list[OptimizationSuggestion] = []
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
                    metadata={"trigger_score": hook_score, "candidate_id": winner.candidate_id},
                )
            )
        if cta_score < 0.6:
            suggestions.append(
                OptimizationSuggestion(
                    type="cta",
                    priority="high",
                    message="CTA lacks urgency and value framing.",
                    replacement_text="Tap now to unlock the limited launch offer.",
                    metadata={"trigger_score": cta_score, "candidate_id": winner.candidate_id},
                )
            )
        if clarity_score < 0.6:
            suggestions.append(
                OptimizationSuggestion(
                    type="clarity",
                    priority="medium",
                    message="Message is dense; shorten lines and isolate one claim per scene.",
                    metadata={"trigger_score": clarity_score, "candidate_id": winner.candidate_id},
                )
            )
        if trust_score < 0.6:
            suggestions.append(
                OptimizationSuggestion(
                    type="trust",
                    priority="medium",
                    message="Add social proof and concrete validation signal.",
                    metadata={"trigger_score": trust_score, "candidate_id": winner.candidate_id},
                )
            )
        return suggestions

    @staticmethod
    def candidate_weights() -> dict[str, Any]:
        """Expose scoring weights for audit / QA inspection."""
        return {k: dict(v) for k, v in _CANDIDATE_WEIGHTS.items()}
