from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Visual type vocabulary
# ---------------------------------------------------------------------------
_VISUAL_TYPES = (
    "close-up",
    "wide-shot",
    "medium-shot",
    "overhead",
    "talking-head",
    "b-roll",
    "text-overlay",
    "product-shot",
)

# ---------------------------------------------------------------------------
# Emotion vocabulary
# ---------------------------------------------------------------------------
_EMOTIONS = (
    "curiosity",
    "tension",
    "excitement",
    "relief",
    "trust",
    "urgency",
    "satisfaction",
    "neutral",
)

# ---------------------------------------------------------------------------
# Keyword → beat heuristics
# ---------------------------------------------------------------------------
_HOOK_KEYWORDS = frozenset(
    [
        "did you know",
        "struggling",
        "?",
        "secret",
        "hack",
        "mistake",
        "stop",
        "before you",
        "ever wonder",
        "most people",
        "you won't believe",
        "what if",
        "warning",
        "alert",
        "finally",
    ]
)

_TENSION_KEYWORDS = frozenset(
    [
        "problem",
        "pain",
        "frustrat",
        "fail",
        "waste",
        "lost",
        "confus",
        "hard",
        "difficult",
        "struggle",
        "slow",
        "expensive",
        "broken",
        "bad",
        "wrong",
        "issue",
        "challenge",
    ]
)

_REVEAL_KEYWORDS = frozenset(
    [
        "introduc",
        "meet",
        "here's",
        "now with",
        "that's why",
        "the solution",
        "imagine",
        "transform",
        "change",
        "discover",
        "built for",
        "finally",
        "unlock",
        "powered by",
    ]
)

_CTA_KEYWORDS = frozenset(
    [
        "get",
        "buy",
        "shop",
        "try",
        "start",
        "join",
        "sign up",
        "click",
        "tap",
        "order",
        "download",
        "claim",
        "grab",
        "now",
        "today",
        "link in bio",
        "swipe",
        "subscribe",
        "follow",
    ]
)

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class SceneBeat:
    """A single scene in a storyboard."""

    scene_index: int
    scene_goal: str  # hook | build_tension | reveal | cta | body
    visual_type: str
    emotion: str
    cta_flag: bool
    script_text: str
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "scene_goal": self.scene_goal,
            "visual_type": self.visual_type,
            "emotion": self.emotion,
            "cta_flag": self.cta_flag,
            "script_text": self.script_text,
            "title": self.title,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# StoryboardEngine
# ---------------------------------------------------------------------------


class StoryboardEngine:
    """Converts a script (list of paragraph strings or raw text) into
    a list of :class:`SceneBeat` objects suitable for injection into
    the planner / render pipeline.

    Beat classification uses keyword heuristics so it works with zero
    external dependencies.

    Beat sequence:
        1. hook          – attention-grab, curiosity driver
        2. build_tension – pain-point / problem exposition
        3. reveal        – solution / product introduction
        4. body          – features / benefits (one per remaining scene)
        5. cta           – call to action (always last)
    """

    # Mapping scene_goal → (visual_type, emotion)
    _BEAT_DEFAULTS: dict[str, tuple[str, str]] = {
        "hook": ("close-up", "curiosity"),
        "build_tension": ("medium-shot", "tension"),
        "reveal": ("product-shot", "excitement"),
        "body": ("b-roll", "trust"),
        "cta": ("text-overlay", "urgency"),
    }

    def parse_script(
        self,
        script: str | list[str],
        *,
        max_scenes: int = 10,
    ) -> list[SceneBeat]:
        """Parse a raw script into ordered SceneBeat objects.

        Args:
            script: Either a newline-separated string or a list of paragraphs.
            max_scenes: Cap on number of scenes produced.

        Returns:
            List of SceneBeat, always starting with a hook and ending with a
            cta if the source text contains any CTA signals.
        """
        paragraphs = self._to_paragraphs(script)
        if not paragraphs:
            return []

        beats: list[SceneBeat] = []
        for idx, text in enumerate(paragraphs[:max_scenes], start=1):
            goal = self._classify_goal(text, idx, len(paragraphs))
            visual_type, emotion = self._pick_visual_emotion(goal, text)
            cta_flag = goal == "cta" or self._has_cta_signal(text)
            beats.append(
                SceneBeat(
                    scene_index=idx,
                    scene_goal=goal,
                    visual_type=visual_type,
                    emotion=emotion,
                    cta_flag=cta_flag,
                    script_text=text.strip(),
                    title=self._make_title(goal, idx),
                    metadata={"storyboard_beat": goal},
                )
            )

        return beats

    def to_scene_dicts(
        self,
        script: str | list[str],
        *,
        max_scenes: int = 10,
    ) -> list[dict[str, Any]]:
        """Convenience wrapper — returns plain dicts for injection into
        provider_scene_planner or render pipeline."""
        return [b.to_dict() for b in self.parse_script(script, max_scenes=max_scenes)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_paragraphs(self, script: str | list[str]) -> list[str]:
        if isinstance(script, list):
            return [p.strip() for p in script if p.strip()]
        lines = re.split(r"\n{2,}", script.strip())
        paras = [p.strip() for p in lines if p.strip()]
        if not paras:
            paras = [p.strip() for p in script.strip().split("\n") if p.strip()]
        return paras

    def _classify_goal(self, text: str, idx: int, total: int) -> str:
        text_lower = text.lower()

        # First paragraph is always the hook
        if idx == 1:
            return "hook"

        # Last paragraph — check for CTA signal
        if idx == total and self._has_cta_signal(text_lower):
            return "cta"

        if self._has_tension_signal(text_lower):
            return "build_tension"

        if self._has_reveal_signal(text_lower):
            return "reveal"

        # Explicit CTA anywhere
        if self._has_cta_signal(text_lower):
            return "cta"

        return "body"

    def _pick_visual_emotion(self, goal: str, text: str) -> tuple[str, str]:
        visual_type, emotion = self._BEAT_DEFAULTS.get(goal, ("b-roll", "neutral"))
        text_lower = text.lower()
        # Refine emotion for body scenes
        if goal == "body":
            if any(kw in text_lower for kw in ("thousand", "million", "proven", "trust", "customers")):
                emotion = "trust"
            elif any(kw in text_lower for kw in ("fast", "instant", "quick", "second")):
                emotion = "excitement"
        return visual_type, emotion

    def _make_title(self, goal: str, idx: int) -> str:
        titles = {
            "hook": "Hook",
            "build_tension": "Build Tension",
            "reveal": "Reveal",
            "body": f"Scene {idx}",
            "cta": "CTA",
        }
        return titles.get(goal, f"Scene {idx}")

    def _has_cta_signal(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in _CTA_KEYWORDS)

    def _has_tension_signal(self, text: str) -> bool:
        return any(kw in text for kw in _TENSION_KEYWORDS)

    def _has_reveal_signal(self, text: str) -> bool:
        return any(kw in text for kw in _REVEAL_KEYWORDS)
