"""NarrativeArcDirector — cross-episode narrative arc planning and synthesis.

Director OS Full-Power leap for the storyboard/director layer.

This module provides:
1. **Cross-episode arc planning** — track multi-episode story arcs (e.g.
   introduction → tension → resolution → reward across 4–12 episodes) and
   emit per-episode scene recommendations aligned to the arc phase.

2. **Performance-driven scene synthesis** — analyse per-episode performance
   signals from the learning store and synthesise a recommended scene
   composition (goals, pacing weights, hook intensity) for the *next* episode
   that maximises predicted retention and conversion.

3. **Visual style evolution** — govern how the avatar's visual style and
   production aesthetics evolve across episodes (gradual style drift, seasonal
   theming, callback motifs).

4. **Narrative A/B experiment tracking** — register competing narrative
   strategies for a series, track outcomes, and surface a winner when
   statistical confidence is reached.

Usage::

    director = NarrativeArcDirector()

    # Plan the arc for a 6-episode series
    arc = director.plan_arc(
        series_id="series-001",
        total_episodes=6,
        arc_type="transformation",
    )

    # Get recommendations for episode 3
    rec = director.recommend_next_episode(
        series_id="series-001",
        completed_episodes=[episode1, episode2],
        learning_store=engine,
        platform="tiktok",
    )

    # Register narrative A/B variant
    director.register_narrative_experiment(
        series_id="series-001",
        variant_a={"arc_type": "transformation"},
        variant_b={"arc_type": "authority"},
    )
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Arc type definitions
# ---------------------------------------------------------------------------

# Each arc type maps to an ordered sequence of episode phases.  Each phase has
# a recommended dominant scene_goal distribution and a pacing profile.
_ARC_TYPES: dict[str, list[dict[str, Any]]] = {
    "transformation": [
        {"phase": "introduction", "dominant_goals": ["hook", "body"], "hook_intensity": 1.4, "cta_emphasis": 0.3},
        {"phase": "challenge", "dominant_goals": ["tension", "body"], "hook_intensity": 1.5, "cta_emphasis": 0.2},
        {"phase": "turning_point", "dominant_goals": ["reveal", "body"], "hook_intensity": 1.6, "cta_emphasis": 0.5},
        {"phase": "resolution", "dominant_goals": ["social_proof", "cta"], "hook_intensity": 1.2, "cta_emphasis": 0.9},
    ],
    "authority": [
        {"phase": "credibility_build", "dominant_goals": ["hook", "body"], "hook_intensity": 1.3, "cta_emphasis": 0.2},
        {"phase": "deep_value", "dominant_goals": ["body", "body"], "hook_intensity": 1.0, "cta_emphasis": 0.3},
        {"phase": "proof_stack", "dominant_goals": ["social_proof", "reveal"], "hook_intensity": 1.2, "cta_emphasis": 0.6},
        {"phase": "conversion_push", "dominant_goals": ["cta", "social_proof"], "hook_intensity": 1.1, "cta_emphasis": 1.0},
    ],
    "story": [
        {"phase": "inciting_incident", "dominant_goals": ["hook", "tension"], "hook_intensity": 1.6, "cta_emphasis": 0.1},
        {"phase": "rising_action", "dominant_goals": ["body", "tension"], "hook_intensity": 1.3, "cta_emphasis": 0.2},
        {"phase": "climax", "dominant_goals": ["reveal", "tension"], "hook_intensity": 1.8, "cta_emphasis": 0.4},
        {"phase": "falling_action", "dominant_goals": ["body", "social_proof"], "hook_intensity": 1.1, "cta_emphasis": 0.6},
        {"phase": "resolution", "dominant_goals": ["cta", "social_proof"], "hook_intensity": 1.0, "cta_emphasis": 1.0},
    ],
    "education": [
        {"phase": "hook_question", "dominant_goals": ["hook"], "hook_intensity": 1.5, "cta_emphasis": 0.1},
        {"phase": "framework", "dominant_goals": ["body", "body"], "hook_intensity": 1.0, "cta_emphasis": 0.2},
        {"phase": "deep_dive", "dominant_goals": ["body", "reveal"], "hook_intensity": 1.0, "cta_emphasis": 0.3},
        {"phase": "synthesis", "dominant_goals": ["body", "social_proof"], "hook_intensity": 1.1, "cta_emphasis": 0.5},
        {"phase": "next_step", "dominant_goals": ["cta"], "hook_intensity": 1.2, "cta_emphasis": 1.0},
    ],
}

_DEFAULT_ARC_TYPE = "transformation"

# Minimum confidence to declare a narrative A/B winner
_NARRATIVE_WINNER_MIN_CONFIDENCE = 0.80
# Minimum episodes per variant before declaring a winner
_NARRATIVE_WINNER_MIN_EPISODES = 3

# In-memory registry of series arcs and A/B experiments
_ARC_REGISTRY: dict[str, dict[str, Any]] = {}
_EXPERIMENT_REGISTRY: dict[str, dict[str, Any]] = {}


class NarrativeArcDirector:
    """Plan and direct multi-episode narrative arcs.

    All state is maintained in the in-memory registries so the class works
    without a DB; callers can provide a ``db`` session for persistence.
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Arc planning
    # ------------------------------------------------------------------

    def plan_arc(
        self,
        series_id: str,
        total_episodes: int,
        arc_type: str = _DEFAULT_ARC_TYPE,
        platform: str | None = None,
        market_code: str | None = None,
    ) -> dict[str, Any]:
        """Create an episode-level arc plan for a series.

        Distributes arc phases across ``total_episodes`` and assigns
        per-episode scene composition recommendations.

        Returns:
            Dict with ``series_id``, ``arc_type``, ``total_episodes``,
            ``episode_plans`` (list of per-episode dicts), and
            ``arc_phases`` (phase distribution).
        """
        phases = _ARC_TYPES.get(arc_type, _ARC_TYPES[_DEFAULT_ARC_TYPE])
        n_phases = len(phases)

        episode_plans: list[dict[str, Any]] = []
        for ep_idx in range(1, total_episodes + 1):
            # Map episode index to a phase (distribute evenly)
            phase_idx = min(int((ep_idx - 1) * n_phases / total_episodes), n_phases - 1)
            phase = phases[phase_idx]

            # Compute pacing profile for this episode
            episode_plans.append(
                self._episode_plan(
                    episode_number=ep_idx,
                    phase=phase,
                    platform=platform,
                    total_episodes=total_episodes,
                )
            )

        arc = {
            "series_id": series_id,
            "arc_type": arc_type,
            "total_episodes": total_episodes,
            "platform": platform,
            "market_code": market_code,
            "episode_plans": episode_plans,
            "arc_phases": [p["phase"] for p in phases],
            "created_at": time.time(),
        }
        _ARC_REGISTRY[series_id] = arc
        # Persist to DB when session is available
        self._persist_arc_to_db(arc)
        return arc

    def get_arc(self, series_id: str) -> dict[str, Any] | None:
        """Return the arc plan for a series.

        Checks in-memory registry first; falls back to DB when not found.
        """
        if series_id in _ARC_REGISTRY:
            return _ARC_REGISTRY[series_id]
        return self._load_arc_from_db(series_id)

    # ------------------------------------------------------------------
    # Performance-driven next-episode synthesis
    # ------------------------------------------------------------------

    def recommend_next_episode(
        self,
        series_id: str,
        completed_episodes: list[dict[str, Any]],
        learning_store: Any | None = None,
        platform: str | None = None,
        episode_number: int | None = None,
    ) -> dict[str, Any]:
        """Synthesise scene composition for the next episode.

        Uses performance signals from ``completed_episodes`` and the
        ``learning_store`` to derive:
        - The recommended arc phase
        - Hook intensity and pacing weights
        - Dominant scene goals
        - Style evolution hints
        - Winning scene graph injection (shot-level guidance from top graphs)

        Args:
            series_id: The series to plan the next episode for.
            completed_episodes: List of dicts, each with at minimum
                ``episode_number`` and optionally ``conversion_score``,
                ``view_count``, ``hook_pattern``.
            learning_store: ``PerformanceLearningEngine`` for additional signal.
            platform: Target platform.
            episode_number: Override for the next episode number.

        Returns:
            Dict with ``series_id``, ``next_episode_number``,
            ``recommended_phase``, ``scene_composition``,
            ``style_evolution``, ``performance_insights``,
            and ``winning_shot_guidance`` (from CinematicMemoryStore / WinningSceneGraphStore).
        """
        arc = self.get_arc(series_id)
        next_ep = episode_number or (len(completed_episodes) + 1)

        # Performance insights from completed episodes
        perf_insights = self._analyse_episode_performance(
            completed_episodes, learning_store, platform
        )

        # Inject CinematicMemoryStore shot analytics for series-level enrichment
        shot_analytics: dict[str, Any] = {}
        try:
            from app.services.storyboard.cinematic_memory_store import CinematicMemoryStore
            cinematic = CinematicMemoryStore(db=self._db)
            shot_analytics = cinematic.get_series_shot_analytics(series_id)
        except Exception as exc:
            logger.debug("NarrativeArcDirector: shot analytics failed: %s", exc)

        # Inject winner weight profile from VariantHistoryService for conversion signal
        winner_profile: dict[str, Any] = {}
        try:
            if self._db is not None:
                from app.services.variant_history_service import VariantHistoryService
                vhs = VariantHistoryService()
                winner_profile = vhs.get_winner_weight_profile(self._db, series_id)
        except Exception as exc:
            logger.debug("NarrativeArcDirector: winner profile failed: %s", exc)

        # Determine recommended phase
        if arc:
            ep_plans = arc.get("episode_plans", [])
            if next_ep <= len(ep_plans):
                phase_rec = ep_plans[next_ep - 1]
            else:
                # Beyond planned episodes: use final phase
                phase_rec = ep_plans[-1] if ep_plans else {}
        else:
            # No arc registered: infer phase from episode number
            phase_rec = self._infer_phase(next_ep, perf_insights)

        # Blend arc recommendation with performance signals
        scene_composition = self._synthesise_scene_composition(
            phase_rec=phase_rec,
            perf_insights=perf_insights,
            platform=platform,
            shot_analytics=shot_analytics,
            winner_profile=winner_profile,
        )

        # Style evolution hint
        style_evolution = self._compute_style_evolution(
            completed_episodes=completed_episodes,
            next_ep=next_ep,
        )

        # Winning shot guidance from CinematicMemoryStore and WinningSceneGraphStore
        winning_shot_guidance = self._get_winning_shot_guidance(series_id, platform)

        # Inject winning graph scene sequence into scene_composition when available
        if winning_shot_guidance.get("winning_scene_sequence"):
            scene_composition["winning_scene_sequence"] = winning_shot_guidance["winning_scene_sequence"]

        return {
            "series_id": series_id,
            "next_episode_number": next_ep,
            "recommended_phase": phase_rec.get("phase", "body"),
            "scene_composition": scene_composition,
            "style_evolution": style_evolution,
            "performance_insights": perf_insights,
            "arc_type": arc.get("arc_type") if arc else "inferred",
            "winning_shot_guidance": winning_shot_guidance,
            "shot_analytics": shot_analytics,
            "winner_profile": winner_profile,
        }

    # ------------------------------------------------------------------
    # Narrative A/B experiments
    # ------------------------------------------------------------------

    def register_narrative_experiment(
        self,
        series_id: str,
        variant_a: dict[str, Any],
        variant_b: dict[str, Any],
    ) -> dict[str, Any]:
        """Register an A/B experiment comparing two narrative strategies.

        Returns:
            Dict with ``experiment_id``, ``series_id``, ``variant_a``,
            ``variant_b``, and ``status`` ("running").
        """
        import uuid as _uuid
        exp_id = str(_uuid.uuid4())
        experiment = {
            "experiment_id": exp_id,
            "series_id": series_id,
            "variant_a": {**variant_a, "episodes": [], "scores": []},
            "variant_b": {**variant_b, "episodes": [], "scores": []},
            "status": "running",
            "winner": None,
            "created_at": time.time(),
        }
        _EXPERIMENT_REGISTRY[exp_id] = experiment
        return {k: v for k, v in experiment.items() if k not in ("variant_a", "variant_b")}

    def record_episode_outcome(
        self,
        experiment_id: str,
        variant: str,
        episode_number: int,
        conversion_score: float,
    ) -> dict[str, Any]:
        """Record an episode outcome for an A/B experiment variant.

        Args:
            experiment_id: The experiment to update.
            variant: "a" or "b".
            episode_number: The episode number.
            conversion_score: Measured conversion score ∈ [0, 1].

        Returns:
            Updated experiment dict including ``winner`` when confidence is met.
        """
        exp = _EXPERIMENT_REGISTRY.get(experiment_id)
        if exp is None:
            return {"error": "experiment_not_found"}

        key = f"variant_{variant.lower()}"
        if key not in exp:
            return {"error": "invalid_variant"}

        exp[key]["episodes"].append(episode_number)
        exp[key]["scores"].append(float(conversion_score))

        # Check for winner
        winner = self._evaluate_winner(exp)
        if winner:
            exp["winner"] = winner
            exp["status"] = "concluded"

        return exp

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        """Return an experiment by ID."""
        return _EXPERIMENT_REGISTRY.get(experiment_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _episode_plan(
        episode_number: int,
        phase: dict[str, Any],
        platform: str | None,
        total_episodes: int,
    ) -> dict[str, Any]:
        """Build per-episode plan from phase and platform context."""
        hook_intensity = float(phase.get("hook_intensity", 1.3))
        cta_emphasis = float(phase.get("cta_emphasis", 0.5))
        dominant_goals = list(phase.get("dominant_goals", ["hook", "body", "cta"]))

        # For short-form platforms (tiktok/reels/shorts), boost hook intensity
        if platform and platform.lower() in ("tiktok", "reels", "shorts"):
            hook_intensity = min(hook_intensity * 1.1, 2.0)

        # In later episodes, gradually increase CTA emphasis
        episode_progress = episode_number / max(total_episodes, 1)
        cta_emphasis = min(1.0, cta_emphasis + episode_progress * 0.2)

        return {
            "episode_number": episode_number,
            "phase": phase.get("phase", "body"),
            "dominant_goals": dominant_goals,
            "hook_intensity": round(hook_intensity, 2),
            "cta_emphasis": round(cta_emphasis, 2),
            "recommended_pacing": "fast" if hook_intensity > 1.4 else "moderate",
        }

    def _analyse_episode_performance(
        self,
        episodes: list[dict[str, Any]],
        learning_store: Any | None,
        platform: str | None,
    ) -> dict[str, Any]:
        """Derive performance insights from completed episodes."""
        if not episodes:
            return {
                "avg_conversion_score": 0.5,
                "trend": "stable",
                "best_hook_pattern": None,
                "episode_count": 0,
            }

        conversion_scores = [float(ep.get("conversion_score", 0.5)) for ep in episodes]
        avg_score = sum(conversion_scores) / len(conversion_scores)

        # Trend: compare last half vs first half
        half = len(conversion_scores) // 2
        if half > 0:
            first_mean = sum(conversion_scores[:half]) / half
            second_mean = sum(conversion_scores[half:]) / max(len(conversion_scores) - half, 1)
            trend = "improving" if second_mean > first_mean + 0.05 else (
                "declining" if second_mean < first_mean - 0.05 else "stable"
            )
        else:
            trend = "stable"

        # Best hook pattern from learning store
        best_hook = None
        if learning_store is not None:
            try:
                top_hooks = learning_store.top_hook_patterns(
                    platform=platform, min_records=1
                )
                if top_hooks:
                    best_hook = top_hooks[0].get("hook_pattern")
            except Exception:
                pass

        return {
            "avg_conversion_score": round(avg_score, 4),
            "trend": trend,
            "best_hook_pattern": best_hook,
            "episode_count": len(episodes),
            "scores": conversion_scores,
        }

    @staticmethod
    def _synthesise_scene_composition(
        phase_rec: dict[str, Any],
        perf_insights: dict[str, Any],
        platform: str | None,
        shot_analytics: dict[str, Any] | None = None,
        winner_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Blend arc phase recommendation with performance signal."""
        dominant_goals = list(phase_rec.get("dominant_goals", ["hook", "body", "cta"]))
        hook_intensity = float(phase_rec.get("hook_intensity", 1.3))
        cta_emphasis = float(phase_rec.get("cta_emphasis", 0.5))

        # Boost hook intensity when trend is declining
        if perf_insights.get("trend") == "declining":
            hook_intensity = min(hook_intensity + 0.2, 2.0)

        # Add social_proof when avg score is below 0.5
        if float(perf_insights.get("avg_conversion_score", 0.5)) < 0.5:
            if "social_proof" not in dominant_goals:
                dominant_goals.append("social_proof")

        # Short-form: ensure hook is first, cta is last
        if platform and platform.lower() in ("tiktok", "reels", "shorts"):
            if "hook" not in dominant_goals:
                dominant_goals.insert(0, "hook")
            if "cta" not in dominant_goals:
                dominant_goals.append("cta")

        # Scene asset strategy: hint from shot analytics top asset bundle
        _analytics = shot_analytics or {}
        scene_asset_strategy: dict[str, Any] = {
            "top_asset_bundle": _analytics.get("top_asset_bundle"),
            "retention_best_config": _analytics.get("retention_best_config"),
        }

        # Shot config strategy: preferred shot config from winner profile
        _winner = winner_profile or {}
        shot_config_strategy: dict[str, Any] = {
            "platform": _winner.get("platform"),
            "recommended_rollout_stage": _winner.get("recommended_rollout_stage"),
            "segment_key": _winner.get("segment_key"),
        }

        # Continuity constraints: don't violate arc phase ordering
        continuity_constraints = {
            "arc_phase": phase_rec.get("phase"),
            "enforce_hook_first": platform and platform.lower() in ("tiktok", "reels", "shorts"),
            "min_hook_intensity": round(hook_intensity * 0.8, 2),
        }

        return {
            "dominant_goals": dominant_goals,
            "hook_intensity": round(hook_intensity, 2),
            "cta_emphasis": round(cta_emphasis, 2),
            "best_hook_pattern": perf_insights.get("best_hook_pattern"),
            "recommended_pacing_weights": {
                "hook": round(hook_intensity, 2),
                "body": 0.9,
                "cta": round(min(1.0 + cta_emphasis * 0.5, 1.8), 2),
            },
            "scene_asset_strategy": scene_asset_strategy,
            "shot_config_strategy": shot_config_strategy,
            "continuity_constraints": continuity_constraints,
        }

    @staticmethod
    def _compute_style_evolution(
        completed_episodes: list[dict[str, Any]],
        next_ep: int,
    ) -> dict[str, Any]:
        """Govern visual style evolution across episodes.

        Returns hints for the next episode's visual treatment, gradually
        evolving production aesthetics while maintaining identity continuity.
        """
        # Style maturity: early episodes lean minimal; later episodes add depth
        style_maturity = min(1.0, next_ep / 10.0)

        # Motif callback: reference an early-episode visual motif from ep 1-2
        callback_motif = None
        if next_ep > 3 and completed_episodes:
            first_ep = completed_episodes[0] if completed_episodes else {}
            callback_motif = first_ep.get("visual_motif") or first_ep.get("hook_pattern")

        # Colour evolution: season-aware hint (cycle through 4 quarters)
        month = int(time.localtime().tm_mon)
        season_map = {1: "cool", 2: "cool", 3: "warm", 4: "warm",
                      5: "vibrant", 6: "vibrant", 7: "warm", 8: "warm",
                      9: "earthy", 10: "earthy", 11: "cool", 12: "cool"}
        colour_theme = season_map.get(month, "neutral")

        return {
            "style_maturity": round(style_maturity, 2),
            "callback_motif": callback_motif,
            "colour_theme": colour_theme,
            "production_depth": "rich" if style_maturity > 0.6 else "clean",
        }

    @staticmethod
    def _infer_phase(episode_number: int, perf_insights: dict[str, Any]) -> dict[str, Any]:
        """Infer arc phase when no arc is registered."""
        if episode_number <= 2:
            return {"phase": "introduction", "dominant_goals": ["hook", "body"], "hook_intensity": 1.4, "cta_emphasis": 0.3}
        if perf_insights.get("trend") == "improving":
            return {"phase": "momentum", "dominant_goals": ["body", "reveal"], "hook_intensity": 1.3, "cta_emphasis": 0.6}
        return {"phase": "conversion_push", "dominant_goals": ["reveal", "cta", "social_proof"], "hook_intensity": 1.2, "cta_emphasis": 0.9}

    @staticmethod
    def _evaluate_winner(experiment: dict[str, Any]) -> str | None:
        """Return the winning variant or None when confidence is not yet met."""
        va_scores = experiment["variant_a"].get("scores", [])
        vb_scores = experiment["variant_b"].get("scores", [])
        if len(va_scores) < _NARRATIVE_WINNER_MIN_EPISODES or len(vb_scores) < _NARRATIVE_WINNER_MIN_EPISODES:
            return None

        mean_a = sum(va_scores) / len(va_scores)
        mean_b = sum(vb_scores) / len(vb_scores)
        combined = va_scores + vb_scores
        if not combined:
            return None

        overall_mean = sum(combined) / len(combined)
        if overall_mean == 0:
            return None

        # Simple confidence proxy: normalised difference
        diff = abs(mean_a - mean_b)
        confidence = min(1.0, diff / (overall_mean + 1e-9) * 5)

        if confidence >= _NARRATIVE_WINNER_MIN_CONFIDENCE:
            return "a" if mean_a > mean_b else "b"
        return None

    # ------------------------------------------------------------------
    # DB persistence helpers (full-power arc persistence)
    # ------------------------------------------------------------------

    def _persist_arc_to_db(self, arc: dict[str, Any]) -> None:
        """Persist an arc plan to the DB via EpisodeMemory rows (best-effort).

        Stores the arc as a single EpisodeMemory record with
        ``memory_type="narrative_arc"`` and the full arc dict as payload.
        """
        if self._db is None:
            return
        try:
            from app.models.episode_memory import EpisodeMemory  # type: ignore[import]
            from datetime import datetime, timezone

            # Upsert: remove existing arc record for this series_id before inserting
            existing = (
                self._db.query(EpisodeMemory)
                .filter(
                    EpisodeMemory.series_id == arc["series_id"],
                    EpisodeMemory.memory_type == "narrative_arc",
                )
                .first()
            )
            if existing:
                existing.payload = arc
                existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                self._db.add(existing)
            else:
                row = EpisodeMemory(
                    series_id=arc["series_id"],
                    episode_number=0,  # 0 signals series-level record
                    memory_type="narrative_arc",
                    payload=arc,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                self._db.add(row)
            self._db.commit()
        except Exception as exc:
            logger.debug("NarrativeArcDirector._persist_arc_to_db failed: %s", exc)

    def _load_arc_from_db(self, series_id: str) -> dict[str, Any] | None:
        """Load an arc plan from the DB and populate the in-memory registry."""
        if self._db is None:
            return None
        try:
            from app.models.episode_memory import EpisodeMemory  # type: ignore[import]

            row = (
                self._db.query(EpisodeMemory)
                .filter(
                    EpisodeMemory.series_id == series_id,
                    EpisodeMemory.memory_type == "narrative_arc",
                )
                .first()
            )
            if row and row.payload:
                arc = dict(row.payload)
                _ARC_REGISTRY[series_id] = arc
                return arc
        except Exception as exc:
            logger.debug("NarrativeArcDirector._load_arc_from_db failed: %s", exc)
        return None

    def _get_winning_shot_guidance(
        self,
        series_id: str,
        platform: str | None,
    ) -> dict[str, Any]:
        """Return winning shot / scene guidance from CinematicMemoryStore and WinningSceneGraphStore.

        Combines:
        1. Top-N winning scene sequence from WinningSceneGraphStore (global).
        2. Per-goal shot config from CinematicMemoryStore (series-level).

        Returns:
            Dict with ``winning_scene_sequence``, ``per_goal_shot_config``,
            ``source``.
        """
        winning_scene_sequence: list[dict] | None = None
        per_goal_shot_config: dict[str, Any] = {}

        # WinningSceneGraphStore: top graph for this platform
        try:
            from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore
            graph_store = WinningSceneGraphStore(db=self._db)
            top_graphs = graph_store.get_top_graphs(platform=platform, limit=1)
            if top_graphs:
                winning_scene_sequence = top_graphs[0].get("scene_sequence")
        except Exception as exc:
            logger.debug("NarrativeArcDirector: WinningSceneGraphStore lookup failed: %s", exc)

        # CinematicMemoryStore: per-goal shot configs
        analytics: dict[str, Any] = {}
        try:
            from app.services.storyboard.cinematic_memory_store import CinematicMemoryStore
            cinematic_store = CinematicMemoryStore(db=self._db)
            analytics = cinematic_store.get_series_shot_analytics(series_id)
            per_goal_shot_config = analytics.get("per_goal_best_config", {})
        except Exception as exc:
            logger.debug("NarrativeArcDirector: CinematicMemoryStore lookup failed: %s", exc)

        return {
            "winning_scene_sequence": winning_scene_sequence,
            "per_goal_shot_config": per_goal_shot_config,
            "source": "cinematic_memory+winning_graph",
            "recommended_asset_bundle": analytics.get("top_asset_bundle") if per_goal_shot_config else None,
            "retention_safe_transition_style": (
                (analytics.get("retention_best_config") or {}).get("transition")
                if per_goal_shot_config else None
            ),
        }
