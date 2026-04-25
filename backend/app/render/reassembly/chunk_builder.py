from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.runtime_paths import render_paths


class ChunkBuilder:
    """Encodes a single scene into a self-contained MP4 chunk.

    The chunk contains the scene video, mixed audio, and (optionally) burnt-in
    ASS subtitles.  It is stored at
    ``{chunks_dir}/{project_id}/{episode_id}/{scene_id}.mp4``.
    """

    def build_scene_chunk(
        self,
        project_id: str,
        episode_id: str,
        scene_manifest: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Encode *scene_manifest* assets into one MP4 chunk.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode identifier.
            scene_manifest: Scene manifest dict — must contain at minimum
                ``scene_id``, ``video_path``, and ``audio_path``.

        Returns:
            A dict with ``scene_id``, ``chunk_path``, and ``duration_sec``.

        Raises:
            RuntimeError: If FFmpeg exits with a non-zero return code.
        """
        scene_id: str = scene_manifest["scene_id"]
        video_path: str = scene_manifest["video_path"]
        audio_path: str = scene_manifest["audio_path"]
        subtitle_path: Optional[str] = scene_manifest.get("subtitle_path")

        out_dir = Path(render_paths.chunks_dir) / project_id / episode_id
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{scene_id}.mp4"

        cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path]

        vf_filters = []
        if subtitle_path:
            vf_filters.append(f"ass={subtitle_path}")

        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])

        cmd.extend([
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Chunk build failed for scene '{scene_id}'. "
                f"FFmpeg stderr: {result.stderr}"
            )

        return {
            "scene_id": scene_id,
            "order_index": scene_manifest.get("order_index", scene_manifest.get("scene_index")),
            "chunk_path": str(output_path),
            "duration_sec": scene_manifest.get("duration_sec"),
        }
