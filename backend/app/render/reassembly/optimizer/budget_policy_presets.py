from __future__ import annotations

from typing import Dict, Union


BUDGET_POLICY_PRESETS: Dict[str, Dict[str, Union[float, bool]]] = {
    "cheap": {
        "max_rebuild_cost": 15.0,
        "max_rebuild_time_sec": 180.0,
        "allow_budget_downgrade": True,
        "include_optional_rebuilds": False,
    },
    "balanced": {
        "max_rebuild_cost": 50.0,
        "max_rebuild_time_sec": 600.0,
        "allow_budget_downgrade": True,
        "include_optional_rebuilds": False,
    },
    "quality": {
        "max_rebuild_cost": 150.0,
        "max_rebuild_time_sec": 1800.0,
        "allow_budget_downgrade": False,
        "include_optional_rebuilds": True,
    },
    "emergency": {
        "max_rebuild_cost": 8.0,
        "max_rebuild_time_sec": 90.0,
        "allow_budget_downgrade": True,
        "include_optional_rebuilds": False,
    },
}


def resolve_budget_policy(
    policy: Union[str, None],
) -> Dict[str, Union[str, float, bool]]:
    """Resolve a named budget policy to its parameter dict.

    Unknown policy names fall back to ``"balanced"``.

    Args:
        policy: One of ``"cheap"``, ``"balanced"``, ``"quality"``,
            ``"emergency"``, or ``None`` (defaults to ``"balanced"``).

    Returns:
        Dict containing ``policy`` (the resolved name) plus all budget
        parameters from :data:`BUDGET_POLICY_PRESETS`.
    """
    key = (policy or "balanced").lower().strip()
    if key not in BUDGET_POLICY_PRESETS:
        key = "balanced"
    return {"policy": key, **BUDGET_POLICY_PRESETS[key]}
