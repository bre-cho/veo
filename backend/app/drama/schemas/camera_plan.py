from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CameraPlanRead(BaseModel):
    scene_id: Optional[str] = None
    primary_move: str
    primary_shot: str
    dominant_character_id: Optional[str] = None
    emotional_center_character_id: Optional[str] = None
    focus_order: List[str] = Field(default_factory=list)
    lens_psychology_mode: str
    reveal_timing: str
    movement_strategy: Dict[str, str] = Field(default_factory=dict)
    eye_line_strategy: str
    render_bridge_tokens: Dict[str, str] = Field(default_factory=dict)
    camera_notes: List[str] = Field(default_factory=list)
