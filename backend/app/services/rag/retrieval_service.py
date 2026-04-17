"""RAG retrieval service.

Manages:
- A singleton VectorStore + TFIDFEmbedder.
- Index building from the docs/ directory.
- Query-time retrieval of the top-k most relevant passages.
- Context assembly for LLM prompts.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.services.rag.document_chunker import DocumentChunk, chunk_directory, chunk_text
from app.services.rag.embedder import BaseEmbedder, TFIDFEmbedder, get_embedder
from app.services.rag.vector_store import SearchResult, VectorStore

logger = logging.getLogger(__name__)


# ── Singleton state ───────────────────────────────────────────────────────────

_store: VectorStore | None = None
_embedder: BaseEmbedder | None = None


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def _get_embedder(backend: str = "tfidf", **kwargs) -> BaseEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = get_embedder(backend, **kwargs)
    return _embedder


def reset_index() -> None:
    """Tear down singletons (used in tests)."""
    global _store, _embedder
    _store = None
    _embedder = None


# ── Index building ────────────────────────────────────────────────────────────


def build_index_from_directory(
    docs_root: str | Path,
    *,
    chunk_size: int = 400,
    overlap: int = 80,
    store_path: str | None = None,
    backend: str = "tfidf",
    embedder_kwargs: dict | None = None,
) -> dict[str, Any]:
    """Chunk all docs in *docs_root*, embed, and populate the vector store.

    Returns a summary dict.
    """
    root = Path(docs_root)
    if not root.exists():
        return {"ok": False, "reason": f"docs_root not found: {root}"}

    chunks = list(chunk_directory(root, chunk_size=chunk_size, overlap=overlap))
    if not chunks:
        return {"ok": False, "reason": "No documents found to index"}

    emb = _get_embedder(backend, **(embedder_kwargs or {}))
    if isinstance(emb, TFIDFEmbedder):
        emb.fit([c.text for c in chunks])

    store = _get_store()
    store.clear()
    vectors = emb.embed([c.text for c in chunks])
    store.add(chunks, vectors)

    if store_path:
        store.save(store_path)

    return {"ok": True, "chunks_indexed": len(chunks), "docs_root": str(root)}


def add_text_to_index(
    text: str,
    *,
    source: str = "dynamic",
    metadata: dict | None = None,
    chunk_size: int = 400,
    overlap: int = 80,
) -> int:
    """Chunk and add raw text to the live index. Returns number of chunks added."""
    chunks = chunk_text(text, source=source, chunk_size=chunk_size, overlap=overlap, metadata=metadata)
    if not chunks:
        return 0
    emb = _get_embedder()
    if isinstance(emb, TFIDFEmbedder) and not emb._is_fitted:
        emb.fit([c.text for c in chunks])
    vectors = emb.embed([c.text for c in chunks])
    _get_store().add(chunks, vectors)
    return len(chunks)


def load_index(store_path: str | Path) -> bool:
    """Load a persisted vector store from disk."""
    return _get_store().load(store_path)


# ── Retrieval ─────────────────────────────────────────────────────────────────


def retrieve(
    query: str,
    *,
    top_k: int = 5,
) -> list[SearchResult]:
    """Return the top-k passages most relevant to *query*."""
    emb = _get_embedder()
    store = _get_store()
    if len(store) == 0:
        return []
    q_vec = emb.embed_one(query)
    return store.search(q_vec, top_k=top_k)


def assemble_context(results: list[SearchResult]) -> str:
    """Format retrieval results into a context string for LLM prompts."""
    if not results:
        return ""
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] Source: {r.source}\n{r.text}")
    return "\n\n---\n\n".join(parts)


def retrieve_and_assemble(
    query: str,
    *,
    top_k: int = 5,
) -> tuple[list[SearchResult], str]:
    """Convenience: retrieve + assemble.

    Returns (results, context_string).
    """
    results = retrieve(query, top_k=top_k)
    return results, assemble_context(results)
