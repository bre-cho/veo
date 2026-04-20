from __future__ import annotations

import re
import uuid
from typing import Any

from app.schemas.storyboard import StoryboardResponse, StoryboardScene

# ---------------------------------------------------------------------------
# Platform grammar: each platform has its own pacing and beat structure
# ---------------------------------------------------------------------------
_PLATFORM_GRAMMAR: dict[str, dict[str, Any]] = {
    "tiktok": {
        "max_hook_sec": 3.0,     # hook must land within first 3 seconds
        "ideal_scene_duration": 5.0,
        "cta_position": "late",  # CTA at end
        "hook_weight": 1.6,
        "cta_weight": 1.3,
        "body_weight": 0.8,
        "transition_style": "jump_cut",
        "beat_pattern": ["hook", "tension", "reveal", "body", "cta"],
    },
    "shorts": {
        "max_hook_sec": 3.0,
        "ideal_scene_duration": 6.0,
        "cta_position": "end",
        "hook_weight": 1.5,
        "cta_weight": 1.2,
        "body_weight": 0.9,
        "transition_style": "hard_cut",
        "beat_pattern": ["hook", "tension", "reveal", "body", "cta"],
    },
    "reels": {
        "max_hook_sec": 3.0,
        "ideal_scene_duration": 5.0,
        "cta_position": "late",
        "hook_weight": 1.5,
        "cta_weight": 1.25,
        "body_weight": 0.85,
        "transition_style": "whip_pan",
        "beat_pattern": ["hook", "tension", "reveal", "body", "cta"],
    },
    "youtube": {
        "max_hook_sec": 8.0,
        "ideal_scene_duration": 15.0,
        "cta_position": "middle_and_end",
        "hook_weight": 1.2,
        "cta_weight": 1.1,
        "body_weight": 1.0,
        "transition_style": "match_cut",
        "beat_pattern": ["hook", "intro", "body", "body", "reveal", "social_proof", "cta"],
    },
    "facebook": {
        "max_hook_sec": 5.0,
        "ideal_scene_duration": 8.0,
        "cta_position": "end",
        "hook_weight": 1.3,
        "cta_weight": 1.2,
        "body_weight": 0.95,
        "transition_style": "dissolve",
        "beat_pattern": ["hook", "tension", "body", "reveal", "cta"],
    },
}

_DEFAULT_PLATFORM_GRAMMAR = _PLATFORM_GRAMMAR["shorts"]


def _get_platform_grammar(platform: str | None) -> dict[str, Any]:
    if not platform:
        return _DEFAULT_PLATFORM_GRAMMAR
    return _PLATFORM_GRAMMAR.get(platform.lower(), _DEFAULT_PLATFORM_GRAMMAR)


def _build_beat_map(scenes: list[StoryboardScene], platform: str | None) -> list[dict[str, Any]]:
    """Generate a beat map for the storyboard aligned to the platform's grammar.

    Each beat entry captures which scene covers it, the expected timing, and
    whether the scene is on-beat or drifting from the ideal beat pattern.
    """
    grammar = _get_platform_grammar(platform)
    beat_pattern = grammar["beat_pattern"]
    beat_map: list[dict[str, Any]] = []
    ideal_dur = grammar["ideal_scene_duration"]

    for beat_idx, expected_beat in enumerate(beat_pattern):
        scene = scenes[beat_idx] if beat_idx < len(scenes) else None
        actual_goal = scene.scene_goal if scene else None
        on_beat = actual_goal == expected_beat

        beat_map.append({
            "beat_index": beat_idx + 1,
            "expected_beat": expected_beat,
            "actual_beat": actual_goal,
            "on_beat": on_beat,
            "scene_index": scene.scene_index if scene else None,
            "ideal_duration_sec": ideal_dur,
            "pacing_weight": scene.pacing_weight if scene else 1.0,
        })
    return beat_map


def _build_scene_dependency_graph(scenes: list[StoryboardScene]) -> dict[str, Any]:
    """Build a dependency graph that describes narrative flow between scenes.

    Nodes represent scenes; edges represent narrative dependency (i.e., scene N
    logically depends on / follows from scene N-1).
    """
    nodes = [
        {
            "id": f"scene_{s.scene_index}",
            "scene_index": s.scene_index,
            "scene_goal": s.scene_goal,
            "cta_flag": s.cta_flag,
        }
        for s in scenes
    ]
    edges = []
    for i in range(len(scenes) - 1):
        edges.append({
            "from": f"scene_{scenes[i].scene_index}",
            "to": f"scene_{scenes[i + 1].scene_index}",
            "type": "sequential",
            "transition": scenes[i].transition_hint or "cut",
        })
    return {"nodes": nodes, "edges": edges}


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
        platform: str | None = None,
    ) -> StoryboardResponse:
        grammar = _get_platform_grammar(platform)
        paragraphs = self._to_paragraphs(script_text)
        scenes: list[StoryboardScene] = []

        for idx, text in enumerate(paragraphs, start=1):
            goal = self._scene_goal(idx, len(paragraphs), text)
            cta_flag = self._cta_flag(goal, text, conversion_mode, grammar)
            scenes.append(
                StoryboardScene(
                    scene_index=idx,
                    title=self._title(goal, idx),
                    scene_goal=goal,
                    visual_type=self._visual_type(goal),
                    emotion=self._emotion(goal),
                    cta_flag=cta_flag,
                    open_loop_flag=(idx == 1 or "?" in text),
                    shot_hint=self._shot_hint(goal, grammar),
                    pacing_weight=self._pacing_weight(goal, idx, len(paragraphs), conversion_mode, grammar),
                    voice_direction=self._voice_direction(goal),
                    transition_hint=self._transition_hint(goal, grammar),
                    metadata={
                        "source": "script_text",
                        "script_text": text,
                        "content_goal": content_goal,
                        "platform": platform,
                        "preview_scene_count": len((preview_payload or {}).get("scenes") or []),
                    },
                )
            )

        # Reorder scenes to optimise hook → build-up → CTA flow when needed
        scenes = self._optimise_scene_flow(scenes, grammar, conversion_mode)

        beat_map = _build_beat_map(scenes, platform)
        dependency_graph = _build_scene_dependency_graph(scenes)

        return StoryboardResponse(
            storyboard_id=str(uuid.uuid4()),
            scenes=scenes,
            summary={
                "scene_count": len(scenes),
                "has_cta": any(scene.cta_flag for scene in scenes),
                "content_goal": content_goal,
                "platform": platform,
                "platform_grammar": {
                    "hook_max_sec": grammar["max_hook_sec"],
                    "ideal_scene_duration": grammar["ideal_scene_duration"],
                    "cta_position": grammar["cta_position"],
                },
                "beat_map": beat_map,
                "dependency_graph": dependency_graph,
                "hook_retention_score": self._compute_hook_retention_score(scenes, grammar),
            },
        )

    def generate_from_preview(
        self,
        preview_payload: dict[str, Any],
        *,
        conversion_mode: str | None = None,
        content_goal: str | None = None,
        platform: str | None = None,
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
            platform=platform or preview_payload.get("target_platform"),
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

    def _cta_flag(
        self,
        goal: str,
        text: str,
        conversion_mode: str | None,
        grammar: dict[str, Any] | None = None,
    ) -> bool:
        base = goal == "cta" or self._has_cta(text.lower()) or bool(conversion_mode)
        # YouTube: CTA also in the middle (scene 3+)
        if grammar and grammar.get("cta_position") == "middle_and_end" and self._has_cta(text.lower()):
            return True
        return base

    def _has_cta(self, lower: str) -> bool:
        return any(k in lower for k in self._CTA_KEYWORDS)

    @staticmethod
    def _title(goal: str, idx: int) -> str:
        return {
            "hook": "Hook",
            "build_tension": "Problem",
            "reveal": "Reveal",
            "body": f"Scene {idx}",
            "intro": "Introduction",
            "social_proof": "Social Proof",
            "cta": "CTA",
        }.get(goal, f"Scene {idx}")

    @staticmethod
    def _visual_type(goal: str) -> str:
        return {
            "hook": "close-up",
            "build_tension": "medium-shot",
            "reveal": "product-shot",
            "body": "b-roll",
            "intro": "medium-shot",
            "social_proof": "testimonial",
            "cta": "text-overlay",
        }.get(goal, "b-roll")

    @staticmethod
    def _emotion(goal: str) -> str | None:
        return {
            "hook": "curiosity",
            "build_tension": "tension",
            "reveal": "excitement",
            "body": "trust",
            "intro": "warmth",
            "social_proof": "credibility",
            "cta": "urgency",
        }.get(goal)

    @staticmethod
    def _shot_hint(goal: str, grammar: dict[str, Any] | None = None) -> str | None:
        base = {
            "hook": "fast punch-in, eye-level",
            "build_tension": "handheld realism",
            "reveal": "clean product hero frame",
            "body": "workflow demonstration",
            "intro": "talking-head, warm framing",
            "social_proof": "testimonial close-up",
            "cta": "brand lockup + text banner",
        }.get(goal)
        if grammar and grammar.get("transition_style") == "jump_cut" and goal == "hook":
            return "extreme close-up punch-in, jump-cut ready"
        return base

    @staticmethod
    def _voice_direction(goal: str) -> str | None:
        return {
            "hook": "high-energy open with curiosity",
            "build_tension": "empathetic and direct",
            "reveal": "confident reveal tone",
            "body": "clear and trust-building",
            "intro": "warm and inviting",
            "social_proof": "authentic and credible",
            "cta": "decisive and action-oriented",
        }.get(goal)

    @staticmethod
    def _transition_hint(goal: str, grammar: dict[str, Any] | None = None) -> str | None:
        # Use platform-specific transitions when available
        if grammar:
            style = grammar.get("transition_style", "hard_cut")
            return {
                "hook": style,
                "build_tension": "quick whip" if style == "jump_cut" else style,
                "reveal": "snap reveal",
                "body": "match cut",
                "intro": "dissolve",
                "social_proof": "cross-dissolve",
                "cta": "logo hold",
            }.get(goal)
        return {
            "hook": "hard cut",
            "build_tension": "quick whip",
            "reveal": "snap reveal",
            "body": "match cut",
            "cta": "logo hold",
        }.get(goal)

    @staticmethod
    def _pacing_weight(
        goal: str,
        idx: int,
        total: int,
        conversion_mode: str | None,
        grammar: dict[str, Any] | None = None,
    ) -> float:
        if grammar:
            weight_map = {
                "hook": grammar.get("hook_weight", 1.2),
                "build_tension": 1.0,
                "reveal": 1.1,
                "body": grammar.get("body_weight", 0.9),
                "intro": 0.95,
                "social_proof": 1.0,
                "cta": grammar.get("cta_weight", 1.15),
            }
        else:
            weight_map = {
                "hook": 1.2,
                "build_tension": 1.0,
                "reveal": 1.1,
                "body": 0.9,
                "cta": 1.15,
            }
        base = weight_map.get(goal, 1.0)
        if conversion_mode and idx >= total - 1:
            base += 0.15
        return round(base, 2)

    @staticmethod
    def _optimise_scene_flow(
        scenes: list[StoryboardScene],
        grammar: dict[str, Any],
        conversion_mode: str | None,
    ) -> list[StoryboardScene]:
        """Reorder CTA scenes to the end and ensure the hook comes first.

        For short-form platforms: moves any mid-body CTA scenes to after the last
        body scene when conversion_mode is not set (avoid premature CTA exit).
        For YouTube: leaves structure as-is (mid-roll CTA is OK).
        """
        if not scenes:
            return scenes
        cta_position = grammar.get("cta_position", "end")

        if cta_position == "middle_and_end":
            # YouTube: keep existing order; CTA is welcome mid-roll
            return scenes

        # Short-form: ensure hook is first, CTA is last
        non_cta = [s for s in scenes if s.scene_goal != "cta"]
        cta_scenes = [s for s in scenes if s.scene_goal == "cta"]

        reordered = non_cta + cta_scenes
        # Re-index scenes
        for new_idx, scene in enumerate(reordered, start=1):
            scene.scene_index = new_idx
        return reordered

    @staticmethod
    def _compute_hook_retention_score(
        scenes: list[StoryboardScene],
        grammar: dict[str, Any],
    ) -> float:
        """Estimate how well the first few seconds will retain viewers.

        Heuristic score in [0, 1] based on the hook scene's pacing weight,
        open-loop flag, and alignment with platform grammar.
        """
        if not scenes:
            return 0.0
        hook_scene = scenes[0]
        if hook_scene.scene_goal != "hook":
            return 0.3  # Hook is not first – bad for retention

        score = 0.0
        # Pacing weight contribution
        hook_weight = grammar.get("hook_weight", 1.2)
        score += min(hook_scene.pacing_weight / hook_weight, 1.0) * 0.4

        # Open loop boosts curiosity
        if hook_scene.open_loop_flag:
            score += 0.3

        # Short-form: punchy transition is important
        if hook_scene.transition_hint and any(
            t in (hook_scene.transition_hint or "").lower()
            for t in ("jump_cut", "cut", "punch")
        ):
            score += 0.3

        return round(min(score, 1.0), 3)
