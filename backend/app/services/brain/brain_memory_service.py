"""brain_memory_service — recall winner patterns, episode memory, and continuity."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.episode_memory import EpisodeMemory
from app.services.avatar.avatar_memory_service import AvatarMemoryService
from app.services.pattern_library import PatternLibrary


class BrainMemoryService:
    def __init__(self) -> None:
        self._pattern_library = PatternLibrary()
        self._avatar_memory = AvatarMemoryService()

    def recall(
        self,
        db: Session | None,
        *,
        market_code: str | None,
        content_goal: str | None,
        series_id: str | None,
        avatar_id: str | None = None,
        topic_class: str | None = None,
    ) -> dict[str, Any]:
        winner_patterns: list[dict[str, Any]] = []
        latest_episode_memory: dict[str, Any] | None = None

        if db is not None:
            rows = self._pattern_library.list_top_patterns(
                db,
                market_code=market_code,
                content_goal=content_goal,
                limit=5,
                pattern_types=["winner_dna", "hook_pattern", "scene_sequence_pattern"],
            )
            winner_patterns = [
                {
                    "id": row.id,
                    "pattern_type": row.pattern_type,
                    "market_code": row.market_code,
                    "content_goal": row.content_goal,
                    "score": row.score,
                    "payload": row.payload or {},
                }
                for row in rows
            ]

            if series_id:
                latest = (
                    db.query(EpisodeMemory)
                    .filter(EpisodeMemory.series_id == series_id)
                    .order_by(EpisodeMemory.episode_index.desc(), EpisodeMemory.created_at.desc())
                    .first()
                )
                if latest is not None:
                    latest_episode_memory = {
                        "series_id": latest.series_id,
                        "episode_index": latest.episode_index,
                        "open_loops": latest.open_loops or [],
                        "resolved_loops": latest.resolved_loops or [],
                        "winning_scene_sequence": latest.winning_scene_sequence or [],
                        "series_arc": latest.series_arc or {},
                        "character_callbacks": latest.character_callbacks or [],
                    }

        top = winner_patterns[0] if winner_patterns else None
        winner_dna_summary = {
            "pattern_id": (top or {}).get("id"),
            "pattern_type": (top or {}).get("pattern_type"),
            "score": (top or {}).get("score"),
            "payload": (top or {}).get("payload") or {},
            "hook_core": ((top or {}).get("payload") or {}).get("hook_core"),
            "title_pattern": ((top or {}).get("payload") or {}).get("title_pattern"),
            "thumbnail_logic": ((top or {}).get("payload") or {}).get("thumbnail_logic"),
        }

        return {
            "winner_patterns": winner_patterns,
            "winner_dna_summary": winner_dna_summary,
            "latest_episode_memory": latest_episode_memory,
            "memory_refs": {
                "series_id": series_id,
                "winner_pattern_ids": [item["id"] for item in winner_patterns if item.get("id")],
            },
            "avatar_memory": self._avatar_memory.get_recent_avatar_score(
                db,
                avatar_id=avatar_id or "",
                market_code=market_code,
                content_goal=content_goal,
                topic_class=topic_class,
            ) if avatar_id else {},
        }
