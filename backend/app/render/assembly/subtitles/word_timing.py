from __future__ import annotations

from typing import List

from pydantic import BaseModel


class WordTiming(BaseModel):
    """Timing for a single spoken word."""

    word: str
    start_sec: float
    end_sec: float


class SubtitleWordTrack(BaseModel):
    """Word-level timing track for a single scene."""

    scene_id: str
    words: List[WordTiming]
