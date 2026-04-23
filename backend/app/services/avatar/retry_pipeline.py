"""retry_pipeline — utilities for requeueing jobs with a new avatar context."""
from __future__ import annotations

from typing import Any


class RetryPipeline:
    """Patches a render/publish context dict to use a new avatar, enabling
    downstream systems to retry with the healed avatar selection.
    """

    def retry_with_new_avatar(
        self,
        context: dict[str, Any],
        new_avatar_id: str,
    ) -> dict[str, Any]:
        """Return a copy of *context* with ``avatar_id`` replaced by
        *new_avatar_id* and ``force_avatar`` set to ``True``.

        The original context is not mutated.
        """
        updated = {**context}
        updated["avatar_id"] = new_avatar_id
        updated["force_avatar"] = True
        # Clear previous selection debug so downstream doesn't re-use stale data
        updated.pop("avatar_selection", None)
        updated.pop("avatar_selection_debug", None)
        return updated
