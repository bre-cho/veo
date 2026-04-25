from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel


class AssemblyRequest(BaseModel):
    project_id: str
    episode_id: str
    assembly_plan: Dict[str, Any]
