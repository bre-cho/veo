"""Embedding backends for the RAG pipeline.

Two backends are supported:
- ``tfidf``      : Pure NumPy TF-IDF. No external dependencies beyond numpy.
                   Fast, deterministic, good enough for internal ops docs.
- ``openrouter`` : Delegates to OpenRouter's embeddings endpoint.
                   Requires a valid ``OPENROUTER_API_KEY``-style key stored in
                   the ``AiEngineConfig`` table.

Usage::

    embedder = get_embedder("tfidf")
    vectors  = embedder.embed(["text a", "text b"])   # np.ndarray (n, dim)
"""
from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

# ── Base ──────────────────────────────────────────────────────────────────────


class BaseEmbedder(ABC):
    """Abstract embedder interface."""

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Return (n, dim) float32 embedding matrix."""

    @abstractmethod
    def embed_one(self, text: str) -> np.ndarray:
        """Return (dim,) float32 embedding vector."""


# ── TF-IDF (NumPy) ────────────────────────────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class TFIDFEmbedder(BaseEmbedder):
    """Incremental TF-IDF embedder backed purely by NumPy.

    Call ``fit(corpus)`` once to build the vocabulary, then ``embed(texts)``
    to project texts into the learned TF-IDF space.
    """

    def __init__(self, max_features: int = 4096) -> None:
        self.max_features = max_features
        self._vocab: dict[str, int] = {}       # token → col index
        self._idf: np.ndarray | None = None    # (vocab_size,)
        self._is_fitted: bool = False

    # ── Fitting ───────────────────────────────────────────────────────────────

    def fit(self, corpus: Sequence[str]) -> "TFIDFEmbedder":
        """Build vocabulary and IDF weights from *corpus*."""
        doc_freq: Counter[str] = Counter()
        tokenized = []
        for text in corpus:
            tokens = set(_tokenize(text))
            tokenized.append(tokens)
            doc_freq.update(tokens)

        # Select top-max_features by document frequency.
        top_terms = [t for t, _ in doc_freq.most_common(self.max_features)]
        self._vocab = {t: i for i, t in enumerate(top_terms)}
        n_docs = max(len(corpus), 1)

        idf_vals = np.array(
            [math.log((n_docs + 1) / (doc_freq.get(t, 0) + 1)) + 1.0
             for t in top_terms],
            dtype=np.float32,
        )
        self._idf = idf_vals
        self._is_fitted = True
        return self

    def _transform_one(self, text: str) -> np.ndarray:
        tokens = _tokenize(text)
        if not tokens or not self._is_fitted or self._idf is None:
            return np.zeros(max(len(self._vocab), 1), dtype=np.float32)
        tf_counter: Counter[str] = Counter(tokens)
        vec = np.zeros(len(self._vocab), dtype=np.float32)
        for token, count in tf_counter.items():
            idx = self._vocab.get(token)
            if idx is not None:
                vec[idx] = count / len(tokens)
        tfidf = vec * self._idf
        norm = np.linalg.norm(tfidf)
        return tfidf / norm if norm > 0 else tfidf

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return np.vstack([self._transform_one(t) for t in texts]) if texts else np.empty((0, len(self._vocab)), dtype=np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self._transform_one(text)

    # ── Serialisation helpers ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "max_features": self.max_features,
            "vocab": self._vocab,
            "idf": self._idf.tolist() if self._idf is not None else [],
            "is_fitted": self._is_fitted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TFIDFEmbedder":
        obj = cls(max_features=data.get("max_features", 4096))
        obj._vocab = data.get("vocab", {})
        idf = data.get("idf", [])
        obj._idf = np.array(idf, dtype=np.float32) if idf else None
        obj._is_fitted = data.get("is_fitted", False)
        return obj


# ── OpenRouter embeddings ─────────────────────────────────────────────────────


class OpenRouterEmbedder(BaseEmbedder):
    """Embedder that delegates to the OpenRouter embeddings API via httpx."""

    _BASE = "https://openrouter.ai/api/v1"
    _BATCH_SIZE = 64
    _TIMEOUT = 30

    def __init__(self, api_key: str, model: str = "openai/text-embedding-ada-002") -> None:
        self._api_key = api_key
        self._model = model

    def _call(self, batch: list[str]) -> np.ndarray:
        import httpx

        resp = httpx.post(
            f"{self._BASE}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}",
                     "Content-Type": "application/json"},
            json={"model": self._model, "input": batch},
            timeout=self._TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        vectors = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        return np.array(vectors, dtype=np.float32)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0,), dtype=np.float32)
        results = []
        for i in range(0, len(texts), self._BATCH_SIZE):
            results.append(self._call(list(texts[i: i + self._BATCH_SIZE])))
        return np.vstack(results)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


# ── Factory ───────────────────────────────────────────────────────────────────


def get_embedder(backend: str = "tfidf", **kwargs) -> BaseEmbedder:
    """Return an embedder instance by backend name."""
    if backend == "openrouter":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("api_key is required for openrouter embedder")
        return OpenRouterEmbedder(api_key=api_key, model=kwargs.get("model", "openai/text-embedding-ada-002"))
    return TFIDFEmbedder(max_features=kwargs.get("max_features", 4096))
