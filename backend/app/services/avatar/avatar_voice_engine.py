"""avatar_voice_engine — resolves episode-role-aware voice delivery parameters.

Takes a base voice_profile dict (from the registry) and adjusts intensity,
speaking_rate, and pitch based on the current episode role to create natural
dramatic pacing variation across a series.

Episode role adjustments
------------------------
opener  : intensity +0.1 (hook energy)
reveal  : speaking_rate -0.05 (pause for effect)
escalation: intensity +0.15
resolution: speaking_rate -0.05, intensity -0.1 (calmer close)
"""
from __future__ import annotations

from typing import Any


class AvatarVoiceEngine:
    """Applies episode-role modifiers to an avatar's base voice profile."""

    _ROLE_MODIFIERS: dict[str, dict[str, float]] = {
        "opener": {"intensity_delta": 0.1},
        "reveal": {"speaking_rate_delta": -0.05},
        "escalation": {"intensity_delta": 0.15},
        "resolution": {"speaking_rate_delta": -0.05, "intensity_delta": -0.1},
        "cliffhanger": {"intensity_delta": 0.2, "speaking_rate_delta": 0.05},
    }

    _INTENSITY_BOUNDS = (0.5, 1.5)
    _RATE_BOUNDS = (0.7, 1.3)
    _PITCH_BOUNDS = (0.8, 1.2)

    def resolve_voice_context(
        self,
        *,
        voice_profile: dict[str, Any],
        episode_role: str | None,
    ) -> dict[str, Any]:
        """Return a voice context dict with episode-role adjustments applied.

        Parameters
        ----------
        voice_profile:
            Base voice settings from the avatar registry
            (provider, voice_id, delivery_style, speaking_rate, pitch, intensity).
        episode_role:
            Current episode role label (opener / reveal / escalation / …).
            ``None`` returns the base profile unchanged.

        Returns
        -------
        A new dict — the input is never mutated.
        """
        resolved: dict[str, Any] = dict(voice_profile or {})
        modifiers = self._ROLE_MODIFIERS.get(episode_role or "", {})

        if "intensity_delta" in modifiers:
            base = float(resolved.get("intensity", 1.0))
            lo, hi = self._INTENSITY_BOUNDS
            resolved["intensity"] = max(lo, min(hi, base + modifiers["intensity_delta"]))

        if "speaking_rate_delta" in modifiers:
            base = float(resolved.get("speaking_rate", 1.0))
            lo, hi = self._RATE_BOUNDS
            resolved["speaking_rate"] = max(lo, min(hi, base + modifiers["speaking_rate_delta"]))

        return resolved
