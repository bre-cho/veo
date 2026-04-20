from __future__ import annotations

import uuid
from typing import Any

from app.schemas.lookbook import LookbookRequest, LookbookResponse


class LookbookEngine:
    def generate(self, req: LookbookRequest) -> LookbookResponse:
        outfits = self._build_outfits(req.products)
        scene_pack = self._build_scene_pack(outfits, req.style_preset)
        video_plan = {
            "target_platform": req.target_platform or "shorts",
            "scene_count": len(scene_pack),
            "narrative": "showcase -> styling_tip -> call_to_action",
            "collection_name": req.collection_name,
        }
        return LookbookResponse(
            lookbook_id=str(uuid.uuid4()),
            outfit_sequences=outfits,
            scene_pack=scene_pack,
            video_plan=video_plan,
        )

    @staticmethod
    def _build_outfits(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        outfits: list[dict[str, Any]] = []
        batch_size = 3
        for idx in range(0, len(products), batch_size):
            chunk = products[idx : idx + batch_size]
            if not chunk:
                continue
            outfits.append(
                {
                    "sequence_index": len(outfits) + 1,
                    "products": chunk,
                    "theme": chunk[0].get("style") or "signature",
                }
            )
        return outfits

    @staticmethod
    def _build_scene_pack(outfits: list[dict[str, Any]], style_preset: str | None) -> list[dict[str, Any]]:
        scenes: list[dict[str, Any]] = []
        for outfit in outfits:
            scenes.append(
                {
                    "scene_index": len(scenes) + 1,
                    "title": f"Outfit Set {outfit['sequence_index']}",
                    "shot_hint": "full-body editorial pan",
                    "style": style_preset or "clean-commerce",
                    "metadata": {"sequence_index": outfit["sequence_index"]},
                }
            )
        return scenes
