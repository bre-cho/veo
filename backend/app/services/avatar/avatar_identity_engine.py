"""avatar_identity_engine — selects the best avatar for a given context.

Selection scoring
-----------------
topic_class match  → +2.0
content_goal match → +2.0
market_code match  → +1.0

The avatar with the highest composite score is chosen.  If two avatars tie,
the first match in registry iteration order wins.

Preferred override
------------------
If ``preferred_avatar_id`` is supplied and exists in the registry, it is
returned immediately with score=999 (override bypass).
"""
from __future__ import annotations

from typing import Any

from app.schemas.avatar_system import AvatarSelectionResult
from app.services.avatar.avatar_registry import AVATAR_REGISTRY


class AvatarIdentityEngine:
    """Selects an avatar persona that best fits the current production context."""

    # ------------------------------------------------------------------
    # Internal scoring helpers
    # ------------------------------------------------------------------

    def _topic_fit_score(
        self, *, avatar: dict[str, Any], topic_class: str | None
    ) -> float:
        if topic_class and topic_class in (avatar.get("topic_classes") or []):
            return 2.0
        return 0.0

    def _goal_fit_score(
        self, *, avatar: dict[str, Any], content_goal: str | None
    ) -> float:
        if content_goal and content_goal in (avatar.get("content_goals") or []):
            return 2.0
        return 0.0

    def _market_fit_score(
        self, *, avatar: dict[str, Any], market_code: str | None
    ) -> float:
        if market_code and avatar.get("market_code") == market_code:
            return 1.0
        return 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_avatar(
        self,
        *,
        market_code: str | None,
        content_goal: str | None,
        topic_class: str | None,
        preferred_avatar_id: str | None = None,
    ) -> AvatarSelectionResult:
        """Return the best-matching avatar for the given production context.

        Parameters
        ----------
        market_code:
            ISO market identifier (e.g. ``"US"``, ``"VN"``).
        content_goal:
            Target outcome (e.g. ``"retention"``, ``"conversion"``).
        topic_class:
            Content topic category (e.g. ``"ai"``, ``"business"``).
        preferred_avatar_id:
            When set and present in the registry, bypass scoring and return
            this avatar directly.
        """
        # --- preferred override ---
        if preferred_avatar_id and preferred_avatar_id in AVATAR_REGISTRY:
            chosen = AVATAR_REGISTRY[preferred_avatar_id]
            return AvatarSelectionResult(
                avatar_id=chosen["avatar_id"],
                score=999.0,
                reasons=["preferred_avatar_override"],
                identity=chosen,
                voice=chosen.get("voice_profile") or {},
            )

        # --- scored selection ---
        best_avatar: dict[str, Any] | None = None
        best_score = float("-inf")
        best_reasons: list[str] = []

        for avatar in AVATAR_REGISTRY.values():
            reasons: list[str] = []
            score = 0.0

            x = self._topic_fit_score(avatar=avatar, topic_class=topic_class)
            if x:
                score += x
                reasons.append("topic_class_match")

            x = self._goal_fit_score(avatar=avatar, content_goal=content_goal)
            if x:
                score += x
                reasons.append("content_goal_match")

            x = self._market_fit_score(avatar=avatar, market_code=market_code)
            if x:
                score += x
                reasons.append("market_match")

            if score > best_score:
                best_score = score
                best_avatar = avatar
                best_reasons = reasons

        chosen = best_avatar or next(iter(AVATAR_REGISTRY.values()))
        return AvatarSelectionResult(
            avatar_id=chosen["avatar_id"],
            score=best_score if best_score != float("-inf") else 0.0,
            reasons=best_reasons,
            identity=chosen,
            voice=chosen.get("voice_profile") or {},
        )
