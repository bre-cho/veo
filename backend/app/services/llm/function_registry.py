"""Whitelisted function (tool) definitions for LLM function calling.

Only read-only, safe backend actions are registered here.
Each tool has:
- A JSON-Schema description used in the OpenRouter chat API.
- An ``execute`` callable wired in ``function_executor.py``.

Extend the ``TOOL_REGISTRY`` list to add new tools; they are automatically
included in the LLM request.
"""
from __future__ import annotations

from typing import Any

# ── Tool definitions (OpenAI-compatible JSON schema) ─────────────────────────

TOOL_REGISTRY: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_job_status",
            "description": (
                "Return the current status and scene-level summary for a render job. "
                "Use this when the user asks about the state, progress, or health of a specific render job."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The UUID of the render job.",
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recent_jobs",
            "description": (
                "Return a list of the most recently created or updated render jobs. "
                "Use when the user asks for an overview of current or recent activity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of jobs to return (1–50). Defaults to 10.",
                        "default": 10,
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (queued, processing, done, failed). Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_metrics_snapshot",
            "description": (
                "Return a high-level metrics snapshot: queued/processing/done/failed job counts, "
                "open incident count, and critical incident count."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_timeline",
            "description": "Return the timeline events for a render job.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The UUID of the render job.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to return (1–200). Defaults to 50.",
                        "default": 50,
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_decision_engine_recommendations",
            "description": (
                "Run the decision engine policy and return current recommendations "
                "(e.g. scale worker, switch provider, block release)."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# Whitelist of tool names that are permitted.  Any name not in this set will
# be rejected by the executor even if injected via prompt manipulation.
ALLOWED_TOOL_NAMES: frozenset[str] = frozenset(
    t["function"]["name"] for t in TOOL_REGISTRY
)
