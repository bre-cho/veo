#!/usr/bin/env python3
"""Seed a verified AudioRenderOutput row and matching artifact files for CI.

Creates real (minimal) files under the artifacts tree and inserts a
``status='succeeded'`` row in ``audio_render_outputs`` so that
``verify_audio_artifacts.py`` has something concrete to check.

The row is idempotent: running this script twice leaves exactly one row.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


_CI_OUTPUT_ID = "ci-verify"


def _get_paths() -> tuple[str, str, str, str]:
    """Resolve artifact paths from settings (or env vars as fallback)."""
    import os
    audio_dir = os.environ.get("AUDIO_OUTPUT_DIR", "/app/artifacts/audio")
    video_dir = os.environ.get("VIDEO_OUTPUT_DIR", "/app/artifacts/video")
    audio_artifact_path = f"{audio_dir}/mix/{_CI_OUTPUT_ID}/mixed_audio.mp3"
    video_artifact_path = f"{video_dir}/mux/{_CI_OUTPUT_ID}/final_muxed_video.mp4"
    # Derive public URLs relative to the artifacts mount root (parent of audio_dir)
    audio_url = f"/artifacts/audio/mix/{_CI_OUTPUT_ID}/mixed_audio.mp3"
    video_url = f"/artifacts/video/mux/{_CI_OUTPUT_ID}/final_muxed_video.mp4"
    return audio_artifact_path, video_artifact_path, audio_url, video_url


def _create_artifact_files() -> None:
    """Write minimal placeholder files so FastAPI's StaticFiles can serve them."""
    audio_artifact_path, video_artifact_path, _, _ = _get_paths()
    for path_str in (audio_artifact_path, video_artifact_path):
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b"CI-placeholder")
            print(f"[seed] Created {path}")
        else:
            print(f"[seed] Already exists: {path}")


def _seed_db_row(db_url: str | None) -> None:
    """Insert (or skip) the CI verify row in audio_render_outputs."""
    _, _, audio_url, video_url = _get_paths()
    effective_url = db_url or os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/render_factory",
    )

    from sqlalchemy import create_engine, text

    engine = create_engine(effective_url, pool_pre_ping=True)
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM audio_render_outputs WHERE id = :id"),
            {"id": _CI_OUTPUT_ID},
        ).fetchone()
        if existing:
            print(f"[seed] Row already exists: id={_CI_OUTPUT_ID!r}")
            return

        conn.execute(
            text(
                "INSERT INTO audio_render_outputs "
                "(id, status, mixed_audio_url, final_muxed_video_url, created_at, updated_at) "
                "VALUES (:id, 'succeeded', :audio_url, :video_url, NOW(), NOW())"
            ),
            {
                "id": _CI_OUTPUT_ID,
                "audio_url": audio_url,
                "video_url": video_url,
            },
        )
        print(f"[seed] Inserted row id={_CI_OUTPUT_ID!r} with status='succeeded'")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Seed CI audio artifact verify row")
    parser.add_argument("--db-url", default=None, help="SQLAlchemy database URL")
    args = parser.parse_args()

    try:
        _create_artifact_files()
    except OSError as exc:
        print(f"[ERROR] Could not create artifact files: {exc}", file=sys.stderr)
        return 1

    try:
        _seed_db_row(args.db_url)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Could not seed database row: {exc}", file=sys.stderr)
        return 1

    print("[seed] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
