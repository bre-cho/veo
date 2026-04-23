"""avatar_continuity_engine — builds per-episode avatar continuity snapshots.

Continuity state is injected into scene metadata so that the render layer
(prompt builder, storyboard engine) can enforce persona consistency across
episodes in a series.

Emotion curve defaults by episode role
---------------------------------------
opener      → curiosity_entry
reveal      → controlled_reveal
escalation  → rising_tension
resolution  → calm_closure
cliffhanger → urgent_suspend
(default)   → rising_tension
"""
from __future__ import annotations

from app.schemas.avatar_system import AvatarContinuityState

_EMOTION_CURVE_MAP: dict[str, str] = {
    "opener": "curiosity_entry",
    "reveal": "controlled_reveal",
    "escalation": "rising_tension",
    "resolution": "calm_closure",
    "cliffhanger": "urgent_suspend",
}


class AvatarContinuityEngine:
    """Builds an AvatarContinuityState for the current episode."""

    def build_state(
        self,
        *,
        avatar_id: str,
        series_id: str | None,
        episode_index: int | None,
        episode_role: str | None,
        callback_targets: list[str] | None = None,
        extra_constraints: dict | None = None,
    ) -> AvatarContinuityState:
        """Construct the continuity snapshot for this episode.

        Parameters
        ----------
        avatar_id:
            ID of the selected avatar.
        series_id:
            Series identifier (None for one-shot videos).
        episode_index:
            0-based position within the series.
        episode_role:
            Role label (opener / reveal / escalation / …).
        callback_targets:
            List of prior narrative hooks that this episode should reference.
        extra_constraints:
            Additional continuity constraints to merge in.
        """
        emotion_curve = _EMOTION_CURVE_MAP.get(episode_role or "", "rising_tension")

        constraints: dict = {
            "preserve_persona": True,
            "preserve_tone": True,
            "preserve_brand_identity": True,
        }
        if extra_constraints:
            constraints.update(extra_constraints)

        return AvatarContinuityState(
            avatar_id=avatar_id,
            series_id=series_id,
            episode_index=episode_index,
            narrative_arc_state=episode_role,
            emotion_curve=emotion_curve,
            callback_targets=callback_targets or [],
            continuity_constraints=constraints,
        )
