"""factory_context – runtime context object passed between factory stages.

The FactoryContext is a lightweight in-memory bag-of-values that accumulates
outputs as the pipeline progresses.  It is *not* persisted directly; the
FactoryOrchestrator writes durable records via the ORM models.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class FactoryContext:
    """Carries state across all 12 pipeline stages for a single factory run."""

    # Identifiers
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str | None = None

    # Input
    input_type: str = "topic"           # topic | script | avatar | series
    input_topic: str | None = None
    input_script: str | None = None
    input_avatar_id: str | None = None
    input_series_id: str | None = None

    # Stage outputs (populated progressively)
    context_data: dict[str, Any] = field(default_factory=dict)   # CONTEXT_LOAD
    selected_skill: str | None = None                             # SKILL_ROUTE
    script_plan: dict[str, Any] | None = None                    # SCRIPT_PLAN
    scenes: list[dict[str, Any]] = field(default_factory=list)   # SCENE_BUILD
    avatar_id: str | None = None                                  # AVATAR_AUDIO_BUILD
    audio_url: str | None = None                                  # AVATAR_AUDIO_BUILD
    render_plan: dict[str, Any] | None = None                    # RENDER_PLAN
    render_job_id: str | None = None                              # EXECUTE_RENDER
    qa_passed: bool | None = None                                 # QA_VALIDATE
    seo_package: dict[str, Any] | None = None                    # SEO_PACKAGE
    publish_result: dict[str, Any] | None = None                 # PUBLISH
    learning_memory: dict[str, Any] | None = None                # TELEMETRY_LEARN

    # Final outputs
    output_video_url: str | None = None
    output_thumbnail_url: str | None = None

    # Policy / budget
    policy_mode: str = "production"
    budget_cents: int | None = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Arbitrary extras
    extras: dict[str, Any] = field(default_factory=dict)

    def set_stage_output(self, stage: str, data: Any) -> None:
        """Store the output of a completed stage in extras for audit."""
        self.extras[f"stage_output_{stage}"] = data
