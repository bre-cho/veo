"""LLM client: OpenRouter chat completions with function calling + RAG.

Wraps the OpenRouter `/chat/completions` endpoint via httpx.
Supports:
- RAG-augmented system prompt injection.
- Multi-turn function-calling loop (capped by config).
- Returns the final assistant text reply and a trace of tool calls made.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.llm.function_registry import TOOL_REGISTRY
from app.services.llm.function_executor import execute_tool
from app.services.rag.retrieval_service import retrieve_and_assemble

logger = logging.getLogger(__name__)

_BASE = "https://openrouter.ai/api/v1"
_TIMEOUT = 60


# ── Low-level API call ────────────────────────────────────────────────────────


def _chat_completion(
    api_key: str,
    model: str,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Single round-trip to OpenRouter /chat/completions."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    resp = httpx.post(
        f"{_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ── Multi-turn chat with function calling ─────────────────────────────────────


def chat_with_rag(
    db: Session,
    *,
    user_message: str,
    api_key: str,
    model: str = "openai/gpt-4o-mini",
    conversation_history: list[dict] | None = None,
    top_k: int | None = None,
    enable_tools: bool = True,
    actor: str = "api-user",
) -> dict[str, Any]:
    """Run a RAG-augmented chat turn with optional function calling.

    Parameters
    ----------
    db                   : SQLAlchemy session for tool execution.
    user_message         : The latest user question.
    api_key              : OpenRouter API key.
    model                : OpenRouter model identifier.
    conversation_history : Previous messages (modified in-place).
    top_k                : Override RAG retrieval count.
    enable_tools         : Set False to disable function calling.
    actor                : Label for tool-call audit logging.

    Returns
    -------
    dict with keys: reply (str), tool_calls (list), context_sources (list),
                    messages (list of all messages this turn).
    """
    top_k = top_k or settings.rag_top_k
    history: list[dict] = list(conversation_history or [])

    # Build system prompt with RAG context.
    rag_results, context_str = retrieve_and_assemble(user_message, top_k=top_k)
    system_content = settings.rag_llm_system_prompt
    if context_str:
        system_content = f"{system_content}\n\n## Context\n\n{context_str}"

    messages: list[dict] = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tools = TOOL_REGISTRY if (enable_tools and settings.llm_function_calling_enabled) else None
    max_tool_calls = settings.llm_max_tool_calls_per_request
    tool_calls_trace: list[dict] = []

    for _iteration in range(max_tool_calls + 1):
        response = _chat_completion(api_key, model, messages, tools=tools)
        choice = response["choices"][0]
        assistant_msg = choice["message"]
        messages.append(assistant_msg)

        finish_reason = choice.get("finish_reason", "stop")
        if finish_reason != "tool_calls" or not assistant_msg.get("tool_calls"):
            break

        # Execute tool calls.
        tool_results: list[dict] = []
        for tc in assistant_msg.get("tool_calls", []):
            fn_name = tc["function"]["name"]
            fn_args = tc["function"].get("arguments", "{}")
            result = execute_tool(db, tool_name=fn_name, tool_args=fn_args, audit_actor=actor)
            tool_calls_trace.append({"tool": fn_name, "args": fn_args, "result": result})
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result),
            })

        messages.extend(tool_results)

    reply_content = assistant_msg.get("content") or ""

    return {
        "reply": reply_content,
        "tool_calls": tool_calls_trace,
        "context_sources": [r.source for r in rag_results],
        "messages": messages,
    }
