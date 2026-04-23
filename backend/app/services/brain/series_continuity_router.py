"""series_continuity_router — resolve series/episode assignment and open-loop plan.

Given a (series_id, episode_index) hint and the latest EpisodeMemory for that
series, this service determines:

- The canonical series_id and episode_index to use.
- The episode role (opener / escalation / reveal / bridge / payoff).
- Unresolved open loops that should be injected into this episode.
- Callback targets from previous episodes.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_EPISODE_ROLES = ["opener", "escalation", "reveal", "bridge", "payoff"]


class SeriesContinuityRouter:
    """Determine episode continuity context from memory and hints."""

    def resolve(
        self,
        *,
        series_id: str | None,
        episode_index: int | None,
        latest_episode_memory: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Return continuity resolution dict.

        Returns
        -------
        dict with keys:
            series_id, episode_index, episode_role,
            unresolved_loops, resolved_loops, callback_targets,
            continuity_constraints
        """
        resolved_series_id = series_id or (latest_episode_memory or {}).get("series_id")
        resolved_index = self._resolve_episode_index(episode_index, latest_episode_memory)
        episode_role = self._infer_episode_role(resolved_index, latest_episode_memory)
        unresolved_loops = self._collect_unresolved_loops(latest_episode_memory)
        callback_targets = self._collect_callbacks(latest_episode_memory)
        continuity_constraints = self._build_constraints(latest_episode_memory)

        return {
            "series_id": resolved_series_id,
            "episode_index": resolved_index,
            "episode_role": episode_role,
            "unresolved_loops": unresolved_loops,
            "resolved_loops": list((latest_episode_memory or {}).get("resolved_loops") or []),
            "callback_targets": callback_targets,
            "continuity_constraints": continuity_constraints,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_episode_index(
        hint: int | None,
        memory: dict[str, Any] | None,
    ) -> int:
        if hint is not None:
            return hint
        if memory:
            prev_index = memory.get("episode_index")
            if prev_index is not None:
                try:
                    return int(prev_index) + 1
                except (TypeError, ValueError):
                    pass
        return 0

    @staticmethod
    def _infer_episode_role(episode_index: int, memory: dict[str, Any] | None) -> str:
        if episode_index == 0:
            return "opener"
        arc = (memory or {}).get("series_arc") or {}
        if isinstance(arc, dict):
            arc_pos = str(arc.get("arc_position", "")).lower()
            if arc_pos in ("climax", "reveal"):
                return "reveal"
            if arc_pos in ("rising", "escalation"):
                return "escalation"
            if arc_pos in ("falling", "bridge"):
                return "bridge"
            if arc_pos in ("resolution", "payoff"):
                return "payoff"
        # Cycle through roles in round-robin order for series without arc info
        return _EPISODE_ROLES[episode_index % len(_EPISODE_ROLES)]

    @staticmethod
    def _collect_unresolved_loops(memory: dict[str, Any] | None) -> list[str]:
        if not memory:
            return []
        loops = memory.get("open_loops") or []
        if isinstance(loops, list):
            return [str(l) for l in loops]
        return []

    @staticmethod
    def _collect_callbacks(memory: dict[str, Any] | None) -> list[str]:
        if not memory:
            return []
        callbacks = memory.get("character_callbacks") or []
        if isinstance(callbacks, list):
            return [str(c) for c in callbacks]
        return []

    @staticmethod
    def _build_constraints(memory: dict[str, Any] | None) -> dict[str, Any]:
        if not memory:
            return {"preserve_avatar_identity": True}
        state = memory.get("character_state") or {}
        constraints: dict[str, Any] = {"preserve_avatar_identity": True}
        if isinstance(state, dict) and state.get("tone"):
            constraints["maintain_tone"] = state["tone"]
        return constraints
