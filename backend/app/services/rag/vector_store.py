"""In-memory cosine-similarity vector store for the RAG pipeline.

Backed by a NumPy matrix; persisted to / loaded from a JSON sidecar file.

Usage::

    store = VectorStore()
    store.add(chunks, embedder.embed([c.text for c in chunks]))
    results = store.search(embedder.embed_one(query), top_k=5)
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    source: str
    text: str
    score: float
    metadata: dict


class VectorStore:
    """In-memory vector store with cosine similarity search."""

    def __init__(self) -> None:
        self._vectors: np.ndarray | None = None   # (n, dim) float32
        self._metadata: list[dict[str, Any]] = []

    # ── Indexing ──────────────────────────────────────────────────────────────

    def add(
        self,
        chunks: list[Any],   # list[DocumentChunk]
        vectors: np.ndarray,
    ) -> None:
        """Add (chunk, vector) pairs to the store."""
        if len(chunks) == 0:
            return
        if vectors.shape[0] != len(chunks):
            raise ValueError("chunks and vectors length mismatch")

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms_safe = np.where(norms == 0, 1.0, norms)
        normed = vectors / norms_safe

        self._vectors = (
            np.vstack([self._vectors, normed])
            if self._vectors is not None
            else normed.copy()
        )
        for chunk in chunks:
            self._metadata.append({
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "text": chunk.text,
                "metadata": chunk.metadata,
            })

    def clear(self) -> None:
        self._vectors = None
        self._metadata = []

    def __len__(self) -> int:
        return len(self._metadata)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Return the top-k most similar chunks by cosine similarity."""
        if self._vectors is None or len(self._metadata) == 0:
            return []

        norm = np.linalg.norm(query_vector)
        q = query_vector / norm if norm > 0 else query_vector
        scores: np.ndarray = self._vectors @ q      # (n,)

        top_k = min(top_k, len(self._metadata))
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        results = []
        for idx in top_indices:
            meta = self._metadata[idx]
            results.append(
                SearchResult(
                    chunk_id=meta["chunk_id"],
                    source=meta["source"],
                    text=meta["text"],
                    score=float(scores[idx]),
                    metadata=meta.get("metadata", {}),
                )
            )
        return results

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """Serialise the store: metadata to a JSON sidecar, vectors to a binary .npy file.

        The ``.npy`` format is 10–100× faster to read/write than JSON for large
        matrices and avoids the precision loss of ``float.tolist()``.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        meta_path = p.with_suffix(".meta.json")
        npy_path = p.with_suffix(".npy")
        meta_path.write_text(json.dumps(self._metadata), encoding="utf-8")
        if self._vectors is not None:
            np.save(str(npy_path), self._vectors)
        elif npy_path.exists():
            npy_path.unlink()
        logger.info("VectorStore saved: %d chunks to %s", len(self._metadata), p)

    def load(self, path: str | Path) -> bool:
        """Load store from disk.  Supports both the new ``.npy`` binary format and
        the legacy single-JSON format for backwards compatibility.
        """
        p = Path(path)
        meta_path = p.with_suffix(".meta.json")
        npy_path = p.with_suffix(".npy")

        # --- New binary format ---
        if meta_path.exists():
            try:
                self._metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                self._vectors = np.load(str(npy_path), allow_pickle=False) if npy_path.exists() else None
                logger.info("VectorStore loaded: %d chunks from %s", len(self._metadata), p)
                return True
            except Exception as exc:
                logger.warning("Failed to load VectorStore (binary) from %s: %s", p, exc)
                return False

        # --- Legacy JSON format (single file) ---
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                self._metadata = data.get("metadata", [])
                vecs = data.get("vectors", [])
                self._vectors = np.array(vecs, dtype=np.float32) if vecs else None
                logger.info("VectorStore loaded (legacy JSON): %d chunks from %s", len(self._metadata), p)
                return True
            except Exception as exc:
                logger.warning("Failed to load VectorStore from %s: %s", p, exc)
                return False

        return False
