"""Shared sorting utilities for scene manifests and chunk entries.

All ordering in the render pipeline is numeric by ``order_index`` (preferred)
or ``scene_index`` (fallback) so that scene_1 < scene_2 < scene_10 regardless
of lexicographic ordering.  Entries without either field get a large sentinel
value (999 999) and are further sub-sorted by ``scene_id``.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

_SENTINEL = 999_999


def scene_sort_key(item: Dict[str, Any]) -> Tuple[int, str]:
    """Return a ``(order_index, scene_id)`` sort key for a scene manifest or chunk.

    ``order_index`` is resolved as ``order_index`` → ``scene_index`` → 999 999,
    using the first non-``None`` integer found.
    """
    numeric = next(
        (int(v) for v in (item.get("order_index"), item.get("scene_index")) if v is not None),
        _SENTINEL,
    )
    return numeric, item.get("scene_id", "")
