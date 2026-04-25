"""intent_engine — classifies the psychological intent of a subtext item.

Converts subtext hidden_intent labels into action intents that drive the
narration tone and word choice.
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
}

_DEFAULT_INTENT = "hint"


def classify_intent(hidden_intent: Optional[str]) -> str:
    """Map a hidden_intent label to an action intent."""
    if not hidden_intent:
        return _DEFAULT_INTENT
    return _INTENT_MAP.get(hidden_intent.lower(), _DEFAULT_INTENT)
