"""brain_feedback_service — write render/publish outcomes back to memory."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.episode_memory import EpisodeMemory
from app.schemas.patterns import PatternMemoryIn
from app.services.pattern_library import PatternLibrary
from app.services.template.template_scorecard import classify_template_tier, compute_template_score


class BrainFeedbackService:
    def __init__(self) -> None:
        self._pattern_library = PatternLibrary()

    def record_render_outcome(
        self,
        db: Session | None,
        *,
        project: dict[str, Any] | None,
        render_job_id: str,
        final_video_url: str | None,
        status: str,
    ) -> None:
        if db is None or not project:
            return

        series_id = project.get("series_id")
        episode_index = project.get("episode_index")
        continuity_context = project.get("continuity_context") or {}

        if not series_id or episode_index is None:
            return

        row = EpisodeMemory(
            series_id=str(series_id),
            episode_index=int(episode_index),
            open_loops=continuity_context.get("unresolved_loops") or [],
            resolved_loops=continuity_context.get("resolved_loops") or [],
            winning_scene_sequence=((project.get("brain_plan") or {}).get("scene_strategy") or []),
            series_arc={
                "episode_role": continuity_context.get("episode_role"),
                "render_job_id": render_job_id,
                "status": status,
                "final_video_url": final_video_url,
            },
            character_callbacks=continuity_context.get("callback_targets") or [],
        )
        db.add(row)
        db.commit()

    def record_publish_outcome(
        self,
        db: Session | None,
        *,
        payload: dict[str, Any],
        score: float = 0.5,
    ) -> None:
        if db is None:
            return

        winner_dna = payload.get("winner_dna_summary") or {}
        pattern_payload = {
            "hook_core": winner_dna.get("hook_core"),
            "title_pattern": winner_dna.get("title_pattern"),
            "thumbnail_logic": winner_dna.get("thumbnail_logic"),
            "source_payload": payload,
        }

        self._pattern_library.save(
            db,
            PatternMemoryIn(
                pattern_type="winner_dna",
                market_code=payload.get("market_code"),
                content_goal=payload.get("content_goal"),
                source_id=payload.get("project_id"),
                score=score,
                payload=pattern_payload,
            ),
        )

        # --- Template scorecard + tier classification ---
        raw_metrics: dict[str, Any] = payload.get("metrics") or {}
        derived_score = compute_template_score(raw_metrics)
        total_score = derived_score["total_score"]
        tier = classify_template_tier(total_score)

        # Determine pattern_type from tier
        selected_template_id = payload.get("selected_template_id")
        if tier == "winner":
            template_pattern_type = "template_winner"
        elif tier == "reject":
            template_pattern_type = "template_reject"
        else:
            template_pattern_type = "template_normal"

        if selected_template_id:
            self._pattern_library.save(
                db,
                PatternMemoryIn(
                    pattern_type=template_pattern_type,
                    market_code=payload.get("market_code"),
                    content_goal=payload.get("content_goal"),
                    source_id=payload.get("project_id"),
                    score=total_score / 100.0,  # normalise to [0,1] for PatternMemory
                    payload={
                        "template_id": selected_template_id,
                        "template_family": payload.get("selected_template_family"),
                        "winner_dna_summary": winner_dna,
                        "metrics": raw_metrics,
                        "derived_score": derived_score,
                        "tier": tier,
                        "episode_role": (payload.get("continuity_context") or {}).get("episode_role"),
                        "winning_conditions": {
                            "hook_type": (payload.get("brain_plan") or {}).get("notes", {}).get("hook_type"),
                            "scene_sequence": (payload.get("brain_plan") or {}).get("scene_strategy"),
                            "cta_style": (payload.get("brain_plan") or {}).get("notes", {}).get("cta_style"),
                        },
                    },
                ),
            )

        # --- Trigger evolution when a strong winner is found ---
        if tier == "winner" and selected_template_id and db is not None:
            try:
                self._trigger_evolution(
                    db,
                    winner_payload=payload,
                    total_score=total_score,
                )
            except Exception:
                pass  # evolution is non-fatal

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trigger_evolution(
        self,
        db: Session,
        *,
        winner_payload: dict[str, Any],
        total_score: float,
    ) -> None:
        """Fetch top winner templates from memory and evolve candidates."""
        from app.services.template.template_evolution_engine import TemplateEvolutionEngine

        market_code = winner_payload.get("market_code")
        content_goal = winner_payload.get("content_goal")

        # Retrieve top-2 winners for this niche to enable crossover
        winners_raw = self._pattern_library.list(
            db,
            pattern_type="template_winner",
            market_code=market_code,
            content_goal=content_goal,
        )[:2]

        winner_templates = [w.payload for w in winners_raw if w.payload]
        if not winner_templates:
            return

        # Crossover only when the score is exceptional (>= 90)
        allow_crossover = total_score >= 90.0

        engine = TemplateEvolutionEngine()
        engine.evolve_from_winners(
            db,
            winner_templates=winner_templates,
            market_code=market_code,
            content_goal=content_goal,
            source_id=winner_payload.get("project_id"),
            allow_crossover=allow_crossover,
        )
