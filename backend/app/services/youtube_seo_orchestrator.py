from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.autopilot_brain import AutopilotBrainCompileRequest
from app.services.autopilot_brain_runtime import AutopilotBrainRuntime


class YouTubeSEOOrchestrator:
    """Adds YouTube SEO + binge-chain metadata after render and before publish."""

    def __init__(self) -> None:
        self._brain = AutopilotBrainRuntime()

    def enrich_publish_payload(
        self,
        *,
        db: Session | None,
        payload: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
        platform_lower = (platform or "").lower()
        if platform_lower not in {"youtube", "shorts"}:
            return payload

        cloned = deepcopy(payload)
        metadata = dict(cloned.get("metadata") or {})
        brain_context = dict(metadata.get("autopilot_brain") or {})

        source_text = (
            cloned.get("script_text")
            or cloned.get("topic")
            or cloned.get("title_angle")
            or metadata.get("story_hook")
            or metadata.get("description")
            or "Untitled video"
        )
        if not brain_context:
            compiled = self._brain.compile(
                db=db,
                req=AutopilotBrainCompileRequest(
                    topic=source_text,
                    audience=metadata.get("audience"),
                    platform=platform_lower,
                    market_code=metadata.get("market_code"),
                    niche=metadata.get("niche"),
                    channel_name=metadata.get("channel_name"),
                    store_if_winner=False,
                ),
            )
            brain_context = compiled.runtime_memory_payload
            metadata["autopilot_brain"] = brain_context
            cloned["brain_compile"] = compiled.model_dump()
            seo = compiled.seo_bridge.model_dump()
        else:
            seo = dict(cloned.get("youtube_seo") or {})

        if not seo:
            compiled = self._brain.compile(
                db=db,
                req=AutopilotBrainCompileRequest(topic=source_text, platform=platform_lower),
            )
            seo = compiled.seo_bridge.model_dump()
            cloned["brain_compile"] = compiled.model_dump()

        # Preserve manual overrides if caller already supplied them.
        seo["title"] = str(cloned.get("title_angle") or seo.get("title") or "Untitled")
        if cloned.get("description"):
            seo["description"] = str(cloned["description"])
        if metadata.get("tags"):
            seo["tags"] = list(dict.fromkeys([*seo.get("tags", []), *metadata.get("tags", [])]))

        metadata["description"] = seo.get("description")
        metadata["tags"] = seo.get("tags") or []
        metadata["video_hashtags"] = seo.get("video_hashtags") or []
        metadata["channel_hashtags"] = seo.get("channel_hashtags") or []
        metadata["pinned_comment"] = seo.get("pinned_comment")
        metadata["thumbnail_brief"] = seo.get("thumbnail_brief")
        metadata["series_cta"] = self._extract_series_cta(seo.get("description") or "")

        cloned["youtube_seo"] = seo
        cloned["metadata"] = metadata
        return cloned

    @staticmethod
    def _extract_series_cta(description: str) -> str:
        marker = "Keep going with the next chapters in this chain:"
        if marker not in description:
            return "Continue to the next video in the series."
        return description.split(marker, 1)[1].strip().splitlines()[0:4] and "Continue this chain in order from the description links."
