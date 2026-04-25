from __future__ import annotations

import hashlib
from pathlib import Path


def compute_video_hash(video_path: str) -> str:
    """Return a short stable hash that changes whenever a video file is replaced.

    The hash is derived from the **resolved absolute path**, **file size**, and
    **modification timestamp** (``st_mtime``).  It is therefore:

    - Fast — no need to read file contents.
    - Stable — the same file on the same system always yields the same hash.
    - Invalidating — any write to the file (size or mtime change) produces a
      different hash, automatically expiring cached detection results.

    Args:
        video_path: Path to the video file.

    Returns:
        A 16-character hex string (first 64 bits of SHA-256).

    Raises:
        FileNotFoundError: If *video_path* does not exist.
    """
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(video_path)

    stat = path.stat()
    raw = f"{path.resolve()}:{stat.st_size}:{stat.st_mtime}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
