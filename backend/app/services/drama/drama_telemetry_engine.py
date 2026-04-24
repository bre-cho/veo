"""drama_telemetry_engine — computes scene, character and episode-level telemetry.

Item 22: Telemetry / Scorecard
------------------------------
Produces the metrics the self-learning system needs to improve drama quality
over time.

Scene-level metrics
    tension_score, power_shift_magnitude, trust_shift_magnitude,
    exposure_risk_score, subtext_density, chemistry_score,
    continuity_integrity_score

Character-level metrics
    arc_momentum, mask_break_progress, emotional_variation_range,
    relation_complexity_index

Episode-level metrics
    betrayal_count, alliance_flip_count, unresolved_tension_load,
    emotional_continuity_quality, dominant_relationship_arc_strength
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Score thresholds
# ---------------------------------------------------------------------------

_GRADE_PEAK = 82.0
_GRADE_STRONG = 68.0
_GRADE_NORMAL = 48.0


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _to_100(value: float) -> float:
    return round(_clamp(value) * 100, 1)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class DramaTelemetryEngine:
    """Compute scene, character and episode-level drama telemetry."""

    # ------------------------------------------------------------------
    # Scene-level
    # ------------------------------------------------------------------

    def compute_scene_telemetry(
        self,
        *,
        scene_id: str,
        project_id: str,
        episode_id: str | None = None,
        drama_result: dict[str, Any],
        fake_drama_violations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return scene-level telemetry from a DramaCompilerService result.

        Parameters
        ----------
        drama_result:
            Dict returned by ``DramaCompilerService.compile()``.
        fake_drama_violations:
            List of anti-fake-drama rule names that fired (from FakeDramaValidator).
        """
        scene_drama = drama_result.get("scene_drama", {})
        tension_analysis = drama_result.get("tension_analysis", {})
        power_shifts = drama_result.get("power_shifts", [])
        inner_state_updates = drama_result.get("inner_state_updates", [])
        dialogue_subtexts = drama_result.get("dialogue_subtexts", [])
        scene_law_violations = drama_result.get("scene_law_violations", [])

        # tension_score (0–100): pressure_level from tension analysis
        tension_score = _to_100(tension_analysis.get("pressure_level", 0.0))

        # power_shift_magnitude (0–100): max magnitude across all power shifts
        power_shift_mag = max(
            (abs(ps.get("magnitude", 0.0)) for ps in power_shifts), default=0.0
        )
        power_shift_magnitude = _to_100(power_shift_mag)

        # trust_shift_magnitude (0–100): max abs trust delta across power-shift
        # relationship deltas; fall back to scene_drama for compatibility.
        trust_shift_deltas = [
            abs(rel_delta.get("trust_shift_delta", 0.0))
            for ps in power_shifts
            for rel_delta in ps.get("relationship_deltas", [])
            if isinstance(rel_delta, dict) and rel_delta.get("trust_shift_delta") is not None
        ]
        trust_shift_magnitude = _to_100(
            max(
                trust_shift_deltas,
                default=abs(scene_drama.get("trust_shift_delta", 0.0)),
            )
        )

        # exposure_risk_score (0–100): secret load + exposure shift
        exposure_shift = abs(scene_drama.get("exposure_shift_delta", 0.0))
        secret_loads = [
            float(u.get("updated_state", {}).get("current_secret_load", 0.0))
            for u in inner_state_updates
        ]
        avg_secret = sum(secret_loads) / max(len(secret_loads), 1)
        exposure_risk_score = _to_100((exposure_shift + avg_secret) / 2)

        # subtext_density (0–100): how many subtexts are non-direct / non-inform
        non_direct = sum(
            1 for d in dialogue_subtexts
            if d.get("subtext_label", "direct") not in {"direct", "inform"}
        )
        subtext_density = _to_100(
            non_direct / max(len(dialogue_subtexts), 1)
        )

        # chemistry_score (0–100): derived from relationship engine output inside drama
        # We proxy this as mean attraction + intimacy across relationship deltas
        relationship_deltas = []
        for ps in power_shifts:
            for _key, val in ps.get("relationship_deltas", {}).items():
                relationship_deltas.append(abs(float(val)))
        chemistry_score = _to_100(
            sum(relationship_deltas) / max(len(relationship_deltas), 1)
        ) if relationship_deltas else 0.0

        # continuity_integrity_score (0–100): penalise scene law violations
        continuity_integrity_score = max(
            0.0,
            100.0 - len(scene_law_violations) * 15.0
        )
        # Also penalise fake-drama violations
        violations = fake_drama_violations or []
        continuity_integrity_score = max(
            0.0,
            continuity_integrity_score - len(violations) * 10.0
        )

        # Total scene score: weighted average
        total_scene_score = round(
            tension_score * 0.22
            + power_shift_magnitude * 0.18
            + trust_shift_magnitude * 0.12
            + exposure_risk_score * 0.12
            + subtext_density * 0.16
            + chemistry_score * 0.10
            + continuity_integrity_score * 0.10,
            1,
        )

        grade = (
            "peak" if total_scene_score >= _GRADE_PEAK
            else "strong" if total_scene_score >= _GRADE_STRONG
            else "normal" if total_scene_score >= _GRADE_NORMAL
            else "flat"
        )

        return {
            "scene_id": scene_id,
            "project_id": project_id,
            "episode_id": episode_id,
            "tension_score": tension_score,
            "power_shift_magnitude": power_shift_magnitude,
            "trust_shift_magnitude": trust_shift_magnitude,
            "exposure_risk_score": exposure_risk_score,
            "subtext_density": subtext_density,
            "chemistry_score": chemistry_score,
            "continuity_integrity_score": continuity_integrity_score,
            "total_scene_score": total_scene_score,
            "scene_grade": grade,
            "fake_drama_violations": violations,
            "metadata": {
                "scene_temperature": tension_analysis.get("scene_temperature"),
                "dominant_tension_type": tension_analysis.get("dominant_tension_type"),
                "scene_law_violation_count": len(scene_law_violations),
            },
        }

    # ------------------------------------------------------------------
    # Character-level
    # ------------------------------------------------------------------

    def compute_character_telemetry(
        self,
        *,
        scene_id: str,
        project_id: str,
        drama_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return per-character telemetry list from a DramaCompilerService result."""
        inner_state_updates = drama_result.get("inner_state_updates", [])
        arc_updates = drama_result.get("arc_updates", [])
        character_acting = drama_result.get("character_acting", [])
        power_shifts = drama_result.get("power_shifts", [])

        arc_map: dict[str, dict[str, Any]] = {
            a["character_id"]: a for a in arc_updates
        }
        power_shift_counts: dict[str, int] = {}
        for ps in power_shifts:
            for cid in (ps.get("from_character_id"), ps.get("to_character_id")):
                if cid:
                    power_shift_counts[cid] = power_shift_counts.get(cid, 0) + 1

        results: list[dict[str, Any]] = []
        for update in inner_state_updates:
            cid = update["character_id"]
            updated_state = update.get("updated_state", {})
            arc = arc_map.get(cid, {})

            # arc_momentum: how much arc_stage advanced (0 if same, 1 if large jump)
            arc_stage = arc.get("arc_stage", "ordinary_world")
            arc_stage_order = [
                "ordinary_world", "call_to_change", "refusal",
                "mask_stable", "first_crack", "dark_night",
                "transformed_state",
            ]
            curr_idx = arc_stage_order.index(arc_stage) if arc_stage in arc_stage_order else 0
            arc_momentum = round(curr_idx / max(len(arc_stage_order) - 1, 1), 3)

            # mask_break_progress from arc
            mask_break_progress = round(float(arc.get("mask_break_level") or 0.0), 3)

            # emotional_variation_range: spread of emotion levels
            emotion_levels = [
                float(updated_state.get("anger_level") or 0.0),
                float(updated_state.get("fear_level") or 0.0),
                float(updated_state.get("shame_level") or 0.0),
                float(updated_state.get("desire_level") or 0.0),
                float(updated_state.get("vulnerability_level") or 0.0),
            ]
            emotional_variation_range = round(max(emotion_levels) - min(emotion_levels), 3)

            # relation_complexity_index: number of power shifts involving this character
            rel_complexity = power_shift_counts.get(cid, 0)
            relation_complexity_index = round(min(rel_complexity / 5.0, 1.0), 3)

            results.append({
                "character_id": cid,
                "scene_id": scene_id,
                "project_id": project_id,
                "arc_momentum": arc_momentum,
                "mask_break_progress": mask_break_progress,
                "emotional_variation_range": emotional_variation_range,
                "relation_complexity_index": relation_complexity_index,
                "metadata": {"arc_stage": arc_stage},
            })

        return results

    # ------------------------------------------------------------------
    # Episode-level
    # ------------------------------------------------------------------

    def compute_episode_telemetry(
        self,
        *,
        project_id: str,
        episode_id: str,
        scene_telemetry_list: list[dict[str, Any]],
        drama_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate episode-level telemetry from a list of scene results.

        Parameters
        ----------
        scene_telemetry_list:
            List of scene-level telemetry dicts (output of compute_scene_telemetry).
        drama_results:
            List of DramaCompilerService results for all scenes in the episode.
        """
        betrayal_count = 0
        alliance_flip_count = 0
        tension_loads: list[float] = []
        continuity_scores: list[float] = []

        for result in drama_results:
            inner_updates = result.get("inner_state_updates", [])
            for upd in inner_updates:
                outcome = upd.get("outcome_type", "")
                if "betrayal" in outcome:
                    betrayal_count += 1
                if "alliance" in outcome and "flip" in outcome:
                    alliance_flip_count += 1

            scene_drama = result.get("scene_drama", {})
            tension_loads.append(float(scene_drama.get("power_shift_delta") or 0.0))

        for st in scene_telemetry_list:
            continuity_scores.append(float(st.get("continuity_integrity_score") or 0.0))

        unresolved_tension_load = round(sum(tension_loads) / max(len(tension_loads), 1), 3)

        emotional_continuity_quality = round(
            sum(continuity_scores) / max(len(continuity_scores), 1) / 100.0, 3
        )

        # dominant_relationship_arc_strength: mean power_shift_magnitude across scenes
        power_magnitudes = [
            float(st.get("power_shift_magnitude") or 0.0)
            for st in scene_telemetry_list
        ]
        dominant_relationship_arc_strength = round(
            sum(power_magnitudes) / max(len(power_magnitudes), 1) / 100.0, 3
        )

        return {
            "project_id": project_id,
            "episode_id": episode_id,
            "betrayal_count": betrayal_count,
            "alliance_flip_count": alliance_flip_count,
            "unresolved_tension_load": unresolved_tension_load,
            "emotional_continuity_quality": emotional_continuity_quality,
            "dominant_relationship_arc_strength": dominant_relationship_arc_strength,
            "metadata": {
                "scene_count": len(drama_results),
                "avg_tension_score": round(
                    sum(st.get("tension_score", 0.0) for st in scene_telemetry_list)
                    / max(len(scene_telemetry_list), 1),
                    1,
                ),
            },
        }
