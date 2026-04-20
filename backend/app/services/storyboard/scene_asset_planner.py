"""SceneAssetPlanner — plan required assets for each storyboard scene.

Phase 4.2: Cross-references storyboard visual_types against avatar render
inventory to identify missing assets.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.storyboard import StoryboardResponse

logger = logging.getLogger(__name__)


class SceneAssetPlanner:
    """Plan assets required for each scene in a storyboard.

    ``plan_assets()`` queries the avatar render inventory to check whether
    each scene's ``visual_type`` has an existing reference frame.  Returns
    a per-scene asset plan and a list of ``missing_assets``.
    """

    def plan_assets(
        self,
        storyboard: "StoryboardResponse",
        avatar_id: str,
        db: Any | None = None,
    ) -> dict[str, Any]:
        """Return asset plan for all scenes in the storyboard.

        Args:
            storyboard: The generated storyboard response.
            avatar_id: The avatar for which to check inventory.
            db: Optional SQLAlchemy session for DB queries.

        Returns:
            Dict with:
            - ``scene_assets``: {scene_index → {required_assets, available_in_inventory,
              suggested_render_params}}
            - ``missing_assets``: list of (scene_index, visual_type) that need rendering
        """
        scene_assets: dict[str, Any] = {}
        missing_assets: list[dict[str, Any]] = []

        # Build inventory of visual types for this avatar
        available_visual_types: set[str] = self._get_available_visual_types(avatar_id, db)

        for scene in storyboard.scenes:
            visual_type = scene.visual_type or "unknown"
            required_assets = [visual_type]
            available = visual_type in available_visual_types

            suggested_params: dict[str, Any] = {
                "scene_goal": scene.scene_goal,
                "visual_type": visual_type,
                "pacing_weight": scene.pacing_weight,
            }

            scene_assets[str(scene.scene_index)] = {
                "required_assets": required_assets,
                "available_in_inventory": available,
                "suggested_render_params": suggested_params,
            }

            if not available:
                missing_assets.append(
                    {
                        "scene_index": scene.scene_index,
                        "visual_type": visual_type,
                        "scene_goal": scene.scene_goal,
                    }
                )

        return {
            "avatar_id": avatar_id,
            "scene_assets": scene_assets,
            "missing_assets": missing_assets,
            "inventory_complete": len(missing_assets) == 0,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_available_visual_types(
        self, avatar_id: str, db: Any | None
    ) -> set[str]:
        """Query AvatarReferenceFrame inventory for available visual types."""
        if db is None:
            return set()
        try:
            from app.models.autovis import AvatarReferenceFrame

            rows = (
                db.query(AvatarReferenceFrame.frame_type)
                .filter(AvatarReferenceFrame.avatar_id == avatar_id)
                .all()
            )
            return {str(row.frame_type) for row in rows if row.frame_type}
        except Exception as exc:
            logger.debug(
                "SceneAssetPlanner: could not query inventory for avatar=%s: %s",
                avatar_id, exc,
            )
            return set()
