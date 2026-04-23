"""avatar_pair_learning_engine — learns which avatar fits which context best.

Phase 1: statistical / rule-based learning using pattern memory.
No ML required at this stage.

The engine tracks:
  • avatar × template_family  fit
  • avatar × topic_class      fit
  • avatar × platform         fit

Each combination is stored as a ``PatternMemory`` record with
``pattern_type="avatar_pair_fit"`` and queried back to produce
pair fit scores during tournament scoring.
"""
from __future__ import annotations

from typing import Any


class AvatarPairLearningEngine:
    """Statistical pair-fit tracker for avatar × template × topic × platform."""

    # ── Context key builders ──────────────────────────────────────────────────

    def pair_context_key(
        self,
        *,
        avatar_id: str,
        template_family: str | None,
        topic_class: str | None,
        platform: str | None,
    ) -> str:
        """Build a stable lookup key for the avatar × context combination."""
        return "::".join(
            [
                avatar_id or "none",
                template_family or "none",
                topic_class or "none",
                platform or "none",
            ]
        )

    # ── Score computation ─────────────────────────────────────────────────────

    def compute_pair_fit_score(
        self,
        *,
        avg_score: float,
        sample_count: int,
        recency_factor: float = 1.0,
    ) -> float:
        """Compute a confidence-weighted pair fit score.

        Low sample counts are penalised to avoid over-confidence on sparse data.
        """
        confidence = min(sample_count / 5.0, 1.0)  # saturates at 5 samples
        return round(avg_score * confidence * recency_factor, 4)

    # ── Pattern record builders ───────────────────────────────────────────────

    def build_pattern_payload(
        self,
        *,
        avatar_id: str,
        template_family: str | None,
        topic_class: str | None,
        platform: str | None,
        metrics: dict[str, Any],
        pair_score: float,
    ) -> dict[str, Any]:
        return {
            "avatar_id": avatar_id,
            "template_family": template_family,
            "topic_class": topic_class,
            "platform": platform,
            "pair_score": pair_score,
            "metrics": metrics,
        }

    # ── Lookup helpers (pure, no DB) ──────────────────────────────────────────

    def extract_pair_score_from_pattern(
        self, pattern_payload: dict[str, Any]
    ) -> float:
        """Return the pair_score stored inside a raw PatternMemory payload."""
        return float((pattern_payload or {}).get("pair_score", 0.0))

    def rank_avatar_contexts(
        self,
        avatar_scores: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort avatar × context records by pair_score descending."""
        return sorted(
            avatar_scores,
            key=lambda x: x.get("pair_score", 0.0),
            reverse=True,
        )
