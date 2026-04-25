"""factory_validator – quality gate evaluator for the factory pipeline.

Each stage adapter calls ``evaluate_gate`` before marking itself complete.
The validator writes a FactoryQualityGate record and returns the action
the orchestrator should take (none / block / retry / downgrade / human_review).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.factory.factory_policy import gate_is_blocking
from app.factory.factory_state import GateAction, GateResult
from app.models.factory_run import FactoryQualityGate

logger = logging.getLogger(__name__)


def evaluate_gate(
    db: Session,
    run_id: str,
    stage_name: str,
    gate_name: str,
    score: int | None,
    threshold: int | None,
    detail: str | None = None,
    policy_mode: str = "production",
) -> GateAction:
    """Evaluate a single quality gate, persist the result, and return the action.

    Logic
    -----
    - If score is None the gate is skipped (result = skip, action = none).
    - If score >= threshold → pass.
    - If score < threshold → fail; action depends on policy.
    """
    now = datetime.now(timezone.utc)

    if score is None or threshold is None:
        result = GateResult.SKIP
        action = GateAction.NONE
    elif score >= threshold:
        result = GateResult.PASS
        action = GateAction.NONE
    else:
        result = GateResult.FAIL
        if gate_is_blocking(gate_name, policy_mode):
            action = GateAction.BLOCK
        else:
            action = GateAction.NONE

    gate = FactoryQualityGate(
        run_id=run_id,
        stage_name=stage_name,
        gate_name=gate_name,
        result=result.value,
        score=score,
        threshold=threshold,
        action_taken=action.value,
        detail=detail,
        evaluated_at=now,
    )
    db.add(gate)
    db.commit()

    logger.debug(
        "Quality gate %s/%s: result=%s action=%s score=%s threshold=%s",
        stage_name, gate_name, result.value, action.value, score, threshold,
    )
    return action
