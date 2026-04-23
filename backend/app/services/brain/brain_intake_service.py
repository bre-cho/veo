"""brain_intake_service — entrypoint orchestration for the Brain Layer."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.brain_intake import BrainIntakeRequest
from app.services.avatar.avatar_identity_engine import AvatarIdentityEngine
from app.services.brain.brain_decision_engine import BrainDecisionEngine
from app.services.brain.brain_manifest_builder import BrainManifestBuilder
from app.services.brain.brain_memory_service import BrainMemoryService
from app.services.brain.series_continuity_router import SeriesContinuityRouter


class BrainIntakeService:
    def __init__(self) -> None:
        self._memory = BrainMemoryService()
        self._decision = BrainDecisionEngine()
        self._builder = BrainManifestBuilder()
        self._continuity = SeriesContinuityRouter()
        self._avatar_identity = AvatarIdentityEngine()

    def _orchestrate(self, db: Session | None, request: BrainIntakeRequest) -> dict[str, Any]:
        request_dict = request.model_dump()

        raw = f"{request_dict.get('topic') or ''} {request_dict.get('script_text') or ''}".lower()
        topic_class = "system"
        if any(k in raw for k in ["ai", "algorithm", "automation", "machine"]):
            topic_class = "ai"
        elif any(k in raw for k in ["story", "journey", "biography", "mystery"]):
            topic_class = "documentary"

        avatar_selection = self._avatar_identity.select_avatar(
            market_code=request.market_code,
            content_goal=request.content_goal,
            topic_class=topic_class,
            preferred_avatar_id=request.avatar_id,
        )
        request_dict["avatar_id"] = avatar_selection.avatar_id
        request_dict["topic_class"] = topic_class
        request_dict["avatar_identity"] = avatar_selection.identity
        request_dict["avatar_voice"] = avatar_selection.voice

        memory_bundle = self._memory.recall(
            db,
            market_code=request.market_code,
            content_goal=request.content_goal,
            series_id=request.series_id,
            avatar_id=avatar_selection.avatar_id,
            topic_class=topic_class,
        )
        continuity = self._continuity.resolve(
            series_id=request.series_id,
            episode_index=request.episode_index,
            latest_episode_memory=memory_bundle.get("latest_episode_memory"),
            source_type=request.source_type,
        )
        brain_plan, continuity_context = self._decision.build_plan(
            request=request_dict,
            memory_bundle=memory_bundle,
            continuity=continuity,
        )
        return self._builder.build_preview_payload(
            request=request_dict,
            memory_bundle=memory_bundle,
            brain_plan=brain_plan.model_dump(),
            continuity_context=continuity_context.model_dump(),
        )

    def orchestrate_script_preview(
        self,
        db: Session | None,
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
        request = BrainIntakeRequest(
            source_type="script_upload",
            filename=filename,
            script_text=script_text,
            aspect_ratio=aspect_ratio,
            target_platform=target_platform,
            style_preset=style_preset,
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            series_id=series_id,
            episode_index=episode_index,
        )
        return self._orchestrate(db, request)

    def orchestrate_topic_preview(
        self,
        db: Session | None,
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
        request = BrainIntakeRequest(
            source_type="topic",
            topic=topic,
            aspect_ratio=aspect_ratio,
            target_platform=target_platform,
            style_preset=style_preset,
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            series_id=series_id,
            episode_index=episode_index,
        )
        return self._orchestrate(db, request)
