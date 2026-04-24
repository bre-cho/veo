from __future__ import annotations

from typing import Any, Dict, List


def normalize_scene_payload(scene: Dict[str, Any]) -> Dict[str, Any]:
    beats = scene.get("beats") or []
    return {
        "scene_id": scene.get("scene_id"),
        "scene_goal": scene.get("scene_goal") or scene.get("goal"),
        "characters": scene.get("characters") or [],
        "beats": beats if isinstance(beats, list) else [],
        "time_pressure": scene.get("time_pressure", 0.0),
        "social_consequence": scene.get("social_consequence", 0.0),
    }


def normalize_episode_scenes(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_scene_payload(scene) for scene in scenes]
