"""brain_intake_service — entrypoint orchestration for the Brain Layer.

Public API:
    orchestrate_topic_preview(...)   → enriched preview payload dict
    orchestrate_script_preview(...)  → enriched preview payload dict
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.brain.brain_memory_service import BrainMemoryService
from app.services.brain.brain_decision_engine import BrainDecisionEngine
from app.services.brain.brain_manifest_builder import BrainManifestBuilder

logger = logging.getLogger(__name__)

_memory_service = BrainMemoryService()
_decision_engine = BrainDecisionEngine()
_manifest_builder = BrainManifestBuilder()


class BrainIntakeService:
    """Orchestrate the full Brain Layer pipeline to produce an enriched preview."""

    # ------------------------------------------------------------------
    # Topic intake
    # ------------------------------------------------------------------
    def orchestrate_topic_preview(
        self,
        db,
        *,
        topic: str,
        aspect_ratio: str = "9:16",
        target_platform: str = "shorts",
        style_preset: str | None = None,
        avatar_id: str | None = None,
        market_code: str | None = None,
        content_goal: str | None = None,
        conversion_mode: str | None = None,
        series_id: str | None = None,
        episode_index: int | None = None,
    ) -> dict[str, Any]:
        """Convert a topic → enriched preview payload with brain context."""
        memory_bundle = _memory_service.recall(
            db,
            market_code=market_code,
            content_goal=content_goal,
            series_id=series_id,
            avatar_id=avatar_id,
        )
        brain_plan = _decision_engine.plan(
            source_type="topic",
            topic=topic,
            script_text=None,
            series_id=series_id,
            episode_index=episode_index,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            memory_bundle=memory_bundle,
        )
        return _manifest_builder.build(
            source_type="topic",
            topic=topic,
            script_text=None,
            filename=None,
            aspect_ratio=aspect_ratio,
            target_platform=target_platform,
            style_preset=style_preset,
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            memory_bundle=memory_bundle,
            brain_plan=brain_plan,
        )

    # ------------------------------------------------------------------
    # Script upload
    # ------------------------------------------------------------------
    def orchestrate_script_preview(
        self,
        db,
        *,
        filename: str | None,
        script_text: str,
        aspect_ratio: str = "9:16",
        target_platform: str = "shorts",
        style_preset: str | None = None,
        avatar_id: str | None = None,
        market_code: str | None = None,
        content_goal: str | None = None,
        conversion_mode: str | None = None,
        series_id: str | None = None,
        episode_index: int | None = None,
    ) -> dict[str, Any]:
        """Parse script + run Brain Layer → enriched preview payload."""
        memory_bundle = _memory_service.recall(
            db,
            market_code=market_code,
            content_goal=content_goal,
            series_id=series_id,
            avatar_id=avatar_id,
        )
        brain_plan = _decision_engine.plan(
            source_type="script_upload",
            topic=None,
            script_text=script_text,
            series_id=series_id,
            episode_index=episode_index,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            memory_bundle=memory_bundle,
        )
        return _manifest_builder.build(
            source_type="script_upload",
            topic=None,
            script_text=script_text,
            filename=filename,
            aspect_ratio=aspect_ratio,
            target_platform=target_platform,
            style_preset=style_preset,
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            memory_bundle=memory_bundle,
            brain_plan=brain_plan,
        )
