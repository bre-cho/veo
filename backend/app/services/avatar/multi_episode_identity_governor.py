"""MultiEpisodeIdentityGovernor — cross-episode avatar identity governance.

Phase 2.5 (v16): Tracks avatar visual identity continuity across multiple
episodes of a series, detecting long-term drift and enforcing identity
consistency at the series level (not just per-render).

Key capabilities:
- ``record_episode_identity()``: store the embedding snapshot for an episode.
- ``score_series_identity()``: compute cross-episode identity consistency.
- ``detect_identity_regression()``: identify specific episodes where the
  avatar's appearance diverged significantly from the series baseline.
- ``get_governance_report()``: full identity governance report for a series.

Usage::

    governor = MultiEpisodeIdentityGovernor()

    # After each episode render:
    governor.record_episode_identity(
        series_id="series-001",
        avatar_id="av-123",
        episode_number=3,
        embedding=render_embedding,
    )

    # Governance report for the whole series:
    report = governor.get_governance_report("series-001", "av-123")
    # report["identity_stable"] → bool
    # report["regression_episodes"] → [4, 7]  (episode numbers with drift)
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

# Cosine similarity threshold below which an episode is flagged as drifted
_EPISODE_DRIFT_THRESHOLD = 0.75
# Maximum acceptable fraction of episodes with drift before declaring instability
_MAX_DRIFT_FRACTION = 0.25
# Minimum episodes before computing series-level governance
_MIN_EPISODES_FOR_GOVERNANCE = 2

# In-memory store: {series_id → {avatar_id → list[episode_record]}}
_SERIES_REGISTRY: dict[str, dict[str, list[dict[str, Any]]]] = {}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two unit vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return round(dot / (norm_a * norm_b), 6)


def _mean_embedding(embeddings: list[list[float]]) -> list[float]:
    """Compute the element-wise mean of a list of embeddings."""
    if not embeddings:
        return []
    dim = len(embeddings[0])
    avg = [sum(e[i] for e in embeddings) / len(embeddings) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in avg)) or 1.0
    return [round(x / norm, 6) for x in avg]


class MultiEpisodeIdentityGovernor:
    """Track and govern avatar identity across multiple episodes.

    All state is held in-process (``_SERIES_REGISTRY``).  A ``db`` session
    can be provided for future persistence; the interface is already defined.
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_episode_identity(
        self,
        series_id: str,
        avatar_id: str,
        episode_number: int,
        embedding: list[float],
        render_url: str | None = None,
        quality_score: float | None = None,
    ) -> dict[str, Any]:
        """Record the avatar's identity embedding for a completed episode.

        Args:
            series_id: Series identifier.
            avatar_id: Avatar identifier.
            episode_number: Episode number (1-based).
            embedding: Per-episode mean embedding extracted from the render.
            render_url: Optional URL of the render output.
            quality_score: Optional quality score ∈ [0, 1].

        Returns:
            Dict with ``recorded``, ``series_id``, ``episode_number``.
        """
        record = {
            "episode_number": episode_number,
            "embedding": embedding,
            "render_url": render_url,
            "quality_score": quality_score,
            "recorded_at": time.time(),
        }
        _SERIES_REGISTRY.setdefault(series_id, {}).setdefault(avatar_id, [])
        # Overwrite if episode already recorded
        episodes = _SERIES_REGISTRY[series_id][avatar_id]
        existing = [i for i, e in enumerate(episodes) if e["episode_number"] == episode_number]
        if existing:
            episodes[existing[0]] = record
        else:
            episodes.append(record)

        return {"recorded": True, "series_id": series_id, "episode_number": episode_number}

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------

    def score_series_identity(
        self,
        series_id: str,
        avatar_id: str,
    ) -> float:
        """Compute overall cross-episode identity consistency ∈ [0, 1].

        Uses the mean of all episode embeddings as the series baseline and
        measures how consistently each episode aligns to it.

        Returns 1.0 when there are fewer than ``_MIN_EPISODES_FOR_GOVERNANCE``
        episodes (trivially consistent).
        """
        episodes = self._get_episodes(series_id, avatar_id)
        if len(episodes) < _MIN_EPISODES_FOR_GOVERNANCE:
            return 1.0

        embeddings = [ep["embedding"] for ep in episodes if ep.get("embedding")]
        if not embeddings:
            return 1.0

        baseline = _mean_embedding(embeddings)
        sims = [_cosine_similarity(baseline, emb) for emb in embeddings]
        return round(sum(sims) / len(sims), 4)

    def detect_identity_regression(
        self,
        series_id: str,
        avatar_id: str,
    ) -> list[int]:
        """Return episode numbers where identity drift exceeds the threshold.

        Compares each episode's embedding to the series-level mean embedding.
        Returns a sorted list of episode numbers flagged as drifted.
        """
        episodes = self._get_episodes(series_id, avatar_id)
        if len(episodes) < _MIN_EPISODES_FOR_GOVERNANCE:
            return []

        embeddings = [ep["embedding"] for ep in episodes if ep.get("embedding")]
        if not embeddings:
            return []

        baseline = _mean_embedding(embeddings)
        drifted: list[int] = []
        for ep in episodes:
            emb = ep.get("embedding")
            if emb and _cosine_similarity(baseline, emb) < _EPISODE_DRIFT_THRESHOLD:
                drifted.append(ep["episode_number"])
        return sorted(drifted)

    def get_governance_report(
        self,
        series_id: str,
        avatar_id: str,
    ) -> dict[str, Any]:
        """Return a full identity governance report for a series.

        Returns:
            Dict with:
            - ``series_id``, ``avatar_id``
            - ``episode_count``: number of recorded episodes
            - ``series_identity_score``: overall consistency ∈ [0, 1]
            - ``identity_stable``: True when score ≥ _EPISODE_DRIFT_THRESHOLD
              and drift fraction ≤ _MAX_DRIFT_FRACTION
            - ``regression_episodes``: list of episode numbers with drift
            - ``drift_fraction``: fraction of episodes with drift
            - ``per_episode_scores``: list of {episode_number, similarity}
            - ``recommendation``: actionable guidance
        """
        episodes = self._get_episodes(series_id, avatar_id)
        episode_count = len(episodes)

        if episode_count < _MIN_EPISODES_FOR_GOVERNANCE:
            return {
                "series_id": series_id,
                "avatar_id": avatar_id,
                "episode_count": episode_count,
                "series_identity_score": 1.0,
                "identity_stable": True,
                "regression_episodes": [],
                "drift_fraction": 0.0,
                "per_episode_scores": [],
                "recommendation": "Collect more episodes before governance assessment.",
            }

        embeddings = [ep["embedding"] for ep in episodes if ep.get("embedding")]
        baseline = _mean_embedding(embeddings) if embeddings else []

        per_ep_scores: list[dict[str, Any]] = []
        drifted: list[int] = []
        for ep in sorted(episodes, key=lambda e: e["episode_number"]):
            emb = ep.get("embedding")
            if emb and baseline:
                sim = _cosine_similarity(baseline, emb)
            else:
                sim = 1.0
            per_ep_scores.append({
                "episode_number": ep["episode_number"],
                "similarity": round(sim, 4),
                "drifted": sim < _EPISODE_DRIFT_THRESHOLD,
            })
            if sim < _EPISODE_DRIFT_THRESHOLD:
                drifted.append(ep["episode_number"])

        series_score = self.score_series_identity(series_id, avatar_id)
        drift_fraction = round(len(drifted) / max(episode_count, 1), 4)
        stable = series_score >= _EPISODE_DRIFT_THRESHOLD and drift_fraction <= _MAX_DRIFT_FRACTION

        # Recommendation
        if stable:
            rec = "Identity is stable across episodes. No action required."
        elif drift_fraction > _MAX_DRIFT_FRACTION:
            rec = (
                f"High identity drift detected in {len(drifted)} episode(s) "
                f"({drifted}). Re-render with stricter identity gate or refresh canonical reference."
            )
        else:
            rec = "Minor identity variance observed. Monitor next episodes."

        return {
            "series_id": series_id,
            "avatar_id": avatar_id,
            "episode_count": episode_count,
            "series_identity_score": series_score,
            "identity_stable": stable,
            "regression_episodes": drifted,
            "drift_fraction": drift_fraction,
            "per_episode_scores": per_ep_scores,
            "recommendation": rec,
        }

    def clear_series(self, series_id: str, avatar_id: str | None = None) -> None:
        """Remove all identity records for a series (or specific avatar)."""
        if series_id not in _SERIES_REGISTRY:
            return
        if avatar_id is not None:
            _SERIES_REGISTRY[series_id].pop(avatar_id, None)
        else:
            del _SERIES_REGISTRY[series_id]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_episodes(
        self, series_id: str, avatar_id: str
    ) -> list[dict[str, Any]]:
        """Return all recorded episodes for (series_id, avatar_id)."""
        return _SERIES_REGISTRY.get(series_id, {}).get(avatar_id, [])
