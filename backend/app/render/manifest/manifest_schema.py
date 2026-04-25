from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SceneAssetManifest(BaseModel):
    """Full asset + metadata record for a single rendered scene."""

    project_id: str
    episode_id: str
    scene_id: str

    status: str = "created"

    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    final_output_path: Optional[str] = None

    duration_sec: Optional[float] = None
    timeline: Optional[Dict[str, Any]] = None

    voiceover_text: Optional[str] = None
    word_timings: List[Dict[str, Any]] = Field(default_factory=list)

    detection: Dict[str, Any] = Field(default_factory=dict)
    subtitle_placement: Dict[str, Any] = Field(default_factory=dict)

    voice_directive: Dict[str, Any] = Field(default_factory=dict)
    render_purpose: Optional[str] = None
    drama_metadata: Dict[str, Any] = Field(default_factory=dict)

    provider_payload: Dict[str, Any] = Field(default_factory=dict)
    tts_payload: Dict[str, Any] = Field(default_factory=dict)

    needs_reassembly: bool = False

    error: Optional[Dict[str, Any]] = None

    updated_at: Optional[str] = None
