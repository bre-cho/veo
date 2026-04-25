from __future__ import annotations


class RebuildCostEstimator:
    """Estimate per-scene rebuild cost and time given a change type.

    Costs are expressed in abstract *cost units* (not real currency).  The
    defaults match the relative expense of each processing step:

    * ``audio``    — TTS regeneration
    * ``video``    — avatar/diffusion rendering (most expensive)
    * ``subtitle`` — subtitle file rebuild
    * ``chunk``    — FFmpeg scene chunk encode (always incurred)
    * ``concat``   — final episode concat (not per-scene; excluded here)
    """

    DEFAULT_COSTS: dict = {
        "audio": 1.0,
        "video": 10.0,
        "subtitle": 0.5,
        "chunk": 2.0,
        "concat": 1.0,
    }

    DEFAULT_TIME_SEC: dict = {
        "audio": 8.0,
        "video": 90.0,
        "subtitle": 1.0,
        "chunk": 8.0,
        "concat": 5.0,
    }

    def estimate_scene(
        self,
        scene_manifest: dict,
        change_type: str,
    ) -> dict:
        """Estimate rebuild cost and time for a single scene.

        Args:
            scene_manifest: Scene manifest dict (must include ``scene_id``).
            change_type: Category of the change.

        Returns:
            Dict with ``scene_id``, ``estimated_cost``, ``estimated_time_sec``.
        """
        cost = 0.0
        time_sec = 0.0

        if change_type in ("voice", "all"):
            cost += self.DEFAULT_COSTS["audio"]
            time_sec += self.DEFAULT_TIME_SEC["audio"]

        if change_type in ("video", "avatar", "style", "continuity", "shared_asset", "all"):
            cost += self.DEFAULT_COSTS["video"]
            time_sec += self.DEFAULT_TIME_SEC["video"]

        if change_type in ("subtitle", "voice", "timeline", "all"):
            cost += self.DEFAULT_COSTS["subtitle"]
            time_sec += self.DEFAULT_TIME_SEC["subtitle"]

        # Chunk encode is always needed.
        cost += self.DEFAULT_COSTS["chunk"]
        time_sec += self.DEFAULT_TIME_SEC["chunk"]

        return {
            "scene_id": scene_manifest["scene_id"],
            "estimated_cost": round(cost, 2),
            "estimated_time_sec": round(time_sec, 2),
        }

    def estimate_many(
        self,
        manifests: list,
        change_type: str,
    ) -> dict:
        """Estimate total rebuild cost and time for a set of scenes.

        Args:
            manifests: List of scene manifest dicts.
            change_type: Category of the change.

        Returns:
            Dict with ``items``, ``estimated_cost``, ``estimated_time_sec``.
        """
        items = [self.estimate_scene(item, change_type) for item in manifests]
        return {
            "items": items,
            "estimated_cost": round(sum(i["estimated_cost"] for i in items), 2),
            "estimated_time_sec": round(sum(i["estimated_time_sec"] for i in items), 2),
        }
