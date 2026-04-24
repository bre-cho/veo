from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID


class DialogueDramaService:
    """Build line-level dialogue subtext rows from scene analysis output."""

    def build_rows(
        self,
        *,
        scene_id: UUID,
        project_id: UUID | None,
        episode_id: UUID | None,
        subtext_map: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for idx, item in enumerate(subtext_map):
            rows.append(
                {
                    "project_id": project_id,
                    "episode_id": episode_id,
                    "scene_id": scene_id,
                    "line_index": idx,
                    "speaker_id": item.get("speaker_id"),
                    "target_id": item.get("target_id"),
                    "literal_intent": item.get("literal_intent") or item.get("psychological_action"),
                    "hidden_intent": item.get("hidden_intent"),
                    "psychological_action": item.get("psychological_action"),
                    "suggested_subtext": item.get("suggested_subtext"),
                    "threat_level": float(item.get("threat_level", 0.0) or 0.0),
                    "honesty_level": float(item.get("honesty_level", 0.5) or 0.5),
                    "mask_level": float(item.get("mask_level", 0.5) or 0.5),
                }
            )
        return rows
