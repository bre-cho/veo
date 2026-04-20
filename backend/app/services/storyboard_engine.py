from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING, Any

from app.schemas.storyboard import StoryboardResponse, StoryboardScene

if TYPE_CHECKING:
    from app.services.learning_engine import PerformanceLearningEngine

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
        learning_store: "PerformanceLearningEngine | None" = None,
        episode_memory: dict[str, Any] | None = None,
    ) -> StoryboardResponse:
        grammar = _get_platform_grammar(platform)
        paragraphs = self._to_paragraphs(script_text)
        scenes: list[StoryboardScene] = []

        # Derive pacing boost from learning store for hook scenes
        hook_pacing_boost = 0.0
        if learning_store is not None:
            try:
                hook_pacing_boost = _derive_hook_pacing_boost(learning_store, platform=platform)
            except Exception:
                hook_pacing_boost = 0.0

        # Inject open-loop resolution beat from episode memory when available
        resolution_hint: str | None = None
        if episode_memory:
            open_loops: list[str] = episode_memory.get("open_loops") or []
            if open_loops:
                resolution_hint = open_loops[0]

        for idx, text in enumerate(paragraphs, start=1):
            goal = self._scene_goal(idx, len(paragraphs), text)
            cta_flag = self._cta_flag(goal, text, conversion_mode, grammar)
            pacing = self._pacing_weight(goal, idx, len(paragraphs), conversion_mode, grammar)
            if goal == "hook" and hook_pacing_boost:
                pacing = round(min(pacing + hook_pacing_boost, self.MAX_PACING_WEIGHT), 2)

            # Inject resolution hint as metadata on the last body scene
            scene_meta: dict[str, Any] = {
                "source": "script_text",
                "script_text": text,
                "content_goal": content_goal,
                "platform": platform,
                "preview_scene_count": len((preview_payload or {}).get("scenes") or []),
            }
            if resolution_hint and goal == "body" and idx == len(paragraphs) - 1:
                scene_meta["resolution_hint"] = resolution_hint

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
                    pacing_weight=pacing,
                    voice_direction=self._voice_direction(goal),
                    transition_hint=self._transition_hint(goal, grammar),
                    metadata=scene_meta,
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
                "hook_pacing_boost": hook_pacing_boost,
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

    @staticmethod
    def plan_shot_assets(
        scenes: list[StoryboardScene],
        avatar_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a per-scene asset production checklist.

        Returns a list of dicts (one per scene) describing what assets need to
        be prepared: background type, avatar pose, overlay text flag, and
        b-roll category.  This is used by the production pipeline to pre-fetch
        or generate required materials before a render job is created.
        """
        _GOAL_BACKGROUNDS = {
            "hook": "branded_gradient",
            "build_tension": "environmental",
            "reveal": "product_hero",
            "body": "neutral_studio",
            "intro": "warm_studio",
            "social_proof": "lifestyle",
            "cta": "brand_lockup",
        }
        _GOAL_POSES = {
            "hook": "direct_address",
            "build_tension": "expressive",
            "reveal": "presenting",
            "body": "explaining",
            "intro": "welcoming",
            "social_proof": "testimonial_close_up",
            "cta": "pointing_cta",
        }
        _GOAL_BROLL = {
            "hook": "teaser_clip",
            "build_tension": "problem_montage",
            "reveal": "product_close_up",
            "body": "workflow_demo",
            "intro": "avatar_intro",
            "social_proof": "before_after",
            "cta": None,
        }
        checklist = []
        for scene in scenes:
            goal = scene.scene_goal
            checklist.append({
                "scene_index": scene.scene_index,
                "scene_goal": goal,
                "avatar_id": avatar_id,
                "background_type": _GOAL_BACKGROUNDS.get(goal, "neutral_studio"),
                "avatar_pose": _GOAL_POSES.get(goal, "explaining"),
                "overlay_text": scene.cta_flag or goal in ("hook", "cta"),
                "broll_category": _GOAL_BROLL.get(goal),
                "voice_direction": scene.voice_direction,
                "shot_hint": scene.shot_hint,
            })
        return checklist


# ---------------------------------------------------------------------------
# Continuity Planner
# ---------------------------------------------------------------------------

class ContinuityPlanner:
    """Plan narrative continuity between consecutive episodes.

    ``plan_continuity()`` inspects the previous episode's storyboard and
    returns a list of ``continuity_hints`` that the next episode should respect
    (open loop resolutions, colour palette consistency, character state).

    This is used by the StoryboardEngine's Director OS layer to inject hints
    into new episode generation rather than starting from a blank slate.
    """

    def plan_continuity(
        self,
        prev_episode: StoryboardResponse,
        next_script: str,
    ) -> list[str]:
        """Return continuity hints to inject into the next episode.

        Analyses the previous storyboard for:
        - Unresolved open loops (scenes with ``open_loop_flag=True`` not
          followed by a resolve)
        - CTA position mismatch
        - Scene-count consistency
        """
        hints: list[str] = []
        scenes = prev_episode.scenes
        if not scenes:
            return hints

        # 1. Detect open loops in previous episode
        open_scene_goals = {
            scene.scene_goal
            for scene in scenes
            if scene.open_loop_flag
        }
        cta_scene_goals = {scene.scene_goal for scene in scenes if scene.cta_flag}
        unresolved = open_scene_goals - cta_scene_goals - {"hook"}
        if unresolved:
            hints.append(
                f"Resolve open narrative threads from previous episode: {', '.join(sorted(unresolved))}"
            )

        # 2. Maintain colour palette consistency (inferred from visual_type)
        first_scene_visual = scenes[0].visual_type if scenes else None
        if first_scene_visual:
            hints.append(
                f"Maintain visual style consistency: open with a '{first_scene_visual}' shot to signal continuity"
            )

        # 3. Character state carry-over
        prev_summary = prev_episode.summary or {}
        content_goal = prev_summary.get("content_goal")
        if content_goal:
            hints.append(
                f"Continue '{content_goal}' content arc; reference the product outcome established in the prior episode"
            )

        # 4. Platform grammar consistency
        platform = prev_summary.get("platform")
        if platform:
            hints.append(
                f"Use '{platform}' platform grammar for pacing and transitions to match viewer expectations"
            )

        return hints

    def save_episode_memory(
        self,
        db: Any,
        *,
        series_id: str,
        episode_index: int,
        storyboard: StoryboardResponse,
        character_state: dict[str, Any] | None = None,
    ) -> None:
        """Persist this episode's state into ``EpisodeMemory`` for future continuity checks."""
        try:
            from app.models.episode_memory import EpisodeMemory

            scenes = storyboard.scenes
            open_loops = [
                s.scene_goal
                for s in scenes
                if s.open_loop_flag and s.scene_goal != "hook"
            ]
            resolved_loops = [s.scene_goal for s in scenes if s.cta_flag]

            row = EpisodeMemory(
                series_id=series_id,
                episode_index=episode_index,
                storyboard_id=storyboard.storyboard_id,
                character_state=character_state or {},
                open_loops=open_loops,
                resolved_loops=resolved_loops,
            )
            db.add(row)
            db.commit()
        except Exception:
            pass  # Non-fatal

    @staticmethod
    def load_latest_episode(db: Any, series_id: str) -> dict[str, Any] | None:
        """Load the most recent episode memory for a series, or None."""
        try:
            from app.models.episode_memory import EpisodeMemory

            row = (
                db.query(EpisodeMemory)
                .filter(EpisodeMemory.series_id == series_id)
                .order_by(EpisodeMemory.episode_index.desc())
                .first()
            )
            if row is None:
                return None
            return {
                "series_id": row.series_id,
                "episode_index": row.episode_index,
                "storyboard_id": row.storyboard_id,
                "character_state": row.character_state or {},
                "open_loops": row.open_loops or [],
                "resolved_loops": row.resolved_loops or [],
            }
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Scene Pattern Library
# ---------------------------------------------------------------------------

class ScenePatternLibrary:
    """Store and query winning scene patterns.

    Wraps ``PatternLibrary`` with scene-specific query helpers.  Patterns are
    stored with ``pattern_type='scene_pattern'`` and a payload containing
    ``platform``, ``scene_goal``, and ``conversion_score``.
    """

    _PATTERN_TYPE = "scene_pattern"
    _MIN_CONVERSION_SCORE = 0.75

    def save_winning_scenes(
        self,
        db: Any,
        *,
        storyboard: StoryboardResponse,
        platform: str | None,
        content_goal: str | None,
        conversion_score: float,
    ) -> None:
        """Persist high-scoring scenes as reusable patterns."""
        if conversion_score < self._MIN_CONVERSION_SCORE:
            return
        from app.services.pattern_library import PatternLibrary
        from app.schemas.patterns import PatternMemoryIn

        lib = PatternLibrary()
        for scene in storyboard.scenes:
            pattern = PatternMemoryIn(
                pattern_type=self._PATTERN_TYPE,
                content_goal=content_goal,
                source_id=storyboard.storyboard_id,
                score=conversion_score,
                payload={
                    "platform": platform,
                    "scene_goal": scene.scene_goal,
                    "visual_type": scene.visual_type,
                    "shot_hint": scene.shot_hint,
                    "pacing_weight": scene.pacing_weight,
                    "emotion": scene.emotion,
                    "voice_direction": scene.voice_direction,
                    "transition_hint": scene.transition_hint,
                },
            )
            try:
                lib.save(db, pattern)
            except Exception:
                pass

    def get_top_patterns(
        self,
        db: Any,
        *,
        platform: str | None = None,
        scene_goal: str | None = None,
        content_goal: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return top winning scene patterns for a platform/scene_goal combo."""
        from app.services.pattern_library import PatternLibrary

        lib = PatternLibrary()
        rows = lib.list(
            db,
            pattern_type=self._PATTERN_TYPE,
            content_goal=content_goal,
        )
        # Filter by platform and scene_goal from payload
        filtered = []
        for row in rows:
            p = row.payload or {}
            if platform and p.get("platform") != platform:
                continue
            if scene_goal and p.get("scene_goal") != scene_goal:
                continue
            filtered.append(p)
        return filtered[:limit]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _derive_hook_pacing_boost(
    learning_store: "PerformanceLearningEngine",
    platform: str | None,
) -> float:
    """Return a +0.1 pacing boost for hook scenes when top performers reward it.

    Queries the learning store for top hook patterns on the given platform and
    returns 0.1 when any winning pattern is a hook-type pattern, else 0.0.
    """
    try:
        top_hooks = learning_store.top_hooks(platform=platform)
        if top_hooks:
            return 0.1
    except Exception:
        pass
    return 0.0
