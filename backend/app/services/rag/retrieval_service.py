"""RAG retrieval service.

Manages:
- A singleton VectorStore + TFIDFEmbedder.
- Index building from the docs/ directory.
- Query-time retrieval of the top-k most relevant passages.
- Context assembly for LLM prompts.

Performance notes
-----------------
* **Incremental index**: ``build_index_from_directory`` tracks the last-modified
  time of each document.  On a rebuild request it only processes files that have
  changed since the last successful index, cutting rebuild time from O(total) to
  O(changed).  Pass ``force_full=True`` to skip the mtime check.
* **Persistent TFIDFEmbedder**: The fitted vocabulary is saved next to the
  vector-store on disk and reloaded at startup, so we avoid re-fitting on every
  process restart.
"""
from __future__ import annotations

import hashlib
import json
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
# Maps source-file path → last-modified timestamp (float); used for incremental builds.
_file_mtimes: dict[str, float] = {}


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
    global _store, _embedder, _file_mtimes
    _store = None
    _embedder = None
    _file_mtimes = {}


# ── Embedder persistence helpers ──────────────────────────────────────────────

def _embedder_path_for(store_path: str) -> Path:
    """Return the sidecar path for the TFIDFEmbedder vocabulary."""
    return Path(store_path).with_suffix(".embedder.json")


def _try_load_embedder(store_path: str) -> TFIDFEmbedder | None:
    """Attempt to load a previously-saved TFIDFEmbedder from disk."""
    ep = _embedder_path_for(store_path)
    return TFIDFEmbedder.load(ep)


def _save_embedder(emb: TFIDFEmbedder, store_path: str) -> None:
    ep = _embedder_path_for(store_path)
    emb.save(ep)


# ── Index building ────────────────────────────────────────────────────────────


def build_index_from_directory(
    docs_root: str | Path,
    *,
    chunk_size: int = 400,
    overlap: int = 80,
    store_path: str | None = None,
    backend: str = "tfidf",
    embedder_kwargs: dict | None = None,
    force_full: bool = False,
) -> dict[str, Any]:
    """Chunk all docs in *docs_root*, embed, and populate the vector store.

    When *store_path* is provided and *force_full* is ``False`` the function
    performs an **incremental** rebuild: only files whose mtime has changed since
    the last call are re-chunked and re-embedded.  The store is rebuilt from
    scratch only when the embedder vocabulary must change (new documents alter
    the TF-IDF corpus).

    Returns a summary dict.
    """
    global _file_mtimes

    root = Path(docs_root)
    if not root.exists():
        return {"ok": False, "reason": f"docs_root not found: {root}"}

    # Gather all source files with their current mtimes.
    all_files: list[Path] = sorted(root.rglob("*"))
    current_mtimes: dict[str, float] = {
        str(f): f.stat().st_mtime for f in all_files if f.is_file()
    }

    changed_files = [
        f for f in all_files
        if f.is_file() and (force_full or current_mtimes[str(f)] != _file_mtimes.get(str(f)))
    ]

    if not force_full and not changed_files:
        logger.debug("build_index_from_directory: no changed files, skipping rebuild")
        return {"ok": True, "chunks_indexed": len(_get_store()), "docs_root": str(root), "skipped": True}

    # For TF-IDF we must re-fit when the corpus changes (IDF weights depend on
    # the whole corpus).  Rebuild the entire store in that case.
    # For other backends (openrouter) incremental add is safe.
    emb = _get_embedder(backend, **(embedder_kwargs or {}))
    if isinstance(emb, TFIDFEmbedder):
        # Full corpus required for IDF; always do a full rebuild for TF-IDF.
        all_chunks = list(chunk_directory(root, chunk_size=chunk_size, overlap=overlap))
        if not all_chunks:
            return {"ok": False, "reason": "No documents found to index"}
        # Attempt to reuse a previously-fitted vocab if available and nothing changed.
        if not force_full and store_path and not changed_files:
            saved = _try_load_embedder(store_path)
            if saved is not None:
                _embedder = saved
                emb = saved

        if not emb._is_fitted or force_full or changed_files:
            emb.fit([c.text for c in all_chunks])

        store = _get_store()
        store.clear()
        vectors = emb.embed([c.text for c in all_chunks])
        store.add(all_chunks, vectors)
        _file_mtimes = current_mtimes

        if store_path:
            store.save(store_path)
            _save_embedder(emb, store_path)

        return {"ok": True, "chunks_indexed": len(all_chunks), "docs_root": str(root)}

    # Non-TF-IDF backend: incremental — add only changed-file chunks.
    changed_chunks = list(chunk_directory(
        root,
        chunk_size=chunk_size,
        overlap=overlap,
        include_files={str(f) for f in changed_files},
    ) if hasattr(chunk_directory, "__code__") and "include_files" in chunk_directory.__code__.co_varnames else
        # Fallback: full rebuild if chunk_directory doesn't support include_files.
        chunk_directory(root, chunk_size=chunk_size, overlap=overlap))

    if not changed_chunks:
        return {"ok": False, "reason": "No documents found to index"}

    store = _get_store()
    vectors = emb.embed([c.text for c in changed_chunks])
    store.add(changed_chunks, vectors)
    _file_mtimes.update(current_mtimes)

    if store_path:
        store.save(store_path)

    return {"ok": True, "chunks_indexed": len(changed_chunks), "docs_root": str(root), "incremental": True}


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
    """Load a persisted vector store from disk.

    Also attempts to restore a saved TFIDFEmbedder vocabulary so that
    subsequent ``embed_one`` calls use the same IDF weights.
    """
    ok = _get_store().load(store_path)
    if ok:
        saved_emb = _try_load_embedder(str(store_path))
        if saved_emb is not None:
            global _embedder
            _embedder = saved_emb
    return ok


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
