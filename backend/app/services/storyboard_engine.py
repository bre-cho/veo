from __future__ import annotations

import re
import uuid
from typing import Any

from app.schemas.storyboard import StoryboardResponse, StoryboardScene


class StoryboardEngine:
    MIN_PACING_WEIGHT = 0.6
    MAX_PACING_WEIGHT = 1.8
    _CTA_KEYWORDS = (
        "buy",
        "shop",
        "order",
        "join",
        "tap",
        "click",
        "start",
        "claim",
        "download",
    )

    def generate_from_script(
        self,
        *,
        script_text: str,
        conversion_mode: str | None = None,
        content_goal: str | None = None,
        preview_payload: dict[str, Any] | None = None,
    ) -> StoryboardResponse:
        paragraphs = self._to_paragraphs(script_text)
        scenes: list[StoryboardScene] = []

        for idx, text in enumerate(paragraphs, start=1):
            goal = self._scene_goal(idx, len(paragraphs), text)
            cta_flag = self._cta_flag(goal, text, conversion_mode)
            scenes.append(
                StoryboardScene(
                    scene_index=idx,
                    title=self._title(goal, idx),
                    scene_goal=goal,
                    visual_type=self._visual_type(goal),
                    emotion=self._emotion(goal),
                    cta_flag=cta_flag,
                    open_loop_flag=(idx == 1 or "?" in text),
                    shot_hint=self._shot_hint(goal),
                    pacing_weight=self._pacing_weight(goal, idx, len(paragraphs), conversion_mode),
                    voice_direction=self._voice_direction(goal),
                    transition_hint=self._transition_hint(goal),
                    metadata={
                        "source": "script_text",
                        "script_text": text,
                        "content_goal": content_goal,
                        "preview_scene_count": len((preview_payload or {}).get("scenes") or []),
                    },
                )
            )

        return StoryboardResponse(
            storyboard_id=str(uuid.uuid4()),
            scenes=scenes,
            summary={
                "scene_count": len(scenes),
                "has_cta": any(scene.cta_flag for scene in scenes),
                "content_goal": content_goal,
            },
        )

    def generate_from_preview(
        self,
        preview_payload: dict[str, Any],
        *,
        conversion_mode: str | None = None,
        content_goal: str | None = None,
    ) -> StoryboardResponse:
        scenes = preview_payload.get("scenes") or []
        text = "\n\n".join((scene.get("script_text") or "").strip() for scene in scenes if scene.get("script_text"))
        if not text:
            text = (preview_payload.get("script_text") or "").strip()
        return self.generate_from_script(
            script_text=text,
            conversion_mode=conversion_mode or preview_payload.get("conversion_mode"),
            content_goal=content_goal or preview_payload.get("content_goal"),
            preview_payload=preview_payload,
        )

    # backward compatibility
    def parse_script(self, script: str | list[str], *, max_scenes: int = 10) -> list[StoryboardScene]:
        text = script if isinstance(script, str) else "\n\n".join(script)
        resp = self.generate_from_script(script_text=text)
        return resp.scenes[:max_scenes]

    def to_scene_dicts(self, script: str | list[str], *, max_scenes: int = 10) -> list[dict[str, Any]]:
        return [scene.model_dump() for scene in self.parse_script(script, max_scenes=max_scenes)]

    @staticmethod
    def _to_paragraphs(text: str) -> list[str]:
        if not text.strip():
            return []
        parts = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        return parts or [line.strip() for line in text.splitlines() if line.strip()]

    def _scene_goal(self, idx: int, total: int, text: str) -> str:
        lower = text.lower()
        if idx == 1:
            return "hook"
        if idx == total and self._has_cta(lower):
            return "cta"
        if any(k in lower for k in ("problem", "pain", "struggle", "difficult")):
            return "build_tension"
        if any(k in lower for k in ("solution", "introducing", "here's", "now")):
            return "reveal"
        if self._has_cta(lower):
            return "cta"
        return "body"

    def _cta_flag(self, goal: str, text: str, conversion_mode: str | None) -> bool:
        return goal == "cta" or self._has_cta(text.lower()) or bool(conversion_mode)

    def _has_cta(self, lower: str) -> bool:
        return any(k in lower for k in self._CTA_KEYWORDS)

    @staticmethod
    def _title(goal: str, idx: int) -> str:
        return {
            "hook": "Hook",
            "build_tension": "Problem",
            "reveal": "Reveal",
            "body": f"Scene {idx}",
            "cta": "CTA",
        }.get(goal, f"Scene {idx}")

    @staticmethod
    def _visual_type(goal: str) -> str:
        return {
            "hook": "close-up",
            "build_tension": "medium-shot",
            "reveal": "product-shot",
            "body": "b-roll",
            "cta": "text-overlay",
        }.get(goal, "b-roll")

    @staticmethod
    def _emotion(goal: str) -> str | None:
        return {
            "hook": "curiosity",
            "build_tension": "tension",
            "reveal": "excitement",
            "body": "trust",
            "cta": "urgency",
        }.get(goal)

    @staticmethod
    def _shot_hint(goal: str) -> str | None:
        return {
            "hook": "fast punch-in, eye-level",
            "build_tension": "handheld realism",
            "reveal": "clean product hero frame",
            "body": "workflow demonstration",
            "cta": "brand lockup + text banner",
        }.get(goal)

    @staticmethod
    def _voice_direction(goal: str) -> str | None:
        return {
            "hook": "high-energy open with curiosity",
            "build_tension": "empathetic and direct",
            "reveal": "confident reveal tone",
            "body": "clear and trust-building",
            "cta": "decisive and action-oriented",
        }.get(goal)

    @staticmethod
    def _transition_hint(goal: str) -> str | None:
        return {
            "hook": "hard cut",
            "build_tension": "quick whip",
            "reveal": "snap reveal",
            "body": "match cut",
            "cta": "logo hold",
        }.get(goal)

    @staticmethod
    def _pacing_weight(goal: str, idx: int, total: int, conversion_mode: str | None) -> float:
        base = {
            "hook": 1.2,
            "build_tension": 1.0,
            "reveal": 1.1,
            "body": 0.9,
            "cta": 1.15,
        }.get(goal, 1.0)
        if conversion_mode and idx >= total - 1:
            base += 0.15
        return round(base, 2)
