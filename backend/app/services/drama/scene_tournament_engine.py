"""scene_tournament_engine — Scene Variant Tournament Engine (item 26).

For each scene, the engine generates 2–4 variant compilations with slightly
different beat parameters.  Each variant is scored on tension, subtext,
chemistry and power-shift.  The winning variant's "DNA" is stored so the
system learns which dramatic patterns perform best for a given relationship type.

Tournament DNA represents the beat + relationship parameters of a winning scene
variant, keyed by relationship archetype pair (e.g. "authority_vs_rebel").
"""
from __future__ import annotations

import random
from typing import Any

from app.services.drama.drama_compiler_service import DramaCompilerService
from app.services.drama.drama_telemetry_engine import DramaTelemetryEngine
from app.services.drama.fake_drama_validator import FakeDramaValidator

_compiler = DramaCompilerService()
_telemetry = DramaTelemetryEngine()
_validator = FakeDramaValidator()

# ---------------------------------------------------------------------------
# In-memory DNA store (production systems would persist this to DB)
# ---------------------------------------------------------------------------

_WINNER_DNA_STORE: dict[str, dict[str, Any]] = {}


def get_winner_dna(relationship_key: str) -> dict[str, Any] | None:
    """Retrieve the stored winner DNA for a relationship pair."""
    return _WINNER_DNA_STORE.get(relationship_key)


def list_winner_dna() -> dict[str, dict[str, Any]]:
    """Return all stored winner DNA entries."""
    return dict(_WINNER_DNA_STORE)


# ---------------------------------------------------------------------------
# Variant generation helpers
# ---------------------------------------------------------------------------

_BEAT_OUTCOME_VARIANTS = [
    "neutral",
    "confrontation",
    "exposure",
    "moral_power_flip",
    "betrayal",
    "confession",
    "silent_standoff",
]

_TENSION_VARIANTS = [
    0.3,   # restrained / cold
    0.55,  # simmering
    0.75,  # heated
    0.9,   # near-explosive
]

_SUBTEXT_VARIANTS = [
    "direct",
    "i_already_know_more_than_i_say",
    "i_control_the_meaning_of_this_moment",
    "you_will_not_control_me",
    "i_see_everything_but_cannot_safely_say_it",
    "you_exist_inside_my_frame",
]


def _make_variant_beat(base_beat: dict[str, Any], variant_index: int) -> dict[str, Any]:
    """Produce a slightly different beat for variant `variant_index`."""
    beat = dict(base_beat)

    # Cycle through outcome types
    if variant_index < len(_BEAT_OUTCOME_VARIANTS):
        beat["outcome_type"] = _BEAT_OUTCOME_VARIANTS[variant_index]

    # Vary conflict intensity
    tension_pool = _TENSION_VARIANTS
    beat["conflict_intensity"] = tension_pool[variant_index % len(tension_pool)]
    beat["pressure_level"] = beat["conflict_intensity"]

    # Vary spoken intent / subtext seed
    beat["spoken_intent"] = _SUBTEXT_VARIANTS[variant_index % len(_SUBTEXT_VARIANTS)]

    return beat


def _relationship_key_from_characters(characters: list[dict[str, Any]]) -> str:
    """Build a stable relationship key from character archetypes, e.g. 'authority_vs_rebel'."""
    archetypes = sorted(
        str(c.get("archetype") or c.get("acting_preset_seed") or "observer")
        for c in characters[:2]  # use primary pair
    )
    return "_vs_".join(archetypes)


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------

def _score_variant(
    drama_result: dict[str, Any],
    scene_id: str,
    project_id: str,
) -> float:
    """Compute a combined tournament score for one variant (0–100)."""
    violations = _validator.validate(drama_result=drama_result)
    telemetry = _telemetry.compute_scene_telemetry(
        scene_id=scene_id,
        project_id=project_id,
        drama_result=drama_result,
        fake_drama_violations=violations,
    )
    # Weighted tournament score: tension + subtext + power-shift + chemistry
    score = (
        telemetry["tension_score"] * 0.30
        + telemetry["subtext_density"] * 0.25
        + telemetry["power_shift_magnitude"] * 0.25
        + telemetry["chemistry_score"] * 0.20
    )
    # Penalise fake-drama violations
    score -= len(violations) * 5.0
    return round(max(0.0, score), 2)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class SceneTournamentEngine:
    """Generates 2–4 scene variants, scores them, returns the winner.

    Usage
    -----
    engine = SceneTournamentEngine()
    result = engine.run_tournament(
        project_id="proj_x",
        scene_id="scene_012",
        base_beat={...},
        characters=[...],
        character_states=[...],
        relationships=[...],
        memory_traces=[...],
        num_variants=3,
    )
    """

    def run_tournament(
        self,
        *,
        project_id: str,
        scene_id: str,
        episode_id: str | None = None,
        base_beat: dict[str, Any],
        characters: list[dict[str, Any]],
        character_states: list[dict[str, Any]] | None = None,
        relationships: list[dict[str, Any]] | None = None,
        memory_traces: list[dict[str, Any]] | None = None,
        arc_progresses: list[dict[str, Any]] | None = None,
        num_variants: int = 3,
    ) -> dict[str, Any]:
        """Run the scene tournament.

        Parameters
        ----------
        base_beat:
            The baseline beat dict to vary.
        characters:
            Character profile list.
        num_variants:
            Number of variants to generate (2–4).  Clamped to [2, 4].

        Returns
        -------
        dict with keys:
            winner_variant_index: int
            winner_score: float
            winner_drama_result: dict
            winner_beat: dict
            all_variants: list[dict]  (index, score, beat, drama_result)
            relationship_key: str
            dna_stored: bool
        """
        num_variants = max(2, min(4, num_variants))
        relationship_key = _relationship_key_from_characters(characters)

        variants: list[dict[str, Any]] = []
        best_score = -1.0
        best_index = 0

        for idx in range(num_variants):
            variant_beat = _make_variant_beat(base_beat, idx)
            variant_scene_id = f"{scene_id}_v{idx}"

            drama_result = _compiler.compile(
                project_id=project_id,
                scene_id=variant_scene_id,
                episode_id=episode_id,
                beat=variant_beat,
                characters=characters,
                character_states=character_states,
                relationships=relationships,
                memory_traces=memory_traces,
                arc_progresses=arc_progresses,
            )
            score = _score_variant(drama_result, variant_scene_id, project_id)

            variants.append({
                "variant_index": idx,
                "score": score,
                "beat": variant_beat,
                "drama_result": drama_result,
            })

            if score > best_score:
                best_score = score
                best_index = idx

        winner = variants[best_index]

        # Build winner DNA
        winner_dna: dict[str, Any] = {
            "relationship_key": relationship_key,
            "winner_outcome_type": winner["beat"].get("outcome_type", "neutral"),
            "winner_conflict_intensity": winner["beat"].get("conflict_intensity", 0.5),
            "winner_spoken_intent": winner["beat"].get("spoken_intent", "direct"),
            "winner_score": best_score,
            "scene_temperature": (
                winner["drama_result"]
                .get("tension_analysis", {})
                .get("scene_temperature", "cold")
            ),
            "power_shift_magnitude": (
                winner["drama_result"]
                .get("scene_drama", {})
                .get("power_shift_delta", 0.0)
            ),
        }

        # Store winner DNA for this relationship type
        _WINNER_DNA_STORE[relationship_key] = winner_dna
        dna_stored = True

        return {
            "winner_variant_index": best_index,
            "winner_score": best_score,
            "winner_drama_result": winner["drama_result"],
            "winner_beat": winner["beat"],
            "winner_dna": winner_dna,
            "all_variants": [
                {
                    "variant_index": v["variant_index"],
                    "score": v["score"],
                    "beat": v["beat"],
                }
                for v in variants
            ],
            "relationship_key": relationship_key,
            "dna_stored": dna_stored,
        }
