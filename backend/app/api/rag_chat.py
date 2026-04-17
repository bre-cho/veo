"""RAG chat API endpoints.

Phase 1: read-only, knowledge-base Q&A + optional function calling.

Endpoints
---------
POST /api/v1/rag/chat            – Chat with RAG context.
POST /api/v1/rag/index           – Add a text passage to the live index.
POST /api/v1/rag/rebuild-index   – Rebuild index from the docs/ directory.
GET  /api/v1/rag/status          – Index health / chunk count.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.rag import (
    IndexRequest,
    IndexResponse,
    RagChatRequest,
    RagChatResponse,
    RebuildIndexResponse,
)
from app.services.ai_engine_service import get_ai_engine_config
from app.services.rag.retrieval_service import (
    add_text_to_index,
    build_index_from_directory,
    _get_store,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


def _require_api_key(db: Session) -> str:
    """Fetch the OpenRouter API key or raise 503."""
    cfg = get_ai_engine_config(db)
    if not cfg.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. "
                   "Set it via PATCH /api/v1/ai-engine/config.",
        )
    return cfg.openrouter_api_key


@router.post("/chat", response_model=RagChatResponse)
async def rag_chat(payload: RagChatRequest, db: Session = Depends(get_db)):
    """RAG-augmented chat with optional LLM function calling."""
    if not settings.rag_enabled:
        raise HTTPException(status_code=503, detail="RAG is disabled via RAG_ENABLED=false")

    api_key = _require_api_key(db)
    model = payload.model or get_ai_engine_config(db).default_model

    from app.services.llm.llm_client import chat_with_rag

    try:
        result = chat_with_rag(
            db,
            user_message=payload.message,
            api_key=api_key,
            model=model,
            conversation_history=[m.model_dump() for m in payload.history],
            top_k=payload.top_k,
            enable_tools=payload.enable_tools,
        )
    except Exception as exc:
        logger.exception("RAG chat error: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    return RagChatResponse(
        reply=result["reply"],
        context_sources=result.get("context_sources", []),
        tool_calls=result.get("tool_calls", []),
    )


@router.post("/index", response_model=IndexResponse)
async def add_to_index(payload: IndexRequest):
    """Add a raw text passage to the live RAG index."""
    n = add_text_to_index(
        payload.text,
        source=payload.source,
        metadata=payload.metadata,
    )
    return IndexResponse(ok=True, chunks_indexed=n, source=payload.source)


@router.post("/rebuild-index", response_model=RebuildIndexResponse)
async def rebuild_index():
    """Rebuild the RAG index from the docs/ directory."""
    docs_root = Path(settings.rag_docs_root)
    result = build_index_from_directory(
        docs_root,
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
        store_path=settings.rag_vector_store_path,
        backend=settings.rag_embedding_backend,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("reason", "Index build failed"))
    return RebuildIndexResponse(ok=True, chunks_indexed=result.get("chunks_indexed", 0))


@router.get("/status")
async def rag_status():
    """Return index health: chunk count and embedding backend."""
    store = _get_store()
    return {
        "ok": True,
        "chunk_count": len(store),
        "embedding_backend": settings.rag_embedding_backend,
        "rag_enabled": settings.rag_enabled,
    }
