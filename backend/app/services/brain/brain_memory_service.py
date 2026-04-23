"""brain_memory_service — recall winner patterns, episode memory, and continuity.

Reads from:
- PatternLibrary (PatternMemory DB)
- EpisodeMemory (DB)
- Avatar continuity state (best-effort)

Returns a memory bundle consumed by BrainDecisionEngine.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_WINNER_PATTERN_TYPES = (
    "winner_dna",
    "scene_sequence_pattern",
    "hook_pattern",
    "title_pattern",
    "pacing_pattern",
    "cta_pattern",
)
_TOP_WINNER_LIMIT = 5


class BrainMemoryService:
    """Recall memory bundle for Brain Layer planning."""

    def recall(
        self,
        db,
        *,
        market_code: str | None = None,
        content_goal: str | None = None,
        series_id: str | None = None,
        avatar_id: str | None = None,
    ) -> dict[str, Any]:
        """Return memory bundle.

        Returns
        -------
        dict with keys:
            winner_patterns, winner_dna_summary,
            latest_episode_memory, continuity_context, memory_refs
        """
        winner_patterns = self._load_winner_patterns(db, market_code=market_code, content_goal=content_goal)
        winner_dna_summary = self._build_winner_dna_summary(winner_patterns)
        latest_episode_memory = self._load_latest_episode_memory(db, series_id=series_id)
        continuity_context = self._build_continuity_context(latest_episode_memory, series_id=series_id)

        return {
            "winner_patterns": winner_patterns,
            "winner_dna_summary": winner_dna_summary,
            "latest_episode_memory": latest_episode_memory,
            "continuity_context": continuity_context,
            "memory_refs": {
                "market_code": market_code,
                "content_goal": content_goal,
                "series_id": series_id,
                "avatar_id": avatar_id,
                "winner_count": len(winner_patterns),
            },
        }

    # ------------------------------------------------------------------

    def _load_winner_patterns(
        self,
        db,
        *,
        market_code: str | None,
        content_goal: str | None,
    ) -> list[dict[str, Any]]:
        if db is None:
            return []
        try:
            from app.services.pattern_library import PatternLibrary
            lib = PatternLibrary()
            rows = lib.list_winners(
                db,
                market_code=market_code,
                content_goal=content_goal,
                limit=_TOP_WINNER_LIMIT,
            )
            return [
                {
                    "id": r.id,
                    "pattern_type": r.pattern_type,
                    "score": float(r.score) if r.score is not None else None,
                    "payload": r.payload or {},
                    "market_code": r.market_code,
                    "content_goal": r.content_goal,
                }
                for r in rows
            ]
        except Exception as exc:
            logger.debug("BrainMemoryService: winner pattern load failed: %s", exc)
            return []

    def _build_winner_dna_summary(self, patterns: list[dict[str, Any]]) -> dict[str, Any]:
        if not patterns:
            return {}
        top = patterns[0]
        payload = top.get("payload") or {}
        return {
            "top_pattern_id": top.get("id"),
            "hook_pattern": payload.get("hook_pattern"),
            "title_pattern": payload.get("title_pattern"),
            "pacing_pattern": payload.get("pacing_pattern"),
            "cta_pattern": payload.get("cta_pattern"),
            "scene_sequence_pattern": payload.get("scene_sequence_pattern"),
            "confidence": top.get("score") or 0.0,
        }

    def _load_latest_episode_memory(
        self,
        db,
        *,
        series_id: str | None,
    ) -> dict[str, Any] | None:
        if db is None or not series_id:
            return None
        try:
            from app.models.episode_memory import EpisodeMemory

            row = (
                db.query(EpisodeMemory)
                .filter(EpisodeMemory.series_id == series_id)
                .order_by(EpisodeMemory.episode_index.desc(), EpisodeMemory.created_at.desc())
                .first()
            )
            if row is None:
                return None
            return {
                "id": row.id,
                "series_id": row.series_id,
                "episode_index": row.episode_index,
                "character_state": row.character_state,
                "open_loops": row.open_loops or [],
                "resolved_loops": row.resolved_loops or [],
                "storyboard_id": row.storyboard_id,
                "winning_scene_sequence": row.winning_scene_sequence,
                "series_arc": row.series_arc,
                "character_callbacks": row.character_callbacks or [],
            }
        except Exception as exc:
            logger.debug("BrainMemoryService: episode memory load failed: %s", exc)
            return None

    @staticmethod
    def _build_continuity_context(
        episode_memory: dict[str, Any] | None,
        *,
        series_id: str | None,
    ) -> dict[str, Any]:
        if not episode_memory:
            return {
                "series_id": series_id,
                "episode_index": None,
                "unresolved_loops": [],
                "resolved_loops": [],
                "callback_targets": [],
                "continuity_constraints": {"preserve_avatar_identity": True},
            }
        return {
            "series_id": episode_memory.get("series_id") or series_id,
            "episode_index": episode_memory.get("episode_index"),
            "unresolved_loops": episode_memory.get("open_loops") or [],
            "resolved_loops": episode_memory.get("resolved_loops") or [],
            "callback_targets": episode_memory.get("character_callbacks") or [],
            "continuity_constraints": {"preserve_avatar_identity": True},
        }
