"""factory_state – pipeline stage definitions and run state machine.

The factory pipeline is fixed at 12 stages (in order).  A FactoryRun
progresses through them sequentially; individual stages may be retried or
skipped based on policy, but the order is immutable.
"""
from __future__ import annotations

from enum import Enum


class FactoryStage(str, Enum):
    INTAKE = "INTAKE"
    CONTEXT_LOAD = "CONTEXT_LOAD"
    SKILL_ROUTE = "SKILL_ROUTE"
    SCRIPT_PLAN = "SCRIPT_PLAN"
    SCENE_BUILD = "SCENE_BUILD"
    AVATAR_AUDIO_BUILD = "AVATAR_AUDIO_BUILD"
    RENDER_PLAN = "RENDER_PLAN"
    EXECUTE_RENDER = "EXECUTE_RENDER"
    QA_VALIDATE = "QA_VALIDATE"
    SEO_PACKAGE = "SEO_PACKAGE"
    PUBLISH = "PUBLISH"
    TELEMETRY_LEARN = "TELEMETRY_LEARN"


STAGE_ORDER: list[FactoryStage] = list(FactoryStage)

STAGE_INDEX: dict[FactoryStage, int] = {s: i for i, s in enumerate(STAGE_ORDER)}


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class GateResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


class GateAction(str, Enum):
    NONE = "none"
    BLOCK = "block"
    RETRY = "retry"
    DOWNGRADE = "downgrade"
    HUMAN_REVIEW = "human_review"


def next_stage(current: FactoryStage) -> FactoryStage | None:
    """Return the stage that follows *current*, or None if at end."""
    idx = STAGE_INDEX[current]
    if idx + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[idx + 1]


def percent_complete(current: FactoryStage, stage_status: StageStatus) -> int:
    """Compute integer 0-100 progress based on current stage."""
    idx = STAGE_INDEX[current]
    total = len(STAGE_ORDER)
    if stage_status == StageStatus.DONE:
        return int((idx + 1) / total * 100)
    return int(idx / total * 100)
