"""chemistry_engine — computes multi-dimensional chemistry between two characters.

Section 13: Chemistry Engine
------------------------------
Chemistry dimensions:
  - tempo_compatibility / mismatch
  - eye_contact_tolerance
  - interruption_rhythm
  - mutual_reading_accuracy
  - emotional_danger
  - attraction_vs_fear_blend
  - speech_completion_tendency
  - silence_comfort_index

Chemistry applies to ALL relationship archetypes, not just romance:
  - mentor / student
  - enemies
  - manipulator / wounded observer
  - authority / rebel
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Archetype-pair chemistry templates
# ---------------------------------------------------------------------------

_ARCHETYPE_PAIR_CHEMISTRY: dict[frozenset[str], dict[str, float]] = {
    frozenset({"mentor", "wounded_observer"}): {
        "tempo_compatibility": 0.7,
        "eye_contact_tolerance": 0.5,
        "interruption_rhythm": 0.3,     # mentor rarely interrupts
        "mutual_reading_accuracy": 0.75,
        "emotional_danger": 0.4,
        "attraction_vs_fear_blend": 0.6,  # slight draw toward safety
        "speech_completion_tendency": 0.4,
        "silence_comfort_index": 0.6,
    },
    frozenset({"mentor", "rebel"}): {
        "tempo_compatibility": 0.3,      # tempo clash
        "eye_contact_tolerance": 0.4,
        "interruption_rhythm": 0.7,      # rebel cuts in
        "mutual_reading_accuracy": 0.5,
        "emotional_danger": 0.6,
        "attraction_vs_fear_blend": 0.5,
        "speech_completion_tendency": 0.3,
        "silence_comfort_index": 0.3,
    },
    frozenset({"manipulator", "wounded_observer"}): {
        "tempo_compatibility": 0.5,
        "eye_contact_tolerance": 0.3,    # observer avoids
        "interruption_rhythm": 0.6,      # manipulator controls
        "mutual_reading_accuracy": 0.8,  # both read each other
        "emotional_danger": 0.85,
        "attraction_vs_fear_blend": 0.3,  # fear dominant
        "speech_completion_tendency": 0.7,  # manipulator finishes sentences
        "silence_comfort_index": 0.2,
    },
    frozenset({"authority", "rebel"}): {
        "tempo_compatibility": 0.2,
        "eye_contact_tolerance": 0.6,    # stare down
        "interruption_rhythm": 0.8,      # rebel constantly interrupts
        "mutual_reading_accuracy": 0.6,
        "emotional_danger": 0.75,
        "attraction_vs_fear_blend": 0.5,
        "speech_completion_tendency": 0.2,
        "silence_comfort_index": 0.2,
    },
}


def _default_chemistry() -> dict[str, float]:
    return {
        "tempo_compatibility": 0.5,
        "eye_contact_tolerance": 0.5,
        "interruption_rhythm": 0.5,
        "mutual_reading_accuracy": 0.5,
        "emotional_danger": 0.0,
        "attraction_vs_fear_blend": 0.5,
        "speech_completion_tendency": 0.5,
        "silence_comfort_index": 0.5,
    }


def _chemistry_type(score: float, dims: dict[str, float]) -> str:
    """Classify chemistry type from score + dimensions."""
    attraction = dims.get("attraction_vs_fear_blend", 0.5)
    danger = dims.get("emotional_danger", 0.0)
    tempo = dims.get("tempo_compatibility", 0.5)
    silence = dims.get("silence_comfort_index", 0.5)

    if danger > 0.7 and attraction < 0.4:
        return "threat_dynamic"
    if danger > 0.6 and attraction > 0.5:
        return "forbidden_tension"
    if score > 0.7 and tempo > 0.6 and silence > 0.6:
        return "deep_resonance"
    if score > 0.6 and attraction > 0.6:
        return "mutual_pull"
    if tempo < 0.3 and danger > 0.5:
        return "power_clash"
    if score > 0.5 and attraction < 0.4:
        return "unfinished_business"
    if score < 0.3:
        return "incompatible"
    return "neutral"


class ChemistryEngine:
    """Computes multi-dimensional chemistry between two characters."""

    def compute(
        self,
        source_id: str,
        target_id: str,
        source_profile: dict[str, Any],
        target_profile: dict[str, Any],
        edge: dict[str, Any] | None = None,
        reverse_edge: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a ChemistrySchema-compatible dict.

        Parameters
        ----------
        source_id, target_id:
            Character identifiers.
        source_profile, target_profile:
            CharacterProfileSchema-compatible dicts.
        edge:
            Optional relationship edge (source → target).
        reverse_edge:
            Optional reverse edge (target → source).

        Returns
        -------
        dict with keys matching ``ChemistrySchema``.
        """
        src_arch = str(source_profile.get("archetype") or "observer")
        tgt_arch = str(target_profile.get("archetype") or "observer")

        # Load archetype template or default
        dims = dict(
            _ARCHETYPE_PAIR_CHEMISTRY.get(frozenset({src_arch, tgt_arch}), {})
            or _default_chemistry()
        )

        # Modulate from edge scores
        if edge:
            attraction = float(edge.get("attraction") or edge.get("attraction_level") or 0.0)
            fear = float(edge.get("fear") or edge.get("fear_level") or 0.0)
            trust = float(edge.get("trust") or edge.get("trust_level") or 0.5)
            resentment = float(edge.get("resentment") or edge.get("resentment_level") or 0.0)
            emotional_hook = float(edge.get("emotional_hook_strength") or 0.0)

            # Blend edge into archetype template
            _blend = 0.4  # how much edge data overrides template
            dims["attraction_vs_fear_blend"] = round(
                dims["attraction_vs_fear_blend"] * (1 - _blend)
                + (attraction / max(attraction + fear, 0.01)) * _blend,
                3,
            )
            dims["emotional_danger"] = round(
                dims["emotional_danger"] * (1 - _blend) + fear * _blend,
                3,
            )
            dims["silence_comfort_index"] = round(
                dims["silence_comfort_index"] * (1 - _blend) + trust * _blend,
                3,
            )
            dims["mutual_reading_accuracy"] = round(
                min(1.0, dims["mutual_reading_accuracy"] + emotional_hook * 0.2),
                3,
            )

        # Reverse edge asymmetry: if target fears source more, adjust danger
        if reverse_edge:
            rev_fear = float(
                reverse_edge.get("fear") or reverse_edge.get("fear_level") or 0.0
            )
            dims["emotional_danger"] = round(
                max(dims["emotional_danger"], rev_fear), 3
            )

        # Tempo compatibility from baseline tempo defaults
        src_tempo = str(source_profile.get("tempo_default") or "moderate")
        tgt_tempo = str(target_profile.get("tempo_default") or "moderate")
        _TEMPO_RANK = {"slow": 0, "moderate": 1, "fast": 2}
        src_t = _TEMPO_RANK.get(src_tempo, 1)
        tgt_t = _TEMPO_RANK.get(tgt_tempo, 1)
        tempo_compat = 1.0 - abs(src_t - tgt_t) / 2.0  # 0, 0.5, or 1.0
        dims["tempo_compatibility"] = round(
            dims["tempo_compatibility"] * 0.5 + tempo_compat * 0.5, 3
        )

        # Overall chemistry score (weighted average of all dimensions)
        weights = {
            "tempo_compatibility": 0.10,
            "eye_contact_tolerance": 0.10,
            "interruption_rhythm": 0.10,
            "mutual_reading_accuracy": 0.15,
            "emotional_danger": 0.15,
            "attraction_vs_fear_blend": 0.20,
            "speech_completion_tendency": 0.10,
            "silence_comfort_index": 0.10,
        }
        chemistry_score = round(
            sum(dims.get(k, 0.5) * w for k, w in weights.items()), 3
        )

        chemistry_type = _chemistry_type(chemistry_score, dims)
        tension_type = "suppressed" if chemistry_type in {
            "forbidden_tension", "unfinished_business", "deep_resonance"
        } else "explicit"

        return {
            "source_character_id": source_id,
            "target_character_id": target_id,
            "tempo_compatibility": dims["tempo_compatibility"],
            "eye_contact_tolerance": dims["eye_contact_tolerance"],
            "interruption_rhythm": dims["interruption_rhythm"],
            "mutual_reading_accuracy": dims["mutual_reading_accuracy"],
            "emotional_danger": dims["emotional_danger"],
            "attraction_vs_fear_blend": dims["attraction_vs_fear_blend"],
            "speech_completion_tendency": dims["speech_completion_tendency"],
            "silence_comfort_index": dims["silence_comfort_index"],
            "chemistry_score": chemistry_score,
            "chemistry_type": chemistry_type,
            "tension_type": tension_type,
        }

    def compute_all_pairs(
        self,
        characters: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Compute chemistry for every pair of characters in the scene.

        Returns
        -------
        List of ChemistrySchema-compatible dicts.
        """
        edge_map: dict[tuple[str, str], dict[str, Any]] = {}
        for r in relationships:
            src = r.get("source_character_id", "")
            tgt = r.get("target_character_id", "")
            if src and tgt:
                edge_map[(src, tgt)] = r

        profile_map: dict[str, dict[str, Any]] = {
            (c.get("id") or c.get("avatar_id") or c["name"]): c
            for c in characters
        }

        results: list[dict[str, Any]] = []
        ids = list(profile_map.keys())
        for i, src in enumerate(ids):
            for tgt in ids[i + 1:]:
                edge = edge_map.get((src, tgt))
                rev = edge_map.get((tgt, src))
                result = self.compute(
                    source_id=src,
                    target_id=tgt,
                    source_profile=profile_map[src],
                    target_profile=profile_map[tgt],
                    edge=edge,
                    reverse_edge=rev,
                )
                results.append(result)
        return results
