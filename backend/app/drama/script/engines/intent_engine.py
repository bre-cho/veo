"""intent_engine — classifies the psychological intent of a subtext item.

Converts subtext hidden_intent labels into action intents that drive the
narration tone and word choice.

Two public API functions:
- ``classify_intent`` — used by the single-scene engine; broader mapping.
- ``classify_sentence_intent`` — used by the multi-scene engine; focused on
  the six strongest dramatic hidden-intent archetypes.
"""
from __future__ import annotations

from typing import Optional

_INTENT_MAP = {
    "control": "dominate",
    "fear": "destabilize",
    "lie": "mislead",
    "manipulation": "mislead",
    "guilt": "destabilize",
    "envy": "undermine",
    "loyalty": "reinforce",
    "love": "connect",
    "grief": "lament",
    "shame": "expose",
    # Extended archetypes (also used by next-level engine)
    "betrayal": "trap",
    "secret": "tease",
    "loss": "emotional_pull",
}

_DEFAULT_INTENT = "hint"


def classify_intent(hidden_intent: Optional[str]) -> str:
    """Map a hidden_intent label to an action intent (single-scene engine)."""
    if not hidden_intent:
        return _DEFAULT_INTENT
    return _INTENT_MAP.get(hidden_intent.lower(), _DEFAULT_INTENT)


def classify_sentence_intent(hidden_intent: Optional[str]) -> str:
    """Map a hidden_intent label to an action intent (multi-scene engine).

    Uses the same ``_INTENT_MAP`` as ``classify_intent``, covering all
    hidden-intent archetypes including the drama-specific ones added for the
    next-level engine (betrayal → trap, secret → tease, loss → emotional_pull).
    """
    if not hidden_intent:
        return _DEFAULT_INTENT
    return _INTENT_MAP.get(hidden_intent.lower(), _DEFAULT_INTENT)
