"""script_engine — orchestrator that assembles the full voiceover script.

Pipeline:
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
