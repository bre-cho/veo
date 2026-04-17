"""Pydantic schemas for RAG chat API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class RagChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    enable_tools: bool = Field(default=True)
    model: str | None = Field(default=None)


class RagChatResponse(BaseModel):
    reply: str
    context_sources: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class IndexRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = Field(default="dynamic")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    ok: bool
    chunks_indexed: int
    source: str


class RebuildIndexResponse(BaseModel):
    ok: bool
    chunks_indexed: int = 0
    reason: str | None = None
