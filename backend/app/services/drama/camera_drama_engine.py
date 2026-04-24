"""camera_drama_engine — maps drama state to camera/shot directives.

Section 15: Camera Drama Engine
---------------------------------
Camera serves psychology, not aesthetics.

Camera decisions based on psychology (section 15.1):
  - power holder: frame stable, centered, controlled
  - losing control: tighter framing, breath-visible pacing
  - being exposed: hold longer, less escape cutting
  - manipulator: delayed reveal, eye-lock timing
  - wounded character: partial framing, obstruction, negative space

CameraDramaPlan output schema (section 15.2) covers:
  character_focus_priority, emotional_anchor_character_id,
  dominant_visual_axis, lens_psychology_mode, framing_mode,
  eye_line_strategy, reveal_timing, pause_hold_strategy,
  movement_strategy, blocking_sync_notes, continuity_notes,
  shot_sequence.

Lens/shot psychology (section 15.3):
  - wide_with_distance: alienation / social coldness
  - tight_close_up: pressure / internal fracture
  - off_centre: instability / exclusion
  - over_shoulder_dominance: who owns the frame
  - low_motion_locked: authority
  - creeping_push_in: exposure / realisation / dread
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

# Section 15.1: psychology → lens mode
_ARCHETYPE_LENS: dict[str, str] = {
    "mentor": "low_motion_locked",          # authority / stability
    "manipulator": "creeping_push_in",      # exposure / dread
    "rebel": "off_centre",                  # instability
    "wounded_observer": "partial_framing",  # obstruction / negative space
    "authority": "low_motion_locked",       # structural control
    "observer": "wide_with_distance",       # alienation / social reading
}

# Section 15.3: lens mode descriptions
_LENS_PSYCHOLOGY: dict[str, str] = {
    "wide_with_distance": "alienation_social_coldness",
    "tight_close_up": "pressure_internal_fracture",
    "off_centre": "instability_exclusion",
    "over_shoulder_dominance": "frame_ownership",
    "low_motion_locked": "authority_controlled",
    "creeping_push_in": "exposure_realisation_dread",
    "partial_framing": "wounded_obstruction_negative_space",
}


# ---------------------------------------------------------------------------
# Framing and eye-line decision tables
# ---------------------------------------------------------------------------

_POWER_FRAMING: dict[str, str] = {
    "dominant": "centered_stable",
    "exposed": "tight_off_centre",
    "submissive": "high_angle_wide",
    "neutral": "medium_two_shot",
}

_POWER_EYE_LINE: dict[str, str] = {
    "dominant": "top_down",
    "exposed": "avoidant_eye_lock",
    "submissive": "upward_deferential",
    "neutral": "level",
}

_REVEAL_TIMING_MAP: dict[str, str] = {
    "betrayal": "delayed",
    "exposure": "withheld_then_hold",
    "confession": "immediate",
    "victory": "immediate",
    "collapse": "held_long",
    "reconciliation": "gentle_reveal",
    "neutral": "immediate",
}

_PAUSE_HOLD_MAP: dict[str, str] = {
    "explosive": "hold_after_peak",
    "heated": "brief_hold_on_reaction",
    "warm": "natural_edit_rhythm",
    "cold": "long_static_hold",
}


class CameraDramaEngine:
    """Derives camera/shot directive and full scene camera plan from drama state."""

    def build_directive(
        self,
        character_id: str,
        scene_id: str,
        character_state: dict[str, Any],
        scene_drama: dict[str, Any],
        subtext: str,
        outcome_type: str | None = None,
    ) -> dict[str, Any]:
        """Return a blocking/camera directive dict (section 15).

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

    def build_scene_camera_plan(
        self,
        scene_id: str,
        characters: list[dict[str, Any]],
        state_map: dict[str, dict[str, Any]],
        scene_drama: dict[str, Any],
        blocking_directives: list[dict[str, Any]],
        outcome_type: str,
    ) -> dict[str, Any]:
        """Build the full CameraDramaPlanSchema-compatible dict for a scene.

        Parameters
        ----------
        characters:
            List of character profile dicts.
        state_map:
            character_id → character_state dict.
        scene_drama:
            Assembled scene drama state.
        blocking_directives:
            Per-character blocking directives already computed.
        outcome_type:
            Scene outcome type.

        Returns
        -------
        dict compatible with ``CameraDramaPlanSchema``.
        """
        scene_temperature = str(scene_drama.get("scene_temperature") or "warm")
        dominant_id = scene_drama.get("dominant_character_id")
        anchor_id = scene_drama.get("emotional_center_character_id") or dominant_id

        # Focus priority: anchor first, then by internal conflict descending
        def _priority_score(c: dict[str, Any]) -> float:
            cid = c.get("id") or c.get("avatar_id") or c["name"]
            state = state_map.get(cid, {})
            base = float(state.get("internal_conflict_level") or 0.0)
            if cid == anchor_id:
                base += 1.0
            return base

        sorted_chars = sorted(characters, key=_priority_score, reverse=True)
        focus_priority = [
            c.get("id") or c.get("avatar_id") or c["name"]
            for c in sorted_chars
        ]

        # Lens psychology: most exposed character drives mode
        anchor_state = state_map.get(str(anchor_id), {}) if anchor_id else {}
        anchor_archetype = ""
        for c in characters:
            cid = c.get("id") or c.get("avatar_id") or c["name"]
            if cid == anchor_id:
                anchor_archetype = str(c.get("archetype") or "observer")
                break
        lens_mode = _ARCHETYPE_LENS.get(anchor_archetype, "wide_with_distance")

        # Override lens mode for outcome
        if outcome_type == "exposure":
            lens_mode = "tight_close_up"
        elif outcome_type in {"betrayal", "collapse"}:
            lens_mode = "wide_with_distance"
        elif outcome_type == "confession":
            lens_mode = "tight_close_up"

        anchor_power = str(anchor_state.get("current_power_position") or "neutral")
        framing_mode = _POWER_FRAMING.get(anchor_power, "medium_two_shot")
        eye_line = _POWER_EYE_LINE.get(anchor_power, "level")
        reveal_timing = _REVEAL_TIMING_MAP.get(outcome_type, "immediate")
        pause_hold = _PAUSE_HOLD_MAP.get(scene_temperature, "natural_edit_rhythm")

        # Movement strategy from tension
        tension_score = float(scene_drama.get("pressure_level") or 0.5) * 100
        if tension_score >= 70:
            movement_strategy = "creeping_push_in"
        elif tension_score >= 45:
            movement_strategy = "slight_drift"
        else:
            movement_strategy = "static_observation"

        # Shot sequence: one entry per character + opening/closing shots
        shot_sequence: list[dict[str, Any]] = [
            {
                "order": 0,
                "shot_type": "establishing_wide",
                "character_focus": None,
                "reason": "scene_entry",
            }
        ]
        for i, bd in enumerate(blocking_directives):
            shot_sequence.append({
                "order": i + 1,
                "shot_type": bd.get("shot_type_preference", "medium"),
                "character_focus": bd.get("character_id"),
                "movement": bd.get("movement_cue"),
                "angle": bd.get("camera_angle_preference"),
                "reason": bd.get("drama_reason"),
            })
        shot_sequence.append({
            "order": len(blocking_directives) + 1,
            "shot_type": _OUTCOME_CAMERA_MAP.get(outcome_type, "medium_eye_level"),
            "character_focus": anchor_id,
            "reason": f"scene_close_{outcome_type}",
        })

        blocking_sync = "; ".join(
            f"{bd['character_id']}:{bd.get('movement_cue', 'static')}"
            for bd in blocking_directives
        )

        return {
            "scene_id": scene_id,
            "character_focus_priority": focus_priority,
            "emotional_anchor_character_id": anchor_id,
            "dominant_visual_axis": "horizontal" if len(characters) > 2 else "vertical",
            "lens_psychology_mode": lens_mode,
            "framing_mode": framing_mode,
            "eye_line_strategy": eye_line,
            "reveal_timing": reveal_timing,
            "pause_hold_strategy": pause_hold,
            "movement_strategy": movement_strategy,
            "blocking_sync_notes": blocking_sync,
            "continuity_notes": f"outcome={outcome_type} temperature={scene_temperature}",
            "shot_sequence": shot_sequence,
        }
