"""LongHorizonContinuityMemory — long-horizon avatar continuity memory.

Phase 2.5 (v16): Provides a richer, longer-lived memory store for avatar
appearance continuity that goes beyond the single-episode ``EpisodeMemory``
table:

- Stores per-avatar **visual trait snapshots** across episodes/renders.
- Detects **gradual style drift** (slow, cumulative changes) that would be
  missed by per-render identity gates.
- Surfaces **continuity warnings** before a render is scheduled (pre-render
  check) to guide the render pipeline.
- Maintains a **trait history** for post-series analysis.

Visual traits tracked per snapshot:
    skin_tone, eye_color, age_range, gender_expression,
    hair_style, hair_color, outfit_code, background_code

Usage::

    memory = LongHorizonContinuityMemory()

    # After each render, snapshot the traits:
    memory.record_snapshot(
        avatar_id="av-123",
        episode_number=5,
        traits={"skin_tone": "medium", "hair_color": "black", ...},
        embedding=render_embedding,
    )

    # Pre-render: check if proposed traits are consistent with history
    warning = memory.pre_render_continuity_check(
        avatar_id="av-123",
        proposed_traits={"hair_color": "blonde"},  # sudden change!
    )
    # warning["drift_risk"] == "high"
    # warning["conflicting_traits"] == ["hair_color"]
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

# Tracked trait fields
_VISUAL_TRAITS = (
    "skin_tone",
    "eye_color",
    "age_range",
    "gender_expression",
    "hair_style",
    "hair_color",
    "outfit_code",
    "background_code",
)

# Fraction of history agreeing on a trait value for it to be considered canonical
_CANONICAL_AGREEMENT_THRESHOLD = 0.7
# Cosine similarity below which a proposed embedding is flagged for pre-render review
_PRE_RENDER_SIM_THRESHOLD = 0.78
# Maximum number of snapshots retained per avatar in memory (circular buffer)
_MAX_SNAPSHOTS = 50

# In-memory store: {avatar_id → list[snapshot]}
_MEMORY_STORE: dict[str, list[dict[str, Any]]] = {}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return round(dot / (norm_a * norm_b), 6)


class LongHorizonContinuityMemory:
    """Long-horizon trait + embedding memory for avatar continuity governance.

    All state is held in ``_MEMORY_STORE`` (in-process, circular buffer per
    avatar).  A ``db`` session can be provided for future persistence.
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_snapshot(
        self,
        avatar_id: str,
        traits: dict[str, Any],
        episode_number: int | None = None,
        embedding: list[float] | None = None,
        render_url: str | None = None,
        quality_score: float | None = None,
    ) -> dict[str, Any]:
        """Record a trait + embedding snapshot for an avatar.

        Args:
            avatar_id: Avatar identifier.
            traits: Visual trait dict (see ``_VISUAL_TRAITS``).
            episode_number: Episode number for the snapshot (optional).
            embedding: Per-render mean embedding (optional).
            render_url: Optional render output URL.
            quality_score: Optional quality score ∈ [0, 1].

        Returns:
            Dict with ``recorded`` and ``snapshot_count``.
        """
        snapshot = {
            "episode_number": episode_number,
            "traits": {k: traits.get(k) for k in _VISUAL_TRAITS},
            "embedding": embedding,
            "render_url": render_url,
            "quality_score": quality_score,
            "recorded_at": time.time(),
        }
        _MEMORY_STORE.setdefault(avatar_id, [])
        snapshots = _MEMORY_STORE[avatar_id]
        snapshots.append(snapshot)

        # Circular buffer: keep only the most recent _MAX_SNAPSHOTS
        if len(snapshots) > _MAX_SNAPSHOTS:
            _MEMORY_STORE[avatar_id] = snapshots[-_MAX_SNAPSHOTS:]

        return {
            "recorded": True,
            "avatar_id": avatar_id,
            "snapshot_count": len(_MEMORY_STORE[avatar_id]),
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_canonical_traits(self, avatar_id: str) -> dict[str, Any]:
        """Derive canonical trait values from the snapshot history.

        For each trait, the value that appears in >= ``_CANONICAL_AGREEMENT_THRESHOLD``
        fraction of snapshots is returned as canonical.  Traits without a clear
        majority are returned as None.

        Returns:
            Dict mapping trait name → canonical value (or None).
        """
        snapshots = _MEMORY_STORE.get(avatar_id, [])
        if not snapshots:
            return {}

        canonical: dict[str, Any] = {}
        for trait in _VISUAL_TRAITS:
            values = [
                s["traits"].get(trait)
                for s in snapshots
                if s["traits"].get(trait) is not None
            ]
            if not values:
                canonical[trait] = None
                continue
            # Most common value
            from collections import Counter
            most_common_val, count = Counter(values).most_common(1)[0]
            if count / len(values) >= _CANONICAL_AGREEMENT_THRESHOLD:
                canonical[trait] = most_common_val
            else:
                canonical[trait] = None  # No clear canonical value

        return canonical

    def get_canonical_embedding(self, avatar_id: str) -> list[float] | None:
        """Return the mean embedding across all snapshots as the canonical.

        Returns None when no snapshots have embeddings.
        """
        snapshots = _MEMORY_STORE.get(avatar_id, [])
        embeddings = [s["embedding"] for s in snapshots if s.get("embedding")]
        if not embeddings:
            return None

        dim = len(embeddings[0])
        avg = [sum(e[i] for e in embeddings) / len(embeddings) for i in range(dim)]
        norm = math.sqrt(sum(x * x for x in avg)) or 1.0
        return [round(x / norm, 6) for x in avg]

    def pre_render_continuity_check(
        self,
        avatar_id: str,
        proposed_traits: dict[str, Any] | None = None,
        proposed_embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        """Check proposed traits/embedding against canonical history before render.

        Returns a risk assessment:
        - ``drift_risk``: "none" | "low" | "medium" | "high"
        - ``conflicting_traits``: list of trait names that deviate from canonical
        - ``embedding_similarity``: cosine similarity to canonical embedding (or None)
        - ``embedding_flagged``: True when similarity < _PRE_RENDER_SIM_THRESHOLD
        - ``recommendation``: actionable guidance
        """
        canonical_traits = self.get_canonical_traits(avatar_id)
        canonical_emb = self.get_canonical_embedding(avatar_id)

        # Trait conflict check
        conflicting: list[str] = []
        if proposed_traits and canonical_traits:
            for trait, canonical_val in canonical_traits.items():
                if canonical_val is None:
                    continue
                proposed_val = proposed_traits.get(trait)
                if proposed_val is not None and proposed_val != canonical_val:
                    conflicting.append(trait)

        # Embedding similarity check
        emb_similarity: float | None = None
        emb_flagged = False
        if proposed_embedding and canonical_emb:
            emb_similarity = _cosine_similarity(canonical_emb, proposed_embedding)
            emb_flagged = emb_similarity < _PRE_RENDER_SIM_THRESHOLD

        # Risk level
        conflict_count = len(conflicting)
        if conflict_count >= 3 or emb_flagged:
            drift_risk = "high"
        elif conflict_count >= 1 or (emb_similarity is not None and emb_similarity < 0.85):
            drift_risk = "medium"
        elif conflict_count == 0 and not emb_flagged:
            drift_risk = "none"
        else:
            drift_risk = "low"

        # Recommendation
        if drift_risk in ("high", "medium"):
            rec = (
                f"Proposed render deviates from canonical avatar in trait(s): {conflicting}. "
                "Align with canonical traits before rendering to avoid continuity break."
            )
        else:
            rec = "Proposed render is consistent with canonical avatar history."

        return {
            "avatar_id": avatar_id,
            "drift_risk": drift_risk,
            "conflicting_traits": conflicting,
            "embedding_similarity": round(emb_similarity, 4) if emb_similarity is not None else None,
            "embedding_flagged": emb_flagged,
            "canonical_traits": canonical_traits,
            "recommendation": rec,
        }

    def get_trait_drift_report(self, avatar_id: str) -> dict[str, Any]:
        """Return a longitudinal drift report showing how traits changed over time.

        Returns:
            Dict with ``avatar_id``, ``snapshot_count``,
            ``trait_stability`` (per-trait agreement ratio),
            ``unstable_traits`` (traits below threshold),
            and ``drift_trend`` ("stable" | "drifting").
        """
        snapshots = _MEMORY_STORE.get(avatar_id, [])
        if not snapshots:
            return {
                "avatar_id": avatar_id,
                "snapshot_count": 0,
                "trait_stability": {},
                "unstable_traits": [],
                "drift_trend": "stable",
            }

        from collections import Counter
        trait_stability: dict[str, float] = {}
        for trait in _VISUAL_TRAITS:
            values = [s["traits"].get(trait) for s in snapshots if s["traits"].get(trait) is not None]
            if not values:
                trait_stability[trait] = 1.0
                continue
            _, top_count = Counter(values).most_common(1)[0]
            trait_stability[trait] = round(top_count / len(values), 4)

        unstable = [t for t, s in trait_stability.items() if s < _CANONICAL_AGREEMENT_THRESHOLD]
        drift_trend = "drifting" if len(unstable) >= 2 else "stable"

        return {
            "avatar_id": avatar_id,
            "snapshot_count": len(snapshots),
            "trait_stability": trait_stability,
            "unstable_traits": unstable,
            "drift_trend": drift_trend,
        }

    def clear_avatar(self, avatar_id: str) -> None:
        """Remove all snapshots for an avatar."""
        _MEMORY_STORE.pop(avatar_id, None)
