from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NextLevelScriptRequest(BaseModel):
    project_id: str
    episode_id: str
    topic: str
    target_audience: Optional[str] = None
    tone: Optional[str] = None
    duration_sec: Optional[int] = 60
    num_scenes: Optional[int] = 5
    extra_context: Optional[Dict[str, Any]] = None
