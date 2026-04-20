from __future__ import annotations

import math
from typing import Any

from app.services.execution_bridge_service import ExecutionBridgeService
from app.services.render_provider_registry import get_provider_capabilities

_execution_bridge = ExecutionBridgeService()
MIN_PACING_WEIGHT = 0.6
MAX_PACING_WEIGHT = 1.8


def estimate_duration_from_text(text: str) -> float:
    words = len((text or "").split())
    duration = max(3.0, round(words / 2.6, 1))
    return duration


def split_text_into_chunks(text: str, chunks: int) -> list[str]:
    words = text.split()
    if not words or chunks <= 1:
        return [text.strip()] if text.strip() else []

    chunk_size = math.ceil(len(words) / chunks)
    out: list[str] = []

    for i in range(0, len(words), chunk_size):
        out.append(" ".join(words[i:i + chunk_size]).strip())

    return [x for x in out if x]


def plan_provider_scenes(
    scenes: list[dict[str, Any]],
    provider: str,
    execution_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    caps = get_provider_capabilities(provider)
    planned: list[dict[str, Any]] = []

    for scene in scenes:
        text = (scene.get("script_text") or "").strip()
        if not text:
            continue
        bridged_scene = _execution_bridge.apply_to_project_scene(scene, execution_context or {})
        title = (bridged_scene.get("title") or "Scene").strip()

        pacing_weight = float((bridged_scene.get("metadata") or {}).get("pacing_weight") or 1.0)
        estimated = estimate_duration_from_text(text) * max(MIN_PACING_WEIGHT, min(MAX_PACING_WEIGHT, pacing_weight))
        scene_goal = (bridged_scene.get("metadata") or {}).get("scene_goal")
        shot_hint = bridged_scene.get("shot_hint") or (bridged_scene.get("metadata") or {}).get("shot_hint")
        prompt_suffix = ""
        if shot_hint:
            prompt_suffix += f" Shot hint: {shot_hint}."
        if scene_goal:
            prompt_suffix += f" Scene goal: {scene_goal}."
        base_prompt = (bridged_scene.get("prompt_text") or bridged_scene.get("visual_prompt") or text).strip()

        if estimated <= caps.max_scene_duration_sec:
            planned.append({
                **bridged_scene,
                "provider": provider,
                "provider_mode": caps.recommended_mode,
                "prompt_text": f"{base_prompt}{prompt_suffix}".strip(),
                "provider_target_duration_sec": min(
                    max(estimated, 3.0),
                    caps.max_scene_duration_sec,
                ),
            })
            continue

        chunk_count = math.ceil(estimated / caps.max_scene_duration_sec)
        chunks = split_text_into_chunks(text, chunk_count)

        for idx, chunk in enumerate(chunks, start=1):
            chunk_scene = {
                "scene_index": len(planned) + 1,
                "title": f"{title} — Part {idx}",
                "script_text": chunk,
                "target_duration_sec": estimate_duration_from_text(chunk),
                "provider": provider,
                "provider_mode": caps.recommended_mode,
                "prompt_text": f"{chunk}{prompt_suffix}".strip(),
                "provider_target_duration_sec": min(
                    max(estimate_duration_from_text(chunk), 3.0),
                    caps.max_scene_duration_sec,
                ),
                "source_scene_index": bridged_scene.get("scene_index"),
            }
            planned.append(_execution_bridge.apply_to_project_scene(chunk_scene, execution_context or {}))

    return planned
