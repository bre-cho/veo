"""brain_decision_engine — deterministic planning pipeline.

Given a BrainIntakeRequest + memory bundle, produces a BrainPlan:
- Classifies the content (topic/script)
- Determines episode role in the series
- Selects winner DNA to apply
- Builds scene strategy + pacing + CTA plan
- Injects open-loop targets and callback targets
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.brain.series_continuity_router import SeriesContinuityRouter

logger = logging.getLogger(__name__)

_CONTINUITY_ROUTER = SeriesContinuityRouter()

_EPISODE_ROLE_SCENE_STRATEGIES: dict[str, list[dict[str, Any]]] = {
    "opener": [
        {"scene_goal": "hook", "pacing_weight": 0.9, "cta_flag": False},
        {"scene_goal": "promise", "pacing_weight": 0.7, "cta_flag": False},
        {"scene_goal": "open_loop", "pacing_weight": 0.8, "cta_flag": False},
    ],
    "escalation": [
        {"scene_goal": "callback", "pacing_weight": 0.6, "cta_flag": False},
        {"scene_goal": "escalation", "pacing_weight": 0.9, "cta_flag": False},
        {"scene_goal": "reveal_tease", "pacing_weight": 0.8, "cta_flag": False},
    ],
    "reveal": [
        {"scene_goal": "callback_payoff", "pacing_weight": 0.7, "cta_flag": False},
        {"scene_goal": "reveal", "pacing_weight": 1.0, "cta_flag": False},
        {"scene_goal": "cta", "pacing_weight": 0.6, "cta_flag": True},
    ],
    "bridge": [
        {"scene_goal": "recap", "pacing_weight": 0.5, "cta_flag": False},
        {"scene_goal": "bridge", "pacing_weight": 0.7, "cta_flag": False},
        {"scene_goal": "tease", "pacing_weight": 0.8, "cta_flag": False},
    ],
    "payoff": [
        {"scene_goal": "resolution", "pacing_weight": 0.8, "cta_flag": False},
        {"scene_goal": "payoff", "pacing_weight": 1.0, "cta_flag": True},
        {"scene_goal": "cta", "pacing_weight": 0.7, "cta_flag": True},
    ],
}


class BrainDecisionEngine:
    """Produce a BrainPlan dict for a given request + memory bundle."""

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
        """Return a BrainPlan-shaped dict."""
        latest_episode_memory = memory_bundle.get("latest_episode_memory")
        winner_dna_summary = memory_bundle.get("winner_dna_summary") or {}
        winner_patterns = memory_bundle.get("winner_patterns") or []

        continuity = _CONTINUITY_ROUTER.resolve(
            series_id=series_id,
            episode_index=episode_index,
            latest_episode_memory=latest_episode_memory,
        )

        episode_role = continuity["episode_role"]
        resolved_series_id = continuity["series_id"]
        resolved_index = continuity["episode_index"]
        unresolved_loops = continuity["unresolved_loops"]
        callback_targets = continuity["callback_targets"]

        scene_strategy = self._build_scene_strategy(
            episode_role=episode_role,
            unresolved_loops=unresolved_loops,
            winner_dna_summary=winner_dna_summary,
            source_type=source_type,
            script_text=script_text,
        )
        pacing_strategy = self._build_pacing_strategy(episode_role, winner_dna_summary)
        cta_strategy = self._build_cta_strategy(
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            winner_dna_summary=winner_dna_summary,
        )

        return {
            "selected_series_id": resolved_series_id,
            "selected_episode_index": resolved_index,
            "episode_role": episode_role,
            "winner_pattern_refs": [p.get("id") for p in winner_patterns if p.get("id")][:3],
            "open_loop_targets": unresolved_loops[:3],
            "callback_targets": callback_targets[:3],
            "scene_strategy": scene_strategy,
            "pacing_strategy": pacing_strategy,
            "cta_strategy": cta_strategy,
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _build_scene_strategy(
        *,
        episode_role: str,
        unresolved_loops: list[str],
        winner_dna_summary: dict[str, Any],
        source_type: str,
        script_text: str | None,
    ) -> list[dict[str, Any]]:
        base = list(_EPISODE_ROLE_SCENE_STRATEGIES.get(episode_role, _EPISODE_ROLE_SCENE_STRATEGIES["opener"]))

        seq_pattern = winner_dna_summary.get("scene_sequence_pattern")
        if seq_pattern:
            for item in base:
                item["winner_pattern_hint"] = seq_pattern

        if unresolved_loops:
            for item in base:
                if item.get("scene_goal") in ("hook", "escalation", "callback"):
                    item.setdefault("open_loop_inject", unresolved_loops[0])

        return base

    @staticmethod
    def _build_pacing_strategy(
        episode_role: str,
        winner_dna_summary: dict[str, Any],
    ) -> dict[str, Any]:
        pacing_pattern = winner_dna_summary.get("pacing_pattern")
        fast_roles = {"opener", "escalation", "reveal"}
        return {
            "overall": "fast" if episode_role in fast_roles else "measured",
            "pattern_ref": pacing_pattern,
        }

    @staticmethod
    def _build_cta_strategy(
        *,
        content_goal: str | None,
        conversion_mode: str | None,
        winner_dna_summary: dict[str, Any],
    ) -> dict[str, Any]:
        cta_pattern = winner_dna_summary.get("cta_pattern")
        return {
            "content_goal": content_goal,
            "conversion_mode": conversion_mode,
            "cta_pattern_ref": cta_pattern,
            "open_loop_cta": conversion_mode == "series_binge",
        }
