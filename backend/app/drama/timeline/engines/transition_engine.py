from __future__ import annotations

from typing import Any, Dict, List


def compile_transitions(render_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a transition map between consecutive scenes."""
    transitions: List[Dict[str, Any]] = []

    for idx in range(len(render_scenes) - 1):
        current_scene = render_scenes[idx]
        next_scene = render_scenes[idx + 1]

        transition_type = select_transition(
            current_scene.get("render_purpose"),
            next_scene.get("render_purpose"),
        )

        transitions.append({
            "from_scene_id": current_scene.get("scene_id"),
            "to_scene_id": next_scene.get("scene_id"),
            "transition_type": transition_type,
            "duration_sec": 0.5,
        })

    return transitions


def select_transition(current_purpose: str | None, next_purpose: str | None) -> str:
    if next_purpose == "reveal":
        return "hard_cut"
    if next_purpose == "cliffhanger":
        return "slow_fade"
    if current_purpose == "hook":
        return "match_cut"
    return "cinematic_cut"
