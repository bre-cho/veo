"""CinematicMemoryStore — shot-level cinematic memory for the director layer.

Completes the Director OS full-power leap by providing deep shot-level memory
that persists across episodes and series.  Unlike ``LongHorizonContinuityMemory``
(which tracks avatar visual traits), ``CinematicMemoryStore`` tracks the
*production craft* decisions:

- Shot type (close-up, medium, wide, over-shoulder, cutaway)
- Lighting scheme (dramatic, soft, natural, studio)
- Pacing outcome (fast-cut, slow-burn, rhythmic)
- Transition style (hard-cut, dissolve, whip-pan, match-cut)
- Conversion outcome associated with each shot configuration

This enables the director layer to learn *which cinematic choices* correlate
with retention and conversion, going beyond heuristic phase-based planning.

Usage::

    store = CinematicMemoryStore()

    # After each episode render + performance signal:
    store.record_shot(
        series_id="series-001",
        episode_number=3,
        scene_index=1,
        shot_data={
            "shot_type": "close_up",
            "lighting_scheme": "dramatic",
            "transition_style": "hard_cut",
            "pacing_outcome": "fast",
            "conversion_outcome": 0.82,
            "hook_pattern": "question_hook",
        },
    )

    # Get best shot config for a given scene goal:
    config = store.recommend_shot_config(
        series_id="series-001",
        scene_goal="hook",
        platform="tiktok",
    )
    # config["shot_type"] → "close_up"
    # config["lighting_scheme"] → "dramatic"
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Tracked shot dimensions
_SHOT_DIMS = ("shot_type", "lighting_scheme", "transition_style", "pacing_outcome")

# Minimum conversion outcome to consider a shot configuration "winning"
_WIN_CONVERSION_THRESHOLD = 0.65
# Minimum number of shots needed before recommendations are produced
_MIN_SHOTS_FOR_RECOMMENDATION = 3
# Circular buffer: maximum shots per series_id
_MAX_SHOTS_PER_SERIES = 200

# In-memory store: {series_id → list[shot_record]}
_SHOT_STORE: dict[str, list[dict[str, Any]]] = {}


class CinematicMemoryStore:
    """Shot-level cinematic memory store for the director layer.

    All state is maintained in the in-memory ``_SHOT_STORE`` (circular buffer
    per series).  When ``db`` is provided, records are also persisted.
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_shot(
        self,
        series_id: str,
        episode_number: int,
        scene_index: int,
        shot_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Record a shot configuration with its performance outcome.

        Args:
            series_id: Series identifier.
            episode_number: Episode number (1-based).
            scene_index: Scene index within the episode (1-based).
            shot_data: Dict with shot configuration fields.  Expected keys:
                ``shot_type``, ``lighting_scheme``, ``transition_style``,
                ``pacing_outcome``, ``conversion_outcome`` (∈ [0, 1]),
                ``hook_pattern`` (optional).

        Returns:
            Dict with ``recorded`` and ``total_shots`` for the series.
        """
        record = {
            "series_id": series_id,
            "episode_number": episode_number,
            "scene_index": scene_index,
            "shot_type": shot_data.get("shot_type", "medium"),
            "lighting_scheme": shot_data.get("lighting_scheme", "natural"),
            "transition_style": shot_data.get("transition_style", "hard_cut"),
            "pacing_outcome": shot_data.get("pacing_outcome", "moderate"),
            "conversion_outcome": float(shot_data.get("conversion_outcome", 0.5)),
            "hook_pattern": shot_data.get("hook_pattern"),
            "scene_goal": shot_data.get("scene_goal"),
            "platform": shot_data.get("platform"),
            "recorded_at": time.time(),
        }

        _SHOT_STORE.setdefault(series_id, [])
        _SHOT_STORE[series_id].append(record)
        # Circular buffer
        if len(_SHOT_STORE[series_id]) > _MAX_SHOTS_PER_SERIES:
            _SHOT_STORE[series_id] = _SHOT_STORE[series_id][-_MAX_SHOTS_PER_SERIES:]

        total = len(_SHOT_STORE[series_id])

        if self._db is not None:
            self._persist_to_db(record)

        return {"recorded": True, "series_id": series_id, "total_shots": total}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_winning_shots(
        self,
        series_id: str,
        platform: str | None = None,
        scene_goal: str | None = None,
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        """Return the top-N highest-converting shot records.

        Filters by platform and/or scene_goal when provided.

        Returns:
            List of shot records sorted by ``conversion_outcome`` descending.
        """
        shots = _SHOT_STORE.get(series_id, [])
        if platform:
            shots = [s for s in shots if not s.get("platform") or s["platform"] == platform]
        if scene_goal:
            shots = [s for s in shots if not s.get("scene_goal") or s["scene_goal"] == scene_goal]

        winning = [s for s in shots if s["conversion_outcome"] >= _WIN_CONVERSION_THRESHOLD]
        winning.sort(key=lambda x: x["conversion_outcome"], reverse=True)
        return winning[:top_n]

    def recommend_shot_config(
        self,
        series_id: str,
        scene_goal: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Recommend the optimal shot configuration for a given scene goal.

        Uses outcome-weighted ranking: each shot's vote weight is proportional
        to its ``conversion_outcome``, not just presence in the winning set.
        This biases recommendations toward shot configs that produced the
        *highest* conversions, not just those above a threshold.

        Returns:
            Dict with recommended ``shot_type``, ``lighting_scheme``,
            ``transition_style``, ``pacing_outcome``, ``confidence`` ∈ [0, 1],
            ``avg_conversion``, and ``sample_count``.
        """
        shots = _SHOT_STORE.get(series_id, [])
        if platform:
            shots = [s for s in shots if not s.get("platform") or s["platform"] == platform]
        if scene_goal:
            shots = [s for s in shots if not s.get("scene_goal") or s["scene_goal"] == scene_goal]

        if len(shots) < _MIN_SHOTS_FOR_RECOMMENDATION:
            return {
                "shot_type": "medium",
                "lighting_scheme": "natural",
                "transition_style": "hard_cut",
                "pacing_outcome": "moderate",
                "confidence": 0.0,
                "avg_conversion": 0.0,
                "sample_count": len(shots),
                "source": "default_fallback",
            }

        # Outcome-weighted voting: accumulate weight per (dimension, value) pair
        dim_value_weights: dict[str, dict[str, float]] = {dim: {} for dim in _SHOT_DIMS}
        total_weight = 0.0
        for s in shots:
            w = float(s.get("conversion_outcome", 0.5))
            total_weight += w
            for dim in _SHOT_DIMS:
                val = s.get(dim)
                if val:
                    dim_value_weights[dim][val] = dim_value_weights[dim].get(val, 0.0) + w

        recommendation: dict[str, Any] = {}
        for dim in _SHOT_DIMS:
            vw = dim_value_weights[dim]
            if vw:
                best_val = max(vw.keys(), key=lambda v: vw[v])
                recommendation[dim] = best_val
            else:
                recommendation[dim] = "medium" if dim == "shot_type" else "natural"

        # Confidence: mean conversion weighted by sample coverage
        avg_conversion = round(
            sum(s["conversion_outcome"] for s in shots) / len(shots), 4
        )
        winning = [s for s in shots if s["conversion_outcome"] >= _WIN_CONVERSION_THRESHOLD]
        confidence = round(len(winning) / max(len(shots), 1), 4)

        recommendation.update({
            "confidence": confidence,
            "avg_conversion": avg_conversion,
            "sample_count": len(shots),
            "source": "outcome_weighted",
        })
        return recommendation

    def get_series_shot_analytics(self, series_id: str) -> dict[str, Any]:
        """Return analytics on shot configuration performance for a series.

        Returns:
            Dict with ``total_shots``, ``winning_shots``, ``win_rate``,
            ``top_shot_type``, ``top_lighting``, ``avg_conversion``,
            ``per_goal_best_config``.
        """
        shots = _SHOT_STORE.get(series_id, [])
        if not shots:
            return {"series_id": series_id, "total_shots": 0}

        winning = [s for s in shots if s["conversion_outcome"] >= _WIN_CONVERSION_THRESHOLD]
        avg_conv = round(sum(s["conversion_outcome"] for s in shots) / len(shots), 4)

        # Top dimensions from winning shots
        top_shot_type = None
        top_lighting = None
        if winning:
            top_shot_type = Counter(s["shot_type"] for s in winning).most_common(1)[0][0]
            top_lighting = Counter(s["lighting_scheme"] for s in winning).most_common(1)[0][0]

        # Per-goal best config
        goals = {s.get("scene_goal") for s in shots if s.get("scene_goal")}
        per_goal: dict[str, Any] = {}
        for goal in goals:
            per_goal[goal] = self.recommend_shot_config(series_id=series_id, scene_goal=goal)

        return {
            "series_id": series_id,
            "total_shots": len(shots),
            "winning_shots": len(winning),
            "win_rate": round(len(winning) / len(shots), 4),
            "avg_conversion": avg_conv,
            "top_shot_type": top_shot_type,
            "top_lighting": top_lighting,
            "per_goal_best_config": per_goal,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _persist_to_db(self, record: dict[str, Any]) -> None:
        """Persist a shot record to the DB (best-effort)."""
        try:
            from app.models.episode_memory import EpisodeMemory  # type: ignore[import]
            from datetime import datetime, timezone

            row = EpisodeMemory(
                series_id=record["series_id"],
                episode_number=record["episode_number"],
                memory_type="cinematic_shot",
                payload=record,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            self._db.add(row)
            self._db.commit()
        except Exception as exc:
            logger.debug("CinematicMemoryStore._persist_to_db failed: %s", exc)
