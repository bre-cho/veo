"""series_continuity_router — resolve series/episode assignment and open-loop plan."""
from __future__ import annotations

from typing import Any


class SeriesContinuityRouter:
    def resolve(
        self,
        *,
        series_id: str | None,
        episode_index: int | None,
        latest_episode_memory: dict[str, Any] | None,
        source_type: str,
    ) -> dict[str, Any]:
        latest_episode_memory = latest_episode_memory or {}

        resolved_series_id = (
            series_id
            or latest_episode_memory.get("series_id")
            or "default_series"
        )

        resolved_episode_index = (
            episode_index
            or latest_episode_memory.get("episode_index")
            or 1
        )

        if resolved_episode_index <= 1:
            episode_role = "opener"
        elif resolved_episode_index == 2:
            episode_role = "escalation"
        else:
            episode_role = "continuation"

        return {
            "series_id": resolved_series_id,
            "episode_index": resolved_episode_index,
            "episode_role": episode_role,
            "unresolved_loops": latest_episode_memory.get("open_loops") or [],
            "resolved_loops": latest_episode_memory.get("resolved_loops") or [],
            "callback_targets": latest_episode_memory.get("character_callbacks") or [],
        }
