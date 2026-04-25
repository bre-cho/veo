"""binge_chain_engine — injects cross-episode memory callbacks into segments.

When open loops from previous scenes/episodes are provided, this engine
inserts a callback segment at the right position to create binge-inducing
continuity hooks.
"""
from __future__ import annotations

from typing import Any, Dict, List

_DEFAULT_CALLBACK_LINE = (
    "But this was not the first time something like this had happened."
)

# Insert position (0-indexed): inject after the first two segments so the
# hook is established before the callback fires.
_CALLBACK_INSERT_POSITION = 2


def inject_binge_callbacks(
    segments: List[Dict[str, Any]],
    open_loops: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Insert a binge-callback segment into ``segments`` when open loops exist.

    The callback is taken from ``open_loops[0]["callback_line"]`` if present,
    otherwise a default line is used.  The segment is inserted at position 2
    (after hook + first escalation) so it doesn't disrupt the opening hook.

    Args:
        segments: Assembled narration segments (mutated in-place via insert).
        open_loops: List of open-loop dicts, each optionally containing
            ``callback_line`` and ``loop_id``.

    Returns:
        The updated segment list (same list object, with callback injected).
    """
    if not open_loops:
        return segments

    loop = open_loops[0]
    callback_line: str = loop.get("callback_line", _DEFAULT_CALLBACK_LINE)
    loop_id: str = loop.get("loop_id", "open_loop_0")

    insert_at = min(_CALLBACK_INSERT_POSITION, len(segments))

    segments.insert(
        insert_at,
        {
            "scene_id": f"binge_callback_{loop_id}",
            "purpose": "callback",
            "text": callback_line,
            "subtext": "previous unresolved loop returns",
            "intent": "reconnect_memory",
            "emotion": "curiosity",
            "duration_sec": 8,
        },
    )

    return segments
