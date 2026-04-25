from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class TimelineRequest(BaseModel):
    project_id: str
    episode_id: str
    render_scenes: List[Dict[str, Any]]
