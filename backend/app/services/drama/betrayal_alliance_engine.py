"""betrayal_alliance_engine — tracks alliance states and betrayal probability.

Section 12: Betrayal / Alliance Engine
----------------------------------------
Drama system is stronger when relationships don't stand still.

Alliance states (section 12.1):
    tactical, emotional, conditional, dependency_based, secret

Betrayal states (section 12.2):
    overt, passive, loyalty_failure, self_protection, ideological

Trigger conditions (section 12.3):
    reward_asymmetry, status_threat, fear_spike, exposure_risk_spike,
    third_party_pressure, scarcity, unresolved_wound_activation

Engine output (section 12.4):
    alliance_strengthen / crack / flip
    betrayal_probability
    reconciliation_probability
    future_tension_seed
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Alliance state classifier
# ---------------------------------------------------------------------------

def _classify_alliance(edge: dict[str, Any]) -> str | None:
    """Determine the alliance type from an edge's scores."""
    trust = float(edge.get("trust") or edge.get("trust_level") or 0.5)
    dependence = float(edge.get("dependence") or edge.get("dependence_level") or 0.0)
    attraction = float(edge.get("attraction") or edge.get("attraction_level") or 0.0)
    hidden_agenda = float(edge.get("hidden_agenda") or edge.get("hidden_agenda_score") or 0.0)
    perceived_loyalty = float(edge.get("perceived_loyalty") or 0.5)

    if trust < 0.3:
        return None  # not yet an alliance
    if hidden_agenda > 0.5:
        return "secret"
    if dependence > 0.6:
        return "dependency_based"
    if trust > 0.7 and attraction > 0.5:
        return "emotional"
    if trust > 0.6 and perceived_loyalty > 0.6:
        return "tactical"
    return "conditional"


# ---------------------------------------------------------------------------
# Betrayal trigger evaluator
# ---------------------------------------------------------------------------

_TRIGGER_THRESHOLDS = {
    "reward_asymmetry": ("moral_superiority", 0.6),      # one side benefits more
    "status_threat": ("perceived_power", 0.7),           # target feels threatened
    "fear_spike": ("fear", 0.65),
    "exposure_risk_spike": ("shame_exposure_risk", 0.6),
    "unresolved_wound_activation": ("resentment", 0.65),
}


def _evaluate_triggers(edge: dict[str, Any]) -> list[str]:
    """Return list of active betrayal trigger names."""
    active: list[str] = []
    for trigger, (field, threshold) in _TRIGGER_THRESHOLDS.items():
        val = float(edge.get(field) or edge.get(f"{field}_level") or 0.0)
        if val >= threshold:
            active.append(trigger)
    return active


# ---------------------------------------------------------------------------
# Betrayal probability formula
# ---------------------------------------------------------------------------

def _betrayal_probability(edge: dict[str, Any], active_triggers: list[str]) -> float:
    """Compute betrayal probability (0–1) from edge scores + triggers."""
    trust = float(edge.get("trust") or edge.get("trust_level") or 0.5)
    resentment = float(edge.get("resentment") or edge.get("resentment_level") or 0.0)
    fear = float(edge.get("fear") or edge.get("fear_level") or 0.0)
    hidden_agenda = float(edge.get("hidden_agenda") or edge.get("hidden_agenda_score") or 0.0)
    perceived_loyalty = float(edge.get("perceived_loyalty") or 0.5)

    base = (
        resentment * 0.30
        + fear * 0.20
        + hidden_agenda * 0.25
        + (1.0 - trust) * 0.15
        + (1.0 - perceived_loyalty) * 0.10
    )
    trigger_boost = len(active_triggers) * 0.05
    return round(min(1.0, base + trigger_boost), 3)


# ---------------------------------------------------------------------------
# Reconciliation probability formula
# ---------------------------------------------------------------------------

def _reconciliation_probability(edge: dict[str, Any]) -> float:
    trust = float(edge.get("trust") or edge.get("trust_level") or 0.5)
    attraction = float(edge.get("attraction") or edge.get("attraction_level") or 0.0)
    emotional_hook = float(edge.get("emotional_hook_strength") or 0.0)
    resentment = float(edge.get("resentment") or edge.get("resentment_level") or 0.0)

    raw = (trust * 0.4 + attraction * 0.3 + emotional_hook * 0.3) * (1.0 - resentment * 0.5)
    return round(min(1.0, raw), 3)


# ---------------------------------------------------------------------------
# Betrayal type classifier
# ---------------------------------------------------------------------------

def _classify_betrayal_type(edge: dict[str, Any], triggers: list[str]) -> str | None:
    """Return the most likely betrayal type or None if probability is low."""
    prob = _betrayal_probability(edge, triggers)
    if prob < 0.25:
        return None

    fear = float(edge.get("fear") or edge.get("fear_level") or 0.0)
    hidden_agenda = float(edge.get("hidden_agenda") or edge.get("hidden_agenda_score") or 0.0)
    resentment = float(edge.get("resentment") or edge.get("resentment_level") or 0.0)
    moral_sup = float(edge.get("moral_superiority") or 0.0)

    if "exposure_risk_spike" in triggers or "fear_spike" in triggers:
        return "self_protection"
    if hidden_agenda > 0.6:
        return "overt"
    if moral_sup > 0.5 and "reward_asymmetry" in triggers:
        return "ideological"
    if resentment > 0.5:
        return "passive"
    return "loyalty_failure"


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class BetrayalAllianceEngine:
    """Evaluates alliance health and betrayal risk between two characters."""

    def evaluate(
        self,
        source_id: str,
        target_id: str,
        edge: dict[str, Any],
        reverse_edge: dict[str, Any] | None = None,
        scene_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return BetrayalAllianceSchema-compatible dict.

        Parameters
        ----------
        source_id, target_id:
            Character identifiers (directed: source → target).
        edge:
            RelationshipEdge dict (source → target).
        reverse_edge:
            Optional reverse edge (target → source) for asymmetry detection.
        scene_context:
            Optional current scene beat / drama state.

        Returns
        -------
        dict with keys matching ``BetrayalAllianceSchema``.
        """
        alliance_state = _classify_alliance(edge)
        active_triggers = _evaluate_triggers(edge)
        betrayal_prob = _betrayal_probability(edge, active_triggers)
        reconciliation_prob = _reconciliation_probability(edge)
        betrayal_type = _classify_betrayal_type(edge, active_triggers)

        # Alliance strength: trust × loyalty × (1 − hidden_agenda)
        trust = float(edge.get("trust") or edge.get("trust_level") or 0.5)
        loyalty = float(edge.get("perceived_loyalty") or 0.5)
        ha = float(edge.get("hidden_agenda") or edge.get("hidden_agenda_score") or 0.0)
        alliance_strength = round(trust * 0.5 + loyalty * 0.3 + (1.0 - ha) * 0.2, 3)

        # Future tension seed
        future_seeds = {
            "overt": "aftermath_confrontation",
            "passive": "slow_erosion_of_trust",
            "loyalty_failure": "guilt_driven_distance",
            "self_protection": "resentment_accumulation",
            "ideological": "permanent_rupture_risk",
        }
        future_tension_seed: str | None = future_seeds.get(betrayal_type or "")

        # Asymmetry detection (optional)
        trigger_reason: str | None = None
        if active_triggers:
            trigger_reason = ", ".join(active_triggers)
        if reverse_edge:
            rev_trust = float(reverse_edge.get("trust") or reverse_edge.get("trust_level") or 0.5)
            if abs(trust - rev_trust) > 0.3:
                if trigger_reason:
                    trigger_reason += "; trust_asymmetry"
                else:
                    trigger_reason = "trust_asymmetry"

        return {
            "source_character_id": source_id,
            "target_character_id": target_id,
            "alliance_state": alliance_state,
            "betrayal_state": betrayal_type,
            "betrayal_probability": betrayal_prob,
            "reconciliation_probability": reconciliation_prob,
            "alliance_strength": alliance_strength,
            "future_tension_seed": future_tension_seed,
            "trigger_reason": trigger_reason,
        }

    def evaluate_all_pairs(
        self,
        characters: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        scene_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate all character pairs in the scene.

        Returns
        -------
        List of BetrayalAllianceSchema-compatible dicts.
        """
        edge_map: dict[tuple[str, str], dict[str, Any]] = {}
        for r in relationships:
            src = r.get("source_character_id", "")
            tgt = r.get("target_character_id", "")
            if src and tgt:
                edge_map[(src, tgt)] = r

        results: list[dict[str, Any]] = []
        ids = [c.get("id") or c.get("avatar_id") or c["name"] for c in characters]
        for i, src in enumerate(ids):
            for tgt in ids[i + 1:]:
                edge = edge_map.get((src, tgt), {
                    "source_character_id": src,
                    "target_character_id": tgt,
                })
                rev = edge_map.get((tgt, src))
                result = self.evaluate(
                    src, tgt, edge, rev, scene_context
                )
                results.append(result)
        return results
