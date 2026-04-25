from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.core.runtime_paths import render_paths
from app.render.reassembly._sort_utils import scene_sort_key


class ConcatFinalizer:
    """Fast-concats pre-encoded scene chunks into the episode final MP4.

    Uses FFmpeg's ``concat`` demuxer with ``-c copy`` so no re-encoding is
    needed — this makes the operation proportionally cheap regardless of
    episode length.
    """

    def concat_chunks(
        self,
        project_id: str,
        episode_id: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Concatenate *chunks* and write the final MP4.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode identifier.
            chunks: Ordered list of chunk dicts, each with a ``chunk_path``
                key pointing to an encoded MP4.

        Returns:
            A dict with ``status`` and ``output_path``.

        Raises:
            RuntimeError: If FFmpeg exits with a non-zero return code.
        """
        out_dir = Path(render_paths.final_dir) / project_id
        out_dir.mkdir(parents=True, exist_ok=True)

        # Sort by order_index so numeric scene ordering (1, 2, 10) is
        # preserved.  Chunks without an order_index fall back to scene_id.
        ordered_chunks = sorted(chunks, key=scene_sort_key)

        concat_file = Path(render_paths.smart_concat_scratch_path(project_id, episode_id))
        with open(concat_file, "w", encoding="utf-8") as fh:
            for chunk in ordered_chunks:
                fh.write(f"file '{chunk['chunk_path']}'\n")

        output_path = out_dir / f"{episode_id}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Smart concat failed for episode '{episode_id}'. "
                f"FFmpeg stderr: {result.stderr}"
            )

        return {"status": "succeeded", "output_path": str(output_path)}
