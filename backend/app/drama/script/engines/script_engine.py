"""script_engine — orchestrator that assembles the full voiceover script.

# Kept for backward-compat: ScriptToRenderAdapter imports this constant.
DEFAULT_VOICE_TONE = "documentary, calm"


Contains two engines:

``ScriptEngine`` (single-scene)
    Brain Layer output (ScriptRequest)
        → Hook Engine      (opening hook + strategy)
        → Narration Engine (subtext → narration lines with intent)
        → Tension Curve    (scene structure)
        → Segment Assembly
        → Binge-Chain Memory callbacks
        → Pacing Engine    (duration_sec per segment)
        → Retention Engine (loops + score)
        → Voice Style      (global + per-segment directives)
        → ScriptOutput

``NextLevelScriptEngine`` (multi-scene)
    Brain Layer output (NextLevelScriptRequest)
        → Decision Engine  (story strategy)
        → A/B Hook Engine  (variants + best-hook selection)
        → Multi-Scene Engine (scene sequence for full episode)
        → Intent Engine    (per-scene sentence intent)
        → Segment Assembly
        → Binge-Chain Engine (open-loop callbacks)
        → Voice Acting Engine (per-segment TTS directives)
        → Script Scoring Engine (5-axis scorecard)
        → NextLevelScriptOutput
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.drama.script.engines.hook_engine import generate_hook
from app.drama.script.engines.narration_engine import generate_narration
from app.drama.script.engines.pacing_engine import apply_pacing
from app.drama.script.engines.retention_engine import (
    inject_retention_hooks,
    optimize_retention,
)
from app.drama.script.engines.voice_style_engine import (
    apply_voice_pattern,
    select_voice_style,
)
from app.drama.script.schemas.script_output import ScriptOutput, ScriptSegment, VoiceDirective
from app.drama.script.schemas.script_request import ScriptRequest

logger = logging.getLogger(__name__)


def _build_tension_curve(drama_state: Dict[str, Any]) -> List[str]:
    """Map tension score to a narrative beat sequence."""
    score: float = float(drama_state.get("tension_score", 0))
    if score > 80:
        return ["hook", "escalation", "reveal", "cliffhanger"]
    if score > 60:
        return ["hook", "escalation", "reveal", "escalation"]
    if score > 40:
        return ["hook", "setup", "reveal", "context"]
    return ["setup", "context", "reveal"]


class ScriptEngine:
    """Orchestrates all sub-engines to produce a ``ScriptOutput``."""

    def generate(self, req: ScriptRequest) -> ScriptOutput:
        drama = req.drama_state.model_dump()
        ctx = req.scene_context.model_dump()
        subtext = [s.model_dump() for s in req.subtext_map]
        memories = [m.model_dump() for m in req.memory_traces]

        # 1. Hook
        hook, hook_strategy = generate_hook(drama, ctx)

        # 2. Narration lines from subtext/memory
        narration = generate_narration(subtext, memories)

        # 3. Scene structure
        structure = _build_tension_curve(drama)

        # 4. Assemble segments
        raw_segments: List[Dict[str, Any]] = []
        for i, purpose in enumerate(structure):
            if i == 0 and purpose == "hook":
                text = hook
            elif i < len(narration):
                text = narration[i]["text"]
            elif narration:
                text = narration[len(narration) - 1]["text"]
            else:
                text = "..."

            intent = narration[i]["intent"] if i < len(narration) else "hint"

            raw_segments.append(
                {
                    "id": i,
                    "purpose": purpose,
                    "text": text,
                    "subtext": "derived",
                    "emotion": "tension",
                    "intent": intent,
                }
            )

        # 5. Binge-chain memory callbacks
        if req.open_loops:
            raw_segments.append(
                {
                    "id": len(raw_segments),
                    "purpose": "callback",
                    "text": "Remember what happened earlier? This is where it connects.",
                    "subtext": "continuity",
                    "emotion": "recognition",
                    "intent": "hint",
                }
            )

        # 6. Pacing
        raw_segments = apply_pacing(raw_segments)

        # 7. Voice directives
        tension = drama.get("tension_score", 0)
        for seg in raw_segments:
            seg["voice"] = apply_voice_pattern(seg, float(tension))

        # 8. Build typed segments
        segments = [
            ScriptSegment(
                id=s["id"],
                purpose=s["purpose"],
                text=s["text"],
                subtext=s.get("subtext"),
                emotion=s.get("emotion"),
                intent=s.get("intent"),
                duration_sec=s.get("duration_sec", 4.0),
                voice=VoiceDirective(**s.get("voice", {})),
            )
            for s in raw_segments
        ]

        # 9. Retention loop
        full_script = " ".join(s.text for s in segments)
        raw_hooks = inject_retention_hooks(full_script)
        retention_hooks, retention_score = optimize_retention(full_script, raw_hooks)

        # 10. Voice style
        voice_style = select_voice_style(drama)

        logger.debug(
            "ScriptEngine: project=%s scene=%s tension=%.1f strategy=%s segments=%d retention=%d",
            req.project_id,
            req.scene_id,
            tension,
            hook_strategy,
            len(segments),
            retention_score,
        )

        return ScriptOutput(
            project_id=req.project_id,
            scene_id=req.scene_id,
            title="Generated Scene",
            hook=hook,
            segments=segments,
            full_script=full_script,
            pacing_map=[s.model_dump() for s in segments],
            retention_hooks=retention_hooks,
            retention_score=retention_score,
            voice_style=voice_style,
            hook_strategy=hook_strategy,
        )


# ---------------------------------------------------------------------------
# Next-Level (multi-scene) engine
# ---------------------------------------------------------------------------

class NextLevelScriptEngine:
    """Cinematic Script Intelligence Engine for multi-scene episodes.

    Upgrades from single-scene ``ScriptEngine`` by adding:
    - Multi-scene sequence planning (``multi_scene_engine``)
    - A/B hook variant generation and best-hook selection (``ab_test_engine``)
    - Per-scene intent classification (``intent_engine``)
    - Binge-chain callback injection (``binge_chain_engine``)
    - Full voice-acting directives per segment (``voice_acting_engine``)
    - 5-axis script quality scorecard (``script_scoring_engine``)
    """

    def generate(self, req: Any) -> Any:
        """Generate a cinematic multi-scene script from a ``NextLevelScriptRequest``.

        Args:
            req: A ``NextLevelScriptRequest`` instance.

        Returns:
            A ``NextLevelScriptOutput`` instance.
        """
        from app.drama.script.engines.ab_test_engine import (
            generate_hook_variants,
            select_best_hook,
        )
        from app.drama.script.engines.binge_chain_engine import inject_binge_callbacks
        from app.drama.script.engines.decision_engine import select_story_strategy
        from app.drama.script.engines.intent_engine import classify_sentence_intent
        from app.drama.script.engines.multi_scene_engine import build_scene_sequence
        from app.drama.script.engines.script_scoring_engine import score_script
        from app.drama.script.engines.voice_acting_engine import apply_voice_acting
        from app.drama.script.schemas.next_level_script_output import (
            NextLevelScriptOutput,
            NextLevelScriptSegment,
            ScriptScorecard,
            VoiceActingMeta,
        )

        drama: Dict[str, Any] = (
            req.drama_state
            if isinstance(req.drama_state, dict)
            else req.drama_state.model_dump()
        )
        scene_contexts: List[Dict[str, Any]] = req.scene_contexts or []
        open_loops: List[Dict[str, Any]] = req.open_loops or []
        tension: float = float(drama.get("tension_score", 0))

        # 1. Story strategy (uses first scene context as anchor)
        first_scene = scene_contexts[0] if scene_contexts else {}
        strategy = select_story_strategy(drama, first_scene)

        # 2. A/B hook variants → select best
        hook_versions = generate_hook_variants(strategy)
        selected_hook = select_best_hook(hook_versions)

        # 3. Build multi-scene sequence
        scene_sequence = build_scene_sequence(
            scene_contexts,
            req.target_duration_min,
        )

        # 4. Opening hook segment
        raw_segments: List[Dict[str, Any]] = [
            {
                "scene_id": "opening",
                "purpose": "hook",
                "text": selected_hook,
                "subtext": "opening psychological trigger",
                "intent": "capture_attention",
                "emotion": "curiosity",
                "duration_sec": 8,
            }
        ]

        # 5. Per-scene segments
        for scene in scene_sequence:
            context: Dict[str, Any] = scene["context"]
            hidden_intent: str = context.get("hidden_intent", "secret")
            intent = classify_sentence_intent(hidden_intent)
            text = self._generate_scene_line(scene["purpose"], context, intent)

            raw_segments.append(
                {
                    "scene_id": scene["scene_id"],
                    "purpose": scene["purpose"],
                    "text": text,
                    "subtext": context.get("hidden_conflict", "unknown tension"),
                    "intent": intent,
                    "emotion": context.get("emotion", "tension"),
                    "duration_sec": scene["duration_sec"],
                }
            )

        # 6. Binge-chain callbacks
        raw_segments = inject_binge_callbacks(raw_segments, open_loops)

        # 7. Voice acting per segment
        for seg in raw_segments:
            seg["voice"] = apply_voice_acting(seg, tension)

        # 8. Full script text
        full_script = "\n\n".join(seg["text"] for seg in raw_segments)

        # 9. Score
        score_dict = score_script(full_script, raw_segments)

        # 10. Build typed segments (enumerate to assign stable int ids)
        typed_segments = [
            NextLevelScriptSegment(
                id=i,
                scene_id=s["scene_id"],
                purpose=s["purpose"],
                text=s["text"],
                subtext=s.get("subtext", ""),
                intent=s.get("intent", "hint"),
                emotion=s.get("emotion", "tension"),
                duration_sec=int(s.get("duration_sec", 8)),
                voice=VoiceActingMeta(**s.get("voice", {})),
            )
            for i, s in enumerate(raw_segments)
        ]

        logger.debug(
            "NextLevelScriptEngine: project=%s episode=%s strategy=%s "
            "scenes=%d tension=%.1f score=%s",
            req.project_id,
            req.episode_id,
            strategy,
            len(scene_sequence),
            tension,
            score_dict,
        )

        return NextLevelScriptOutput(
            project_id=req.project_id,
            episode_id=req.episode_id,
            title="Generated Cinematic Script",
            selected_variant=selected_hook,
            hook_versions=hook_versions,
            full_script=full_script,
            segments=typed_segments,
            pacing_map=[
                {
                    "scene_id": s["scene_id"],
                    "purpose": s["purpose"],
                    "duration_sec": s["duration_sec"],
                }
                for s in raw_segments
            ],
            retention_hooks=[
                "But that was only the beginning.",
                "The next part changes everything.",
                "And this is where the story stops making sense.",
            ],
            open_loop_map=open_loops,
            score=ScriptScorecard(**score_dict),
            hook_strategy=strategy,
        )

    @staticmethod
    def _generate_scene_line(
        purpose: str,
        context: Dict[str, Any],
        intent: str,
    ) -> str:
        """Generate a single narration line for a scene based on its purpose."""
        if purpose == "reveal":
            return "And then, one detail exposed what everyone had missed."

        if purpose == "escalation":
            return "What looked like a small mistake was becoming something much bigger."

        if purpose == "cliffhanger":
            return "But the truth was still buried deeper than anyone expected."

        return "At first, everything seemed ordinary."
