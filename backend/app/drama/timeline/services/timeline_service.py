from __future__ import annotations

from typing import Any, Dict

from app.drama.timeline.engines.timeline_compiler import SceneTimelineCompiler
from app.drama.timeline.schemas.timeline_request import TimelineRequest


class TimelineService:
    """Service that delegates timeline compilation to SceneTimelineCompiler."""

    def __init__(self) -> None:
        self.compiler = SceneTimelineCompiler()

    def compile(self, payload: TimelineRequest) -> Dict[str, Any]:
        return self.compiler.compile(
            project_id=payload.project_id,
            episode_id=payload.episode_id,
            render_scenes=payload.render_scenes,
        )
