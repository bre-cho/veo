"""factory_router – skill routing logic for the SKILL_ROUTE stage.

Determines which workflow (skill) should handle the request based on the
input type, series/avatar presence, and any recent winner-memory signals.
"""
from __future__ import annotations

from app.factory.factory_context import FactoryContext


SKILL_TOPIC_VIDEO = "topic_video"
SKILL_SCRIPT_VIDEO = "script_video"
SKILL_AVATAR_VIDEO = "avatar_video"
SKILL_SERIES_VIDEO = "series_video"


def route_skill(ctx: FactoryContext) -> str:
    """Return the skill identifier that best matches the factory context."""
    if ctx.input_series_id:
        return SKILL_SERIES_VIDEO
    if ctx.input_avatar_id:
        return SKILL_AVATAR_VIDEO
    if ctx.input_script:
        return SKILL_SCRIPT_VIDEO
    return SKILL_TOPIC_VIDEO
