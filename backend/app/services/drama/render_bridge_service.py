"""render_bridge_service — converts Drama Engine output to the render bridge format.

Item 25: Output format for render bridge.

The render bridge payload is injected into the video render pipeline.  It
contains everything the Avatar Acting Model and camera planner need to render
a scene, expressed in the format defined by the problem statement.
"""
from __future__ import annotations

from typing import Any

from app.services.drama.drama_telemetry_engine import DramaTelemetryEngine
from app.services.drama.fake_drama_validator import FakeDramaValidator

_telemetry_engine = DramaTelemetryEngine()
_validator = FakeDramaValidator()


# ---------------------------------------------------------------------------
# Emotion normalisation helpers
# ---------------------------------------------------------------------------

def _emotion_dict_from_state(emotion_state: dict[str, Any]) -> dict[str, float]:
    """Build a normalised emotion float dict from a character emotion_state."""
    mapping = {
        "anger": "anger_level",
        "fear": "fear_level",
        "shame": "shame_level",
        "dominance": "dominance_level",
        "control": "control_level",
        "openness": "openness_level",
        "vulnerability": "vulnerability_level",
    }
    out: dict[str, float] = {}
    for label, state_key in mapping.items():
        val = emotion_state.get(state_key) or emotion_state.get(label)
        if val is not None:
            out[label] = round(float(val), 3)
    return out


def _acting_dict_from_entry(acting_entry: dict[str, Any]) -> dict[str, str]:
    """Build an acting instruction dict from a character_acting entry."""
    line_delivery = acting_entry.get("line_delivery") or {}
    gaze = (
        acting_entry.get("gaze")
        or acting_entry.get("gaze_style")
        or acting_entry.get("gaze_preset")
        or "neutral"
    )
    return {
        "tempo": str(line_delivery.get("tempo") or "moderate"),
        "gaze": str(gaze),
        "micro_expression": str(acting_entry.get("micro_expression") or "neutral"),
        "movement": str(acting_entry.get("body_language") or "neutral_balanced"),
        "voice_pressure": str(line_delivery.get("voice_pressure") or "normal"),
        "pause": str(line_delivery.get("pause") or "measured"),
    }


def _resolve_camera_mode(scene_drama: dict[str, Any]) -> str:
    outcome = str(scene_drama.get("outcome_type") or "neutral")
    pressure = float(scene_drama.get("pressure_level") or 0.0)
    if outcome in {"moral_power_flip", "betrayal", "exposure"}:
        return "power_instability"
    if pressure > 0.8:
        return "high_tension_lockdown"
    if pressure > 0.5:
        return "rising_conflict"
    return "neutral_observe"


def _resolve_camera_movement(outcome_type: str) -> str:
    return {
        "moral_power_flip": "controlled_push_in_at_exposure",
        "betrayal": "slow_push_reveal",
        "exposure": "arc_in_at_reveal",
        "confrontation": "push_in_steady",
        "confession": "slow_dolly_in",
    }.get(outcome_type, "static_observational")


def _resolve_framing(scene_drama: dict[str, Any]) -> str | None:
    dominant = scene_drama.get("dominant_character_id")
    turning_point = scene_drama.get("scene_turning_point")
    if dominant and turning_point:
        return f"{dominant}_center_breaks_after_turn"
    return None


def _build_focus_order(scene_drama: dict[str, Any], character_acting: list[dict[str, Any]]) -> list[str]:
    """Order characters: dominant first, then emotional center, then rest."""
    dominant = scene_drama.get("dominant_character_id")
    emotional_center = scene_drama.get("emotional_center_character_id")
    all_ids = [ca["character_id"] for ca in character_acting]
    order: list[str] = []
    if dominant and dominant in all_ids:
        order.append(dominant)
    if emotional_center and emotional_center in all_ids and emotional_center != dominant:
        order.append(emotional_center)
    for cid in all_ids:
        if cid not in order:
            order.append(cid)
    return order


def _build_blocking_instructions(
    scene_drama: dict[str, Any],
    blocking_directives: list[dict[str, Any]],
) -> list[dict[str, str]]:
    dominant = scene_drama.get("dominant_character_id")
    emotional_center = scene_drama.get("emotional_center_character_id")
    out: list[dict[str, str]] = []
    for bd in blocking_directives:
        cid = bd.get("character_id", "")
        spatial = bd.get("spatial_position") or "neutral"
        movement_cue = bd.get("movement_cue") or ""

        # Narrative blocking
        if cid == dominant:
            blocking = f"holds_{spatial}_then_loses_spatial_control"
        elif cid == emotional_center:
            blocking = "stays_edge_avoids_eye_contact"
        else:
            blocking = f"steps_into_frame_before_line" if movement_cue else f"holds_{spatial}"

        out.append({"character_id": cid, "blocking": blocking})
    return out


def _build_relationship_shifts(power_shifts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ps in power_shifts:
        rel_deltas = ps.get("relationship_deltas") or {}
        out.append({
            "source": ps.get("from_character_id", ""),
            "target": ps.get("to_character_id", ""),
            "trust_delta": round(float(
                rel_deltas.get("trust_shift_delta")
                if rel_deltas.get("trust_shift_delta") is not None
                else rel_deltas.get("trust_level") or 0.0
            ), 3),
            "resentment_delta": round(float(rel_deltas.get("resentment_level") or 0.0), 3),
            "dominance_delta": round(-float(ps.get("magnitude") or 0.0), 3),
            "fear_delta": round(float(rel_deltas.get("fear_level") or 0.0), 3),
            "hidden_agenda_delta": round(float(rel_deltas.get("hidden_agenda_score") or 0.0), 3),
            "shame_delta": round(float(rel_deltas.get("shame_level") or 0.0), 3),
        })
    return out


class RenderBridgeService:
    """Converts a DramaCompilerService result into the render bridge payload.

    Usage
    -----
    service = RenderBridgeService()
    payload = service.build(
        scene_id="scene_012",
        project_id="proj_x",
        drama_result=compiler.compile(...),
        scene_history=[...],
        previous_states={...},
    )
    """

    def build(
        self,
        *,
        scene_id: str,
        project_id: str,
        episode_id: str | None = None,
        drama_result: dict[str, Any],
        scene_history: list[dict[str, Any]] | None = None,
        previous_states: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build the full render bridge payload.

        Parameters
        ----------
        drama_result:
            Output of DramaCompilerService.compile().
        scene_history:
            List of previous scene_drama dicts (for anti-fake-drama checks).
        previous_states:
            Mapping character_id → previous scene state (for rule 5 check).

        Returns
        -------
        dict matching RenderBridgeOutputSchema.
        """
        scene_drama = drama_result.get("scene_drama", {})
        character_acting = drama_result.get("character_acting", [])
        power_shifts = drama_result.get("power_shifts", [])
        blocking_directives = drama_result.get("blocking_directives", [])
        tension_analysis = drama_result.get("tension_analysis", {})

        # Run fake-drama validation
        fake_violations = _validator.validate(
            drama_result=drama_result,
            scene_history=scene_history,
            previous_states=previous_states,
        )

        # Compute scene telemetry
        scene_telemetry = _telemetry_engine.compute_scene_telemetry(
            scene_id=scene_id,
            project_id=project_id,
            episode_id=episode_id,
            drama_result=drama_result,
            fake_drama_violations=fake_violations,
        )

        # drama_state section
        outcome_type = str(scene_drama.get("outcome_type") or "neutral")
        drama_state: dict[str, Any] = {
            "tension_score": scene_telemetry["tension_score"],
            "dominant_character_id": scene_drama.get("dominant_character_id"),
            "emotional_center_character_id": scene_drama.get("emotional_center_character_id"),
            "turning_point": scene_drama.get("scene_turning_point"),
            "outcome_type": outcome_type,
            "scene_temperature": tension_analysis.get("scene_temperature"),
            "pressure_level": tension_analysis.get("pressure_level"),
            "visible_conflict": scene_drama.get("visible_conflict"),
            "hidden_conflict": scene_drama.get("hidden_conflict"),
        }

        # character_updates section
        character_updates: list[dict[str, Any]] = []
        for ca in character_acting:
            cid = ca["character_id"]
            emotion_state = ca.get("emotion_state") or {}
            character_updates.append({
                "character_id": cid,
                "emotion": _emotion_dict_from_state(emotion_state),
                "acting": _acting_dict_from_entry(ca),
            })

        # relationship_shifts section
        relationship_shifts = _build_relationship_shifts(power_shifts)

        # camera_plan section
        camera_plan: dict[str, Any] = {
            "mode": _resolve_camera_mode(scene_drama),
            "focus_order": _build_focus_order(scene_drama, character_acting),
            "movement": _resolve_camera_movement(outcome_type),
            "framing": _resolve_framing(scene_drama),
        }

        # blocking_plan section
        blocking_plan = _build_blocking_instructions(scene_drama, blocking_directives)

        return {
            "scene_id": scene_id,
            "drama_state": drama_state,
            "character_updates": character_updates,
            "relationship_shifts": relationship_shifts,
            "camera_plan": camera_plan,
            "blocking_plan": blocking_plan,
            "telemetry": scene_telemetry,
            "fake_drama_violations": fake_violations,
            "metadata": {
                "project_id": project_id,
                "episode_id": episode_id,
            },
        }
