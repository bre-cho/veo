"""multi_scene_engine — builds the scene sequence for multi-scene scripts.

Given a list of scene contexts and a target episode duration, this engine
assigns a narrative purpose to each scene and computes per-scene durations.
"""
from __future__ import annotations

from typing import Any, Dict, List


def build_scene_sequence(
    scene_contexts: List[Dict[str, Any]],
    target_duration_min: int = 15,
) -> List[Dict[str, Any]]:
    """Distribute scenes across the episode and assign narrative purposes.

    Purpose assignment rules:
    - Scene 0               → ``hook``
    - Last scene            → ``cliffhanger``
    - Every 3rd scene (0-indexed, excluding scene 0) → ``reveal``
    - All other scenes      → ``escalation``

    Args:
        scene_contexts: Ordered list of scene context dicts.  Each dict may
            include ``scene_id``, ``hidden_intent``, ``hidden_conflict``, etc.
        target_duration_min: Target total episode duration in minutes.

    Returns:
        Ordered list of scene dicts with ``scene_id``, ``purpose``,
        ``duration_sec``, and ``context`` keys.
    """
    total_sec = target_duration_min * 60
    scene_count = max(len(scene_contexts), 1)
    avg_scene_sec = total_sec // scene_count

    sequence: List[Dict[str, Any]] = []

    for idx, scene in enumerate(scene_contexts):
        if idx == 0:
            purpose = "hook"
        elif idx == scene_count - 1:
            purpose = "cliffhanger"
        elif idx % 3 == 0:
            purpose = "reveal"
        else:
            purpose = "escalation"

        sequence.append(
            {
                "scene_id": scene.get("scene_id", f"scene_{idx}"),
                "purpose": purpose,
                "duration_sec": avg_scene_sec,
                "context": scene,
            }
        )

    return sequence
