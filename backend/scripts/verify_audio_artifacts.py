#!/usr/bin/env python3
"""E2E script: verify that audio artifact URLs return HTTP 200.

Usage:
    python backend/scripts/verify_audio_artifacts.py [--base-url http://localhost:8000] [--db-url postgresql+psycopg://...]

The script queries the database for recently completed AudioRenderOutput rows,
collects all non-null artifact URLs (mixed_audio_url, final_muxed_video_url,
voice_track_url, music_track_url), resolves relative URLs against --base-url,
and asserts each one returns HTTP 200.

Exit code 0 means all checks passed; non-zero means at least one check failed.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify audio artifact URLs return HTTP 200")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="SQLAlchemy database URL (overrides DATABASE_URL env var)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of most-recent succeeded outputs to check (default: 20)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP request timeout in seconds (default: 10)",
    )
    return parser.parse_args()


def _resolve_url(base: str, artifact_url: str) -> str:
    """Resolve an artifact URL against the API base URL if it is relative."""
    if artifact_url.startswith(("http://", "https://")):
        return artifact_url
    return base.rstrip("/") + "/" + artifact_url.lstrip("/")


def _check_url(url: str, timeout: int) -> tuple[bool, int | str]:
    """HEAD request; falls back to GET on 405.  Returns (ok, status_or_error)."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return True, resp.status
        except urllib.error.HTTPError as exc:
            if exc.code == 405 and method == "HEAD":
                continue
            return False, exc.code
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
    return False, "all methods failed"


def _load_outputs(db_url: str | None, limit: int) -> list[dict[str, Any]]:
    """Load recent succeeded AudioRenderOutput rows via SQLAlchemy."""
    import os

    effective_url = db_url or os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/render_factory",
    )

    from sqlalchemy import create_engine, text

    engine = create_engine(effective_url, pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, mixed_audio_url, final_muxed_video_url, "
                "voice_track_url, music_track_url "
                "FROM audio_render_outputs "
                "WHERE status = 'succeeded' "
                "ORDER BY updated_at DESC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


def main() -> int:
    args = _parse_args()

    try:
        outputs = _load_outputs(args.db_url, args.limit)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Could not load outputs from database: {exc}", file=sys.stderr)
        return 2

    if not outputs:
        print("[ERROR] No succeeded AudioRenderOutput rows found — verification cannot prove artifact availability.")
        return 1

    url_fields = ("mixed_audio_url", "final_muxed_video_url", "voice_track_url", "music_track_url")
    checks: list[tuple[str, str, str]] = []  # (output_id, field, full_url)
    for row in outputs:
        for field in url_fields:
            raw = row.get(field)
            if raw:
                checks.append((str(row["id"]), field, _resolve_url(args.base_url, raw)))

    if not checks:
        print("[ERROR] Succeeded rows found, but no artifact URLs to verify.")
        return 1

    failures: list[tuple[str, str, str, int | str]] = []
    for output_id, field, url in checks:
        ok, status = _check_url(url, args.timeout)
        label = f"[{'OK' if ok else 'FAIL'}] {output_id} / {field}"
        print(f"{label}  {url}  → {status}")
        if not ok:
            failures.append((output_id, field, url, status))

    print()
    if failures:
        print(f"FAILED: {len(failures)} / {len(checks)} checks")
        for output_id, field, url, status in failures:
            print(f"  • {output_id} / {field}: {url} → {status}")
        return 1

    print(f"All {len(checks)} artifact URL checks returned HTTP 200.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
