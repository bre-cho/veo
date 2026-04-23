"""camera_drama_engine — maps drama state to camera/shot directives.

Camera serves psychology, not aesthetics. This engine translates:
    power position × tension × subtext → shot type + movement + angle
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Shot grammar tables
# ---------------------------------------------------------------------------

_POWER_SHOT_MAP: dict[str, str] = {
    "dominant": "low_angle_tight",
    "submissive": "high_angle_wide",
    "exposed": "extreme_close_static",
    "neutral": "medium_eye_level",
}

_TENSION_MOVEMENT_MAP: dict[str, str] = {
    "explosive": "slow_push_in",
    "heated": "slight_drift_in",
    "warm": "static_with_subtle_reframe",
    "cold": "static_wide",
}

_SUBTEXT_ANGLE_MAP: dict[str, str] = {
    "please_stop_looking_deeper": "tight_close_push_in",
    "hurt_them_before_they_see_me": "dutch_angle_slight",
    "i_already_know_the_answer": "low_angle_composed",
    "do_not_come_closer": "wide_maintaining_distance",
    "speaking_but_not_trusting": "two_shot_neutral",
    "control_through_desire": "low_soft_light_close",
    "direct": "medium_eye_level",
}

_OUTCOME_CAMERA_MAP: dict[str, str] = {
    "betrayal": "static_wide_negative_space",
    "exposure": "close_push_in_face",
    "collapse": "wide_static_isolated",
    "victory": "low_angle_forward_blocking",
    "confession": "tight_close_static",
    "reconciliation": "gentle_close_two_shot",
}


class CameraDramaEngine:
    """Derives camera/shot directive from scene drama state."""

    def build_directive(
        self,
        character_id: str,
        scene_id: str,
        character_state: dict[str, Any],
        scene_drama: dict[str, Any],
        subtext: str,
        outcome_type: str | None = None,
    ) -> dict[str, Any]:
        """Return a blocking/camera directive dict.

        Returns
        -------
        dict compatible with ``BlockingDirectiveSchema``.
        """
        power_position = str(character_state.get("current_power_position") or "neutral")
        scene_temperature = str(scene_drama.get("scene_temperature") or "warm")

        shot_type = _POWER_SHOT_MAP.get(power_position, "medium_eye_level")
        movement = _TENSION_MOVEMENT_MAP.get(scene_temperature, "static_wide")
        angle_hint = _SUBTEXT_ANGLE_MAP.get(subtext, "medium_eye_level")

        # Outcome overrides everything when strong
        if outcome_type and outcome_type in _OUTCOME_CAMERA_MAP:
            shot_type = _OUTCOME_CAMERA_MAP[outcome_type]
            movement = "slow_push_in" if outcome_type == "exposure" else movement

        # Spatial position heuristic
        if power_position == "dominant":
            spatial_position = "foreground_centre"
            distance_from_target = "medium"
        elif power_position == "exposed":
            spatial_position = "midground_isolated"
            distance_from_target = "close"
        else:
            spatial_position = "midground"
            distance_from_target = "medium"

        return {
            "scene_id": scene_id,
            "character_id": character_id,
            "spatial_position": spatial_position,
            "distance_from_target": distance_from_target,
            "movement_cue": movement,
            "shot_type_preference": shot_type,
            "camera_angle_preference": angle_hint,
            "drama_reason": f"{power_position}_{subtext}",
        }
