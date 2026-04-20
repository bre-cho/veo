from __future__ import annotations

import uuid
from typing import Any

from app.schemas.scoring import CandidateScore
from app.schemas.lookbook import LookbookRequest, LookbookResponse


class LookbookEngine:
    def generate(self, req: LookbookRequest) -> LookbookResponse:
        candidate_styles = [req.style_preset or "clean-commerce", "editorial", "ugc-dynamic"]
        candidate_payloads: list[tuple[list[dict[str, Any]], list[dict[str, Any]], CandidateScore]] = []
        for idx, style in enumerate(candidate_styles):
            outfits = self._build_outfits(req.products)
            scene_pack = self._build_scene_pack(outfits, style)
            coherence = round(max(0.52, 0.86 - (idx * 0.05)), 3)
            compatibility = round(max(0.5, 0.88 - (idx * 0.04)), 3)
            campaign_fit = round(max(0.48, 0.84 - (idx * 0.06)), 3)
            localization_fit = round(max(0.45, 0.81 - (idx * 0.05)), 3)
            total = round(
                (coherence * 0.27)
                + (compatibility * 0.28)
                + (campaign_fit * 0.25)
                + (localization_fit * 0.2),
                3,
            )
            candidate_payloads.append(
                (
                    outfits,
                    scene_pack,
                    CandidateScore(
                        candidate_id=f"lookbook_{idx + 1}",
                        score_total=total,
                        score_breakdown={
                            "style_coherence": coherence,
                            "product_compatibility": compatibility,
                            "campaign_fit": campaign_fit,
                            "localization_fit": localization_fit,
                        },
                        rationale="Ranked using coherence/compatibility/campaign/localization scoring.",
                        metadata={"style": style},
                    ),
                )
            )

        winner_payload = max(candidate_payloads, key=lambda item: item[2].score_total)
        outfits, scene_pack, winner_score = winner_payload
        candidates = [item[2] for item in candidate_payloads]
        for score in candidates:
            score.winner_flag = score.candidate_id == winner_score.candidate_id

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
            candidates=candidates,
            winner_candidate_id=winner_score.candidate_id,
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
