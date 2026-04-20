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
            - ``render_inventory``: {visual_type: [render_url, ...]} from completed jobs
        """
        scene_assets: dict[str, Any] = {}
        missing_assets: list[dict[str, Any]] = []

        # Build inventory of visual types for this avatar (now also includes RenderJob data)
        available_visual_types, render_inventory = self._get_available_visual_types(avatar_id, db)

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
                "render_urls": render_inventory.get(visual_type, []),
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
            "render_inventory": render_inventory,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_available_visual_types(
        self, avatar_id: str, db: Any | None
    ) -> tuple[set[str], dict[str, list[str]]]:
        """Query AvatarReferenceFrame inventory AND completed RenderJobs for available visual types.

        Returns a tuple of:
        - ``available`` set[str]: visual types available in inventory
        - ``render_inventory`` dict[str, list[str]]: {visual_type: [render_url, ...]}
        """
        available: set[str] = set()
        render_inventory: dict[str, list[str]] = {}
        if db is None:
            return available, render_inventory
        try:
            from app.models.autovis import AvatarReferenceFrame

            rows = (
                db.query(AvatarReferenceFrame.frame_type)
                .filter(AvatarReferenceFrame.avatar_id == avatar_id)
                .all()
            )
            for row in rows:
                if row.frame_type:
                    vt = str(row.frame_type)
                    available.add(vt)
                    render_inventory.setdefault(vt, [])
        except Exception as exc:
            logger.debug(
                "SceneAssetPlanner: could not query AvatarReferenceFrame for avatar=%s: %s",
                avatar_id, exc,
            )

        # Also cross-reference completed RenderJobs for richer inventory
        try:
            from app.models.render_job import RenderJob  # type: ignore[import]
            from datetime import datetime, timedelta, timezone

            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            rows_rj = (
                db.query(RenderJob)
                .filter(
                    RenderJob.status == "completed",
                    RenderJob.updated_at >= cutoff,
                )
                .order_by(RenderJob.updated_at.desc())
                .limit(200)
                .all()
            )
            for row_rj in rows_rj:
                payload: dict = row_rj.payload or {}
                if str(payload.get("avatar_id", "")) != avatar_id:
                    continue
                output_url = str(
                    payload.get("output_url") or payload.get("render_url") or ""
                ).strip()
                visual_type = str(payload.get("visual_type") or "").strip()
                if output_url and visual_type:
                    available.add(visual_type)
                    render_inventory.setdefault(visual_type, [])
                    if output_url not in render_inventory[visual_type]:
                        render_inventory[visual_type].append(output_url)
        except Exception as exc:
            logger.debug(
                "SceneAssetPlanner: could not query RenderJob for avatar=%s: %s",
                avatar_id, exc,
            )

        return available, render_inventory
