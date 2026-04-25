from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class TimelineOutput(BaseModel):
    project_id: str
    episode_id: str
    total_duration_sec: int
    scenes: List[Dict[str, Any]]
    subtitle_tracks: List[Dict[str, Any]]
    audio_tracks: List[Dict[str, Any]]
    transition_map: List[Dict[str, Any]]
    assembly_plan: Dict[str, Any]
