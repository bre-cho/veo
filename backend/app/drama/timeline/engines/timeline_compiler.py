from __future__ import annotations

from typing import Any, Dict, List

from app.drama.timeline.engines.audio_timing_engine import compile_audio_timing
from app.drama.timeline.engines.subtitle_timing_engine import compile_subtitle_timing
from app.drama.timeline.engines.transition_engine import compile_transitions
from app.drama.timeline.engines.assembly_plan_engine import build_assembly_plan


class SceneTimelineCompiler:
    """Compiles a list of render scenes into a full timeline with timing data."""

    def compile(
        self,
        project_id: str,
        episode_id: str,
        render_scenes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        scenes = self._compile_scene_timing(render_scenes)
        audio_tracks = compile_audio_timing(render_scenes)
        subtitle_tracks = compile_subtitle_timing(render_scenes)
        transition_map = compile_transitions(render_scenes)

        total_duration_sec = sum(
            scene.get("duration_sec", 6) for scene in render_scenes
        )

        assembly_plan = build_assembly_plan(
            project_id=project_id,
            episode_id=episode_id,
            scenes=scenes,
            audio_tracks=audio_tracks,
            subtitle_tracks=subtitle_tracks,
            transition_map=transition_map,
        )

        return {
            "project_id": project_id,
            "episode_id": episode_id,
            "total_duration_sec": total_duration_sec,
            "scenes": scenes,
            "subtitle_tracks": subtitle_tracks,
            "audio_tracks": audio_tracks,
            "transition_map": transition_map,
            "assembly_plan": assembly_plan,
        }

    def _compile_scene_timing(self, render_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scenes: List[Dict[str, Any]] = []
        cursor = 0

        for index, scene in enumerate(render_scenes):
            duration = scene.get("duration_sec", 6)

            scenes.append({
                "scene_index": index,
                "scene_id": scene.get("scene_id"),
                "start_sec": cursor,
                "end_sec": cursor + duration,
                "duration_sec": duration,
                "render_purpose": scene.get("render_purpose"),
                "emotion": scene.get("drama_metadata", {}).get("emotion"),
                "intent": scene.get("drama_metadata", {}).get("intent"),
                "subtext": scene.get("drama_metadata", {}).get("subtext"),
            })

            cursor += duration

        return scenes
