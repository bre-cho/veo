from __future__ import annotations

from typing import Any, Dict

from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor
from app.render.assembly.schemas.assembly_request import AssemblyRequest


class AssemblyService:
    """Service layer that delegates assembly execution to FFmpegAssemblyExecutor."""

    def __init__(self) -> None:
        self.executor = FFmpegAssemblyExecutor()

    def assemble(self, payload: AssemblyRequest) -> Dict[str, Any]:
        """Execute assembly for the given request payload.

        Args:
            payload: An :class:`AssemblyRequest` with ``project_id``,
                ``episode_id``, and ``assembly_plan``.

        Returns:
            The result dict from
            :meth:`FFmpegAssemblyExecutor.execute`.
        """
        return self.executor.execute(
            project_id=payload.project_id,
            episode_id=payload.episode_id,
            assembly_plan=payload.assembly_plan,
        )
