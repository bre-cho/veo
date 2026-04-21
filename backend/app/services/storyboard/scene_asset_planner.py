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
        asset_inventory: dict[str, Any] | None = None,
        render_history: list[dict[str, Any]] | None = None,
        winning_shot_config: dict[str, Any] | None = None,
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
        if asset_inventory:
            for asset_type, payload in (asset_inventory or {}).items():
                urls = list((payload or {}).get("render_urls") or [])
                if urls:
                    render_inventory.setdefault(str(asset_type), [])
                    for url in urls:
                        if url not in render_inventory[str(asset_type)]:
                            render_inventory[str(asset_type)].append(url)
                    available_visual_types.add(str(asset_type))

        for scene in storyboard.scenes:
            visual_type = scene.visual_type or "unknown"
            grouped = self._group_assets_for_scene(
                scene_goal=scene.scene_goal,
                visual_type=visual_type,
                winning_shot_config=winning_shot_config,
            )
            required_assets = grouped["required_assets"]
            optional_assets = grouped["optional_assets"]
            available = all(asset in available_visual_types for asset in required_assets)
            ranked_assets = self._rank_asset_candidates(
                scene_goal=scene.scene_goal or "",
                visual_type=visual_type,
                candidates=required_assets + optional_assets,
                winning_shot_config=winning_shot_config,
                render_history=render_history,
                render_inventory=render_inventory,
            )
            reuse_assets = [a for a in ranked_assets if a in render_inventory and render_inventory.get(a)]
            local_missing = [a for a in required_assets if a not in available_visual_types]

            suggested_params: dict[str, Any] = {
                "scene_goal": scene.scene_goal,
                "visual_type": visual_type,
                "pacing_weight": scene.pacing_weight,
            }

            scene_assets[str(scene.scene_index)] = {
                "required_assets": required_assets,
                "optional_assets": optional_assets,
                "reuse_assets": reuse_assets,
                "missing_assets": local_missing,
                "available_in_inventory": available,
                "render_urls": render_inventory.get(visual_type, []),
                "suggested_render_params": suggested_params,
            }

            for missing in local_missing:
                missing_assets.append(
                    {
                        "scene_index": scene.scene_index,
                        "visual_type": visual_type,
                        "scene_goal": scene.scene_goal,
                        "asset_type": missing,
                    }
                )

        return {
            "avatar_id": avatar_id,
            "scene_assets": scene_assets,
            "missing_assets": missing_assets,
            "inventory_complete": len(missing_assets) == 0,
            "render_inventory": render_inventory,
            "asset_inventory": self._build_asset_inventory(scene_assets, render_inventory),
        }

    @staticmethod
    def _group_assets_for_scene(
        *,
        scene_goal: str | None,
        visual_type: str,
        winning_shot_config: dict[str, Any] | None = None,
    ) -> dict[str, list[str]]:
        required = [visual_type]
        optional: list[str] = []
        goal = (scene_goal or "").lower()
        if goal in ("cta", "reveal"):
            optional.append("product_closeup")
        if goal in ("hook", "intro"):
            optional.append("attention_motion_overlay")
        shot_type = str((winning_shot_config or {}).get("shot_type") or "")
        if shot_type:
            optional.append(f"shot_{shot_type}")
        return {
            "required_assets": list(dict.fromkeys(required)),
            "optional_assets": list(dict.fromkeys(optional)),
        }

    @staticmethod
    def _rank_asset_candidates(
        *,
        scene_goal: str,
        visual_type: str,
        candidates: list[str],
        winning_shot_config: dict[str, Any] | None,
        render_history: list[dict[str, Any]] | None,
        render_inventory: dict[str, list[str]],
    ) -> list[str]:
        history = render_history or []
        scored: list[tuple[str, float]] = []
        for asset in candidates:
            score = 0.0
            if asset == visual_type:
                score += 2.0
            if scene_goal and scene_goal in asset:
                score += 1.5
            if winning_shot_config:
                if str(winning_shot_config.get("shot_type") or "") in asset:
                    score += 1.0
                if str(winning_shot_config.get("transition_style") or "") in asset:
                    score += 0.5
            if render_inventory.get(asset):
                score += 1.25
                score += min(len(render_inventory.get(asset, [])) * 0.1, 0.5)
            for row in history:
                if str(row.get("asset_type") or "") == asset:
                    score += float(row.get("conversion_outcome") or 0.0) * 0.8
                    score += float(row.get("retention_outcome") or 0.0) * 0.8
            scored.append((asset, score))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [a for a, _ in scored]

    def _build_asset_inventory(
        self,
        scene_assets: dict[str, Any],
        render_inventory: dict[str, list[str]],
    ) -> dict[str, Any]:
        """Build a structured asset_inventory keyed by asset_type.

        Returns:
            Dict mapping ``asset_type → {scenes: [scene_index, ...], render_urls: [...],
            available: bool}``.
        """
        inventory: dict[str, Any] = {}
        for scene_idx, scene_data in scene_assets.items():
            for asset_type in scene_data.get("required_assets", []):
                if asset_type not in inventory:
                    inventory[asset_type] = {
                        "asset_type": asset_type,
                        "scenes": [],
                        "render_urls": render_inventory.get(asset_type, []),
                        "available": asset_type in render_inventory and bool(render_inventory[asset_type]),
                    }
                try:
                    inventory[asset_type]["scenes"].append(int(scene_idx))
                except (ValueError, TypeError):
                    inventory[asset_type]["scenes"].append(scene_idx)
        return inventory

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
