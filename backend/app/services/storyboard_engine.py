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
        use_winning_graph: bool = False,
        include_asset_plan: bool = False,
        avatar_id: str | None = None,
    ) -> StoryboardResponse:
        grammar = _get_platform_grammar(platform)
        paragraphs = self._to_paragraphs(script_text)
        scenes: list[StoryboardScene] = []

        # Derive per-scene pacing boosts from learning store and pattern library.
        # Previously only the hook scene was boosted; now all scene types benefit
        # from winning-scene performance data.
        scene_pacing_boosts: dict[str, float] = {}
        hook_pacing_boost = 0.0
        if learning_store is not None:
            try:
                scene_pacing_boosts = _derive_all_scene_pacing_boosts(
                    learning_store, platform=platform
                )
                hook_pacing_boost = scene_pacing_boosts.get("hook", 0.0)
            except Exception:
                scene_pacing_boosts = {}
                hook_pacing_boost = 0.0

        # Phase 4.3: Use winning_scene_sequence from episode memory as baseline
        winning_sequence: list[dict] | None = None
        if episode_memory:
            winning_sequence = episode_memory.get("winning_scene_sequence")

        # Phase 4.4: Load winning scene graph when requested
        winning_graph_used = False
        winning_graph_sequence: list[dict] | None = None
        if use_winning_graph:
            try:
                from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore
                store = WinningSceneGraphStore()
                top_graphs = store.get_top_graphs(platform=platform, limit=1)
                if top_graphs:
                    winning_graph_sequence = top_graphs[0].get("scene_sequence")
                    winning_graph_used = bool(winning_graph_sequence)
            except Exception:
                pass

        # Inject open-loop resolution beat from episode memory when available
        resolution_hint: str | None = None
        if episode_memory:
            open_loops: list[str] = episode_memory.get("open_loops") or []
            if open_loops:
                resolution_hint = open_loops[0]

        for idx, text in enumerate(paragraphs, start=1):
            goal = self._scene_goal(idx, len(paragraphs), text)

            # Phase 4.4: When winning graph sequence available, align scene goal
            if winning_graph_sequence and idx <= len(winning_graph_sequence):
                override_goal = winning_graph_sequence[idx - 1].get("scene_goal")
                if override_goal:
                    goal = override_goal

            # Phase 4.3: When winning sequence from episode memory, use pacing hint
            winning_pacing: float | None = None
            if winning_sequence and idx <= len(winning_sequence):
                winning_pacing = winning_sequence[idx - 1].get("pacing_weight")

            cta_flag = self._cta_flag(goal, text, conversion_mode, grammar)
            pacing = self._pacing_weight(goal, idx, len(paragraphs), conversion_mode, grammar)
            # Apply outcome-informed pacing boost for this scene goal when available
            goal_boost = scene_pacing_boosts.get(goal, 0.0)
            if goal_boost:
                pacing = round(min(pacing + goal_boost, self.MAX_PACING_WEIGHT), 2)
            # Phase 4.3: override with winning episode pacing
            if winning_pacing is not None:
                pacing = round(float(winning_pacing), 2)

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

        summary: dict[str, Any] = {
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
            "scene_pacing_boosts": scene_pacing_boosts,
            "winning_graph_used": winning_graph_used,
        }

        storyboard_id = str(uuid.uuid4())

        # Phase 4.2: asset plan when requested
        asset_plan: dict[str, Any] | None = None
        if include_asset_plan and avatar_id:
            try:
                from app.services.storyboard.scene_asset_planner import SceneAssetPlanner
                planner = SceneAssetPlanner()
                response_for_planner = StoryboardResponse(
                    storyboard_id=storyboard_id, scenes=scenes, summary=summary
                )
                asset_plan = planner.plan_assets(response_for_planner, avatar_id)
            except Exception:
                asset_plan = None

        response = StoryboardResponse(
            storyboard_id=storyboard_id,
            scenes=scenes,
            summary=summary,
        )
        if asset_plan is not None:
            response.summary["asset_plan"] = asset_plan
        return response

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

        Returns a full asset manifest per scene: ``video_clip_type``,
        ``prop_list``, ``background``, ``avatar_outfit``, ``text_overlay``,
        ``missing_assets`` flag, plus the original checklist fields.
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
        _GOAL_CLIP_TYPE = {
            "hook": "motion_graphic",
            "build_tension": "live_action",
            "reveal": "product_showcase",
            "body": "talking_head",
            "intro": "avatar_render",
            "social_proof": "testimonial_clip",
            "cta": "overlay_card",
        }
        _GOAL_PROPS = {
            "hook": ["logo_badge", "countdown_timer"],
            "build_tension": ["problem_prop", "contrast_visual"],
            "reveal": ["product_model", "lighting_rig"],
            "body": ["screen_capture", "diagram"],
            "intro": ["name_lower_third"],
            "social_proof": ["review_card", "star_rating"],
            "cta": ["cta_button", "url_card", "qr_code"],
        }
        _GOAL_OUTFITS = {
            "hook": "branded_casual",
            "body": "professional",
            "cta": "branded_casual",
        }

        checklist = []
        for scene in scenes:
            goal = scene.scene_goal
            background = _GOAL_BACKGROUNDS.get(goal, "neutral_studio")
            avatar_outfit = _GOAL_OUTFITS.get(goal, "natural")
            text_overlay = scene.cta_flag or goal in ("hook", "cta")
            video_clip_type = _GOAL_CLIP_TYPE.get(goal, "talking_head")
            prop_list = _GOAL_PROPS.get(goal, [])
            broll = _GOAL_BROLL.get(goal)

            # missing_assets flag: True when avatar not specified for scenes requiring it
            missing_assets = (
                avatar_id is None
                and goal in ("hook", "body", "intro", "social_proof", "cta")
            )

            checklist.append({
                "scene_index": scene.scene_index,
                "scene_goal": goal,
                "avatar_id": avatar_id,
                "background": background,
                "background_type": background,  # backward compat alias
                "avatar_pose": _GOAL_POSES.get(goal, "explaining"),
                "avatar_outfit": avatar_outfit,
                "overlay_text": text_overlay,
                "text_overlay": text_overlay,  # explicit manifest field
                "broll_category": broll,
                "video_clip_type": video_clip_type,
                "prop_list": prop_list,
                "missing_assets": missing_assets,
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
        conversion_rate: float | None = None,
        avg_watch_time: float | None = None,
    ) -> None:
        """Persist high-scoring scenes as reusable patterns."""
        if conversion_score < self._MIN_CONVERSION_SCORE:
            return
        from app.services.pattern_library import PatternLibrary
        from app.schemas.patterns import PatternMemoryIn

        lib = PatternLibrary()
        for scene in storyboard.scenes:
            payload: dict[str, Any] = {
                "platform": platform,
                "scene_goal": scene.scene_goal,
                "visual_type": scene.visual_type,
                "shot_hint": scene.shot_hint,
                "pacing_weight": scene.pacing_weight,
                "emotion": scene.emotion,
                "voice_direction": scene.voice_direction,
                "transition_hint": scene.transition_hint,
            }
            if conversion_rate is not None:
                payload["conversion_rate"] = conversion_rate
            if avg_watch_time is not None:
                payload["avg_watch_time"] = avg_watch_time

            pattern = PatternMemoryIn(
                pattern_type=self._PATTERN_TYPE,
                content_goal=content_goal,
                source_id=storyboard.storyboard_id,
                score=conversion_score,
                payload=payload,
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
    db: Any = None,
) -> float:
    """Return a pacing boost for hook scenes when top performers reward it.

    Queries ``top_hook_patterns()`` from the learning store and
    winning scenes from the pattern library.  Returns up to +0.15 when both
    sources confirm hook-heavy content wins on the given platform.
    """
    boost = 0.0
    try:
        top_hooks = learning_store.top_hook_patterns(platform=platform)
        if top_hooks:
            boost += 0.1
    except Exception:
        pass

    # Also check pattern library winning scenes for hook-type goals
    if db is not None:
        try:
            lib = ScenePatternLibrary()
            patterns = lib.get_top_patterns(db, platform=platform, scene_goal="hook", limit=3)
            if patterns:
                boost = min(boost + 0.05, 0.15)
        except Exception:
            pass

    return round(boost, 3)


# Scene goals that can benefit from outcome-informed pacing boosts.
# Each goal maps to its maximum allowed boost delta.
_SCENE_GOAL_MAX_BOOSTS: dict[str, float] = {
    "hook": 0.15,
    "reveal": 0.10,
    "cta": 0.12,
    "body": 0.08,
    "social_proof": 0.08,
    "build_tension": 0.07,
    "intro": 0.06,
}


def _derive_all_scene_pacing_boosts(
    learning_store: "PerformanceLearningEngine",
    platform: str | None,
    db: Any = None,
) -> dict[str, float]:
    """Return outcome-informed pacing boosts for all scene goal types.

    Phase 4.1: Now computes per-goal optimal pacing bucket by correlating
    pacing_weight with conversion_score from learning store records.

    For each goal, groups records by platform + scene_goal and computes mean
    conversion_score per pacing bucket: [0.6,1.0), [1.0,1.4), [1.4,1.8].
    The bucket with the highest mean becomes the optimal pacing target.

    Returns a ``{scene_goal: boost_delta}`` dict.  Missing goals default to 0.0.
    Requires ≥5 records per platform for outcome-driven analysis.
    """
    boosts: dict[str, float] = {}
    _MIN_RECORDS_FOR_OUTCOME = 5

    # ── Phase 4.1: Outcome-driven per-goal pacing analysis ─────────────────
    try:
        all_records = learning_store.all_records()
        platform_records = [
            r for r in all_records
            if (not platform) or r.get("platform") == platform
        ]
        if len(platform_records) >= _MIN_RECORDS_FOR_OUTCOME:
            # Pacing buckets: [0.6,1.0), [1.0,1.4), [1.4,1.8]
            buckets = [(0.6, 1.0), (1.0, 1.4), (1.4, 1.8)]
            # For each record that has pacing_weight + conversion_score
            goal_bucket_scores: dict[str, dict[str, list[float]]] = {}
            for r in platform_records:
                pacing_weight = float(r.get("pacing_weight") or 1.0)
                score = float(r.get("conversion_score", 0.0))
                # Infer scene_goal from template_family or default to "body"
                goal = str(r.get("scene_goal") or r.get("template_family") or "body")
                for lo, hi in buckets:
                    if lo <= pacing_weight < hi:
                        bucket_key = f"{lo:.1f}-{hi:.1f}"
                        if goal not in goal_bucket_scores:
                            goal_bucket_scores[goal] = {}
                        goal_bucket_scores[goal].setdefault(bucket_key, []).append(score)
                        break

            for goal, bucket_map in goal_bucket_scores.items():
                best_bucket: str | None = None
                best_mean = -1.0
                for bk, scores in bucket_map.items():
                    if len(scores) >= 2:  # require at least 2 samples
                        mean = sum(scores) / len(scores)
                        if mean > best_mean:
                            best_mean = mean
                            best_bucket = bk
                if best_bucket is not None and best_mean > 0.5:
                    # Boost this goal's pacing slightly
                    boosts[goal] = boosts.get(goal, 0.0) + 0.08
    except Exception:
        pass

    # ── Learning-store signal ───────────────────────────────────────────────
    try:
        top_hooks = learning_store.top_hook_patterns(platform=platform)
        if top_hooks:
            boosts["hook"] = boosts.get("hook", 0.0) + 0.10
    except Exception:
        pass

    try:
        top_ctas = learning_store.top_cta_patterns(platform=platform)
        if top_ctas:
            boosts["cta"] = boosts.get("cta", 0.0) + 0.08
    except Exception:
        pass

    try:
        top_templates = learning_store.top_template_families(platform=platform)
        if top_templates:
            # A strong template family implies the body/reveal/social_proof
            # scenes in winning templates should be paced more aggressively.
            for goal in ("body", "reveal", "social_proof", "build_tension"):
                boosts[goal] = boosts.get(goal, 0.0) + 0.05
    except Exception:
        pass

    # ── Pattern library signal (requires DB) ────────────────────────────────
    if db is not None:
        lib = ScenePatternLibrary()
        for goal, max_boost in _SCENE_GOAL_MAX_BOOSTS.items():
            try:
                patterns = lib.get_top_patterns(db, platform=platform, scene_goal=goal, limit=3)
                if patterns:
                    # Average the pacing_weight of winning patterns and derive
                    # a boost relative to the grammar default (1.0 baseline).
                    avg_pacing = sum(
                        float(p.get("pacing_weight") or 1.0) for p in patterns
                    ) / len(patterns)
                    pattern_boost = round(min((avg_pacing - 1.0) * 0.1, 0.05), 4)
                    if pattern_boost > 0:
                        boosts[goal] = boosts.get(goal, 0.0) + pattern_boost
            except Exception:
                pass

    # ── Cap each boost at its maximum ──────────────────────────────────────
    capped: dict[str, float] = {
        goal: round(min(v, _SCENE_GOAL_MAX_BOOSTS.get(goal, 0.10)), 4)
        for goal, v in boosts.items()
        if v > 0
    }
    return capped


class OutcomeInformedShotSelector:
    """Select biased shot types based on winning scenes history.

    ``select_shot_hint()`` queries the pattern library for winning scenes
    matching the given platform/niche/scene_goal and returns the most
    common shot type.  Falls back to a generic default when no history is
    available.
    """

    _FALLBACK_SHOT_HINTS: dict[str, str] = {
        "hook": "wide_shot",
        "body": "medium_shot",
        "cta": "close_up",
        "reveal": "product_close_up",
        "social_proof": "over_the_shoulder",
    }

    def select_shot_hint(
        self,
        platform: str,
        niche: str,
        scene_goal: str,
        db: Any = None,
    ) -> str:
        """Return a shot type hint biased by winning scene history.

        When ``db`` is provided the pattern library is queried.  Falls back to
        ``_FALLBACK_SHOT_HINTS`` when no history is available.
        """
        if db is not None:
            try:
                lib = ScenePatternLibrary()
                patterns = lib.get_top_patterns(
                    db,
                    platform=platform,
                    scene_goal=scene_goal,
                    limit=5,
                )
                if patterns:
                    # Count shot hints in winning patterns
                    shot_counts: dict[str, int] = {}
                    for p in patterns:
                        hint = p.get("shot_hint") or ""
                        if hint:
                            shot_counts[hint] = shot_counts.get(hint, 0) + 1
                    if shot_counts:
                        return max(shot_counts, key=lambda k: shot_counts[k])
            except Exception:
                pass

        return self._FALLBACK_SHOT_HINTS.get(scene_goal, "medium_shot")


# ---------------------------------------------------------------------------
# Cross-Scene Continuity Optimizer (Phase 2C)
# ---------------------------------------------------------------------------

class CrossSceneContinuityOptimizer:
    """Check visual, audio, and character continuity across scenes.

    ``optimize()`` inspects consecutive scenes for continuity violations and
    adds a ``continuity_violation`` flag to each scene's metadata dict.
    """

    def optimize(
        self,
        scenes: list["StoryboardScene"],
    ) -> list["StoryboardScene"]:
        """Flag continuity violations in the scenes list.

        Checks:
        - Visual type consistency: same visual_type on consecutive non-transition scenes
        - Audio mood consistency: emotion should not flip abruptly
        - Character continuity: cta_flag should not appear before any body scene

        Returns the (mutated) scenes list with ``continuity_violation`` added
        to each scene's metadata where applicable.
        """
        if not scenes:
            return scenes

        seen_body = False
        for i, scene in enumerate(scenes):
            violations: list[str] = []

            if scene.scene_goal == "body":
                seen_body = True

            # CTA before any body scene is a continuity issue
            if scene.cta_flag and not seen_body and scene.scene_goal != "hook":
                violations.append("cta_before_body")

            # Visual type should not jump between consecutive scenes
            if i > 0:
                prev = scenes[i - 1]
                if (
                    prev.visual_type and scene.visual_type
                    and prev.visual_type != scene.visual_type
                    and prev.scene_goal not in ("hook", "cta")
                    and scene.scene_goal not in ("hook", "cta")
                ):
                    violations.append(f"visual_type_mismatch:{prev.visual_type}->{scene.visual_type}")

                # Emotion continuity: avoid abrupt flip (e.g. excited -> somber)
                _OPPOSITE_EMOTIONS = {
                    "excited": "somber",
                    "somber": "excited",
                    "playful": "serious",
                    "serious": "playful",
                }
                if prev.emotion and scene.emotion:
                    if _OPPOSITE_EMOTIONS.get(prev.emotion) == scene.emotion:
                        violations.append(f"emotion_flip:{prev.emotion}->{scene.emotion}")

            # Inject violations into scene metadata
            meta: dict = dict(scene.metadata or {})
            if violations:
                meta["continuity_violation"] = violations
            scene.metadata = meta

        return scenes


# ---------------------------------------------------------------------------
# Episode Ladder Memory (Phase 3A)
# ---------------------------------------------------------------------------

class EpisodeLadderMemory:
    """Extended episode memory with series arc and plot hook tracking.

    ``save_episode()`` persists richer metadata than ``ContinuityPlanner``
    including ``series_arc``, ``character_flags``, and ``plot_hooks``.
    ``load_ladder()`` returns all episodes in order.
    ``blocks_hook()`` returns True when a hook has already been used in the
    last N episodes of the series (preventing repetition).
    """

    def save_episode(
        self,
        db: Any,
        series_id: str,
        episode_data: dict[str, Any],
    ) -> None:
        """Persist episode data with series arc, character flags, and plot hooks."""
        try:
            from app.models.episode_memory import EpisodeMemory

            row = EpisodeMemory(
                series_id=series_id,
                episode_index=episode_data.get("episode_index", 0),
                storyboard_id=episode_data.get("storyboard_id"),
                character_state={
                    "character_flags": episode_data.get("character_flags", []),
                    "series_arc": episode_data.get("series_arc", ""),
                    "plot_hooks": episode_data.get("plot_hooks", []),
                    **episode_data.get("character_state", {}),
                },
                open_loops=episode_data.get("open_loops", []),
                resolved_loops=episode_data.get("resolved_loops", []),
            )
            db.add(row)
            db.commit()
        except Exception:
            pass

    def load_ladder(self, db: Any, series_id: str) -> list[dict[str, Any]]:
        """Return all episodes for a series in chronological order."""
        try:
            from app.models.episode_memory import EpisodeMemory

            rows = (
                db.query(EpisodeMemory)
                .filter(EpisodeMemory.series_id == series_id)
                .order_by(EpisodeMemory.episode_index.asc())
                .all()
            )
            return [
                {
                    "series_id": row.series_id,
                    "episode_index": row.episode_index,
                    "storyboard_id": row.storyboard_id,
                    "character_state": row.character_state or {},
                    "open_loops": row.open_loops or [],
                    "resolved_loops": row.resolved_loops or [],
                    "series_arc": (row.character_state or {}).get("series_arc", ""),
                    "character_flags": (row.character_state or {}).get("character_flags", []),
                    "plot_hooks": (row.character_state or {}).get("plot_hooks", []),
                }
                for row in rows
            ]
        except Exception:
            return []

    def blocks_hook(
        self,
        db: Any,
        series_id: str,
        hook: str,
        last_n: int = 3,
    ) -> bool:
        """Return True when ``hook`` was used in the last ``last_n`` episodes."""
        ladder = self.load_ladder(db, series_id)
        recent = ladder[-last_n:] if len(ladder) >= last_n else ladder
        for ep in recent:
            if hook in ep.get("plot_hooks", []):
                return True
        return False


# ---------------------------------------------------------------------------
# Scene Memory Index (Phase 3A)
# ---------------------------------------------------------------------------

class SceneMemoryIndex:
    """Query whether a scene configuration has been recently used in a series.

    ``has_scene_been_used()`` returns True when a scene with the given
    ``scene_goal`` and ``visual_type`` appears in the last ``last_n`` episodes,
    preventing content repetition.
    """

    def has_scene_been_used(
        self,
        db: Any,
        series_id: str,
        scene_goal: str,
        visual_type: str,
        last_n: int = 3,
    ) -> bool:
        """Return True when the scene combination appeared in the last N episodes."""
        try:
            from app.services.pattern_library import PatternLibrary
            from app.models.episode_memory import EpisodeMemory

            rows = (
                db.query(EpisodeMemory)
                .filter(EpisodeMemory.series_id == series_id)
                .order_by(EpisodeMemory.episode_index.desc())
                .limit(last_n)
                .all()
            )
            for row in rows:
                storyboard_id = row.storyboard_id
                if not storyboard_id:
                    continue
                # Check pattern library for scenes from this storyboard
                lib = PatternLibrary()
                patterns = lib.list(db, pattern_type="scene_pattern")
                for p in patterns:
                    if p.source_id == storyboard_id:
                        payload: dict = p.payload or {}
                        if (
                            payload.get("scene_goal") == scene_goal
                            and payload.get("visual_type") == visual_type
                        ):
                            return True
        except Exception:
            pass
        return False
