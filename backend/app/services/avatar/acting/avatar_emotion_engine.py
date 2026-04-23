"""avatar_emotion_engine — evolves an avatar's emotional state through scene beats.

The engine applies incremental updates to tension, control, and openness levels
based on beat type, conflict intensity, and dramatic intent.  All mutations are
non-destructive: a new dict is returned so callers can diff or store snapshots.
"""
from __future__ import annotations

from typing import Any


# Emotion transitions triggered by specific beat types
_BEAT_EMOTION_MAP: dict[str, tuple[str, str | None]] = {
    "betrayal_reveal": ("hurt", "anger"),
    "accusation": ("defensive", "anger"),
    "confession": ("vulnerable", "relief"),
    "victory": ("confident", "joy"),
    "defeat": ("shame", "sadness"),
    "threat": ("threatened", "fear"),
    "manipulation": ("guarded", "suspicion"),
    "reconciliation": ("hopeful", "calm"),
    "interrogation": ("guarded", "fear"),
    "revelation": ("shocked", "curiosity"),
}


class AvatarEmotionEngine:
    """Evolves avatar emotional state through scene beat events."""

    def evolve(
        self,
        current_state: dict[str, Any],
        beat: dict[str, Any],
    ) -> dict[str, Any]:
        """Return an updated emotional state dict based on *beat* events.

        Parameters
        ----------
        current_state:
            Current emotional state dict with keys matching
            ``AvatarEmotionalStateSchema``.
        beat:
            Story beat dict.  Relevant keys: ``beat_type`` / ``type``,
            ``conflict_intensity`` (float 0–1), ``dramatic_intent`` (str).

        Returns
        -------
        dict
            Updated (copied) emotional state.
        """
        state = dict(current_state)
        beat_type: str = beat.get("beat_type") or beat.get("type") or ""
        conflict_intensity: float = float(beat.get("conflict_intensity") or 0.0)

        # Tension escalation driven by conflict intensity
        if conflict_intensity > 0.8:
            state["tension_level"] = min(1.0, float(state.get("tension_level", 0.0)) + 0.2)
            state["control_level"] = max(0.0, float(state.get("control_level", 0.5)) - 0.1)
        elif conflict_intensity > 0.5:
            state["tension_level"] = min(1.0, float(state.get("tension_level", 0.0)) + 0.1)

        # Beat-specific emotion transitions
        if beat_type in _BEAT_EMOTION_MAP:
            primary, secondary = _BEAT_EMOTION_MAP[beat_type]
            state["primary_emotion"] = primary
            if secondary is not None:
                state["secondary_emotion"] = secondary

        # Openness shifts on confession / revelation
        if beat_type in {"confession", "revelation"}:
            state["openness_level"] = min(1.0, float(state.get("openness_level", 0.5)) + 0.15)

        # Update scene_goal from beat if provided
        if beat.get("dramatic_intent"):
            state["scene_goal"] = beat["dramatic_intent"]

        return state
