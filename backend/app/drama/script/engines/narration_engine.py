"""narration_engine — converts subtext map + memory traces into narration lines.

Each line carries an ``intent`` label so the voice acting engine can apply the
correct performance directive.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.drama.script.engines.intent_engine import classify_intent

_CONTROL_LINES = [
    "He wasn't asking a question. He was setting the rules.",
    "That smile meant one thing: he already knew the answer.",
]
_FEAR_LINES = [
    "And that's when everything started to feel… wrong.",
    "Something in the air had shifted. No one said it out loud.",
]
_LIE_LINES = [
    "Every word was carefully chosen. Not one of them was true.",
    "She said exactly what they needed to hear. That was the problem.",
]
_DEFAULT_LINES = [
    "Something didn't add up.",
    "There was more to this than anyone was letting on.",
]

_INTENT_LINES: Dict[str, List[str]] = {
    "control": _CONTROL_LINES,
    "dominate": _CONTROL_LINES,
    "fear": _FEAR_LINES,
    "destabilize": _FEAR_LINES,
    "lie": _LIE_LINES,
    "mislead": _LIE_LINES,
}


def _pick_line(intent: str, index: int) -> str:
    lines = _INTENT_LINES.get(intent, _DEFAULT_LINES)
    return lines[index % len(lines)]


def generate_narration(
    subtext_map: List[Dict[str, Any]],
    memory_traces: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Return a list of ``{text, intent}`` dicts derived from subtext/memory."""
    lines: List[Dict[str, str]] = []

    for i, item in enumerate(subtext_map):
        hidden = item.get("hidden_intent")
        intent = classify_intent(hidden)
        text = _pick_line(intent, i)
        lines.append({"text": text, "intent": intent})

    # Supplement from memory traces if narration is sparse
    for i, trace in enumerate(memory_traces):
        if len(lines) >= 6:
            break
        summary = trace.get("summary")
        if summary:
            lines.append({"text": summary, "intent": "hint"})

    if not lines:
        lines.append({"text": _DEFAULT_LINES[0], "intent": "hint"})

    return lines
