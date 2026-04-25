from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class VoiceDirective(BaseModel):
    tone: str
    speed: str
    pause: str
    stress_words: List[str] = []


class DramaMetadata(BaseModel):
    subtext: Optional[str] = None
    intent: Optional[str] = None
    emotion: Optional[str] = None


class RenderScenePayload(BaseModel):
    scene_index: int
    scene_id: str
    render_purpose: str
    voiceover_text: str
    duration_sec: int
    voice_directive: VoiceDirective
    drama_metadata: DramaMetadata
