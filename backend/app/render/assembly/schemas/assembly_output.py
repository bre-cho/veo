from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AssemblyOutput(BaseModel):
    project_id: str
    episode_id: str
    status: str
    output_path: str
    subtitle_path: str
    command: Optional[List[str]] = None
