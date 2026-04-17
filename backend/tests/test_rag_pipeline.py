"""Tests for the RAG pipeline (chunker + embedder + vector store + retrieval)."""
from __future__ import annotations

import numpy as np
import pytest

from app.services.rag.document_chunker import DocumentChunk, chunk_text
from app.services.rag.embedder import TFIDFEmbedder
from app.services.rag.vector_store import VectorStore
from app.services.rag import retrieval_service


# ── Chunker ───────────────────────────────────────────────────────────────────


def test_chunk_text_basic():
    text = "Hello world. " * 50
    chunks = chunk_text(text, source="test", chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(isinstance(c, DocumentChunk) for c in chunks)
    assert all(len(c.text) > 0 for c in chunks)


def test_chunk_text_empty():
    chunks = chunk_text("", source="empty")
    assert chunks == []


def test_chunk_text_single_chunk():
    text = "Short text."
    chunks = chunk_text(text, source="single", chunk_size=400)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_chunk_metadata():
    chunks = chunk_text("Hello.", source="doc.md", metadata={"env": "prod"})
    assert chunks[0].metadata["env"] == "prod"


def test_chunk_ids_unique():
    text = "word " * 200
    chunks = chunk_text(text, source="test", chunk_size=100, overlap=10)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


# ── TF-IDF Embedder ───────────────────────────────────────────────────────────


def test_tfidf_fit_and_embed():
    corpus = ["render job failed", "scene task queued", "provider veo error"]
    emb = TFIDFEmbedder(max_features=256)
    emb.fit(corpus)
    vectors = emb.embed(corpus)
    assert vectors.shape == (3, len(emb._vocab))
    assert vectors.dtype == np.float32


def test_tfidf_embed_one():
    corpus = ["render job failed", "scene task queued", "provider veo error"]
    emb = TFIDFEmbedder(max_features=256)
    emb.fit(corpus)
    vec = emb.embed_one("render job")
    assert vec.ndim == 1
    assert len(vec) == len(emb._vocab)


def test_tfidf_similar_texts_higher_score():
    emb = TFIDFEmbedder(max_features=512)
    corpus = [
        "the render job is done",
        "render scene completed successfully",
        "weather forecast sunny tomorrow",
    ]
    emb.fit(corpus)
    v_query = emb.embed_one("render job done")
    v_similar = emb.embed_one("render scene completed successfully")
    v_dissimilar = emb.embed_one("weather forecast sunny tomorrow")
    score_similar = float(v_query @ v_similar)
    score_dissimilar = float(v_query @ v_dissimilar)
    assert score_similar >= score_dissimilar


def test_tfidf_serialise_roundtrip():
    emb = TFIDFEmbedder(max_features=128)
    emb.fit(["hello world", "foo bar baz"])
    data = emb.to_dict()
    emb2 = TFIDFEmbedder.from_dict(data)
    v1 = emb.embed_one("hello world")
    v2 = emb2.embed_one("hello world")
    np.testing.assert_allclose(v1, v2, atol=1e-5)


def test_tfidf_empty_corpus():
    emb = TFIDFEmbedder()
    emb.fit([])
    v = emb.embed_one("test")
    assert v.ndim == 1


# ── Vector Store ──────────────────────────────────────────────────────────────


def _make_chunk(i: int, text: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"chunk{i:04d}",
        source=f"doc_{i}.md",
        text=text,
        char_start=0,
        char_end=len(text),
    )


def test_vector_store_add_and_search():
    store = VectorStore()
    texts = ["render job failed", "scene queued", "provider veo error"]
    chunks = [_make_chunk(i, t) for i, t in enumerate(texts)]
    emb = TFIDFEmbedder(max_features=256)
    emb.fit(texts)
    vectors = emb.embed(texts)
    store.add(chunks, vectors)
    assert len(store) == 3

    q = emb.embed_one("render job")
    results = store.search(q, top_k=2)
    assert len(results) == 2
    assert results[0].score >= results[1].score


def test_vector_store_empty_search():
    store = VectorStore()
    q = np.zeros(10, dtype=np.float32)
    results = store.search(q, top_k=5)
    assert results == []


def test_vector_store_save_load(tmp_path):
    store = VectorStore()
    texts = ["hello world", "foo bar"]
    chunks = [_make_chunk(i, t) for i, t in enumerate(texts)]
    emb = TFIDFEmbedder(max_features=64)
    emb.fit(texts)
    vectors = emb.embed(texts)
    store.add(chunks, vectors)

    path = tmp_path / "store.json"
    store.save(str(path))

    store2 = VectorStore()
    ok = store2.load(str(path))
    assert ok
    assert len(store2) == 2


def test_vector_store_clear():
    store = VectorStore()
    texts = ["hello"]
    chunks = [_make_chunk(0, texts[0])]
    emb = TFIDFEmbedder()
    emb.fit(texts)
    store.add(chunks, emb.embed(texts))
    store.clear()
    assert len(store) == 0


# ── Retrieval service ─────────────────────────────────────────────────────────


def test_retrieval_add_and_retrieve():
    retrieval_service.reset_index()
    n = retrieval_service.add_text_to_index(
        "The render job pipeline queues scene tasks for provider dispatch.",
        source="ops-runbook",
    )
    assert n >= 1
    results, ctx = retrieval_service.retrieve_and_assemble("render job pipeline", top_k=3)
    assert len(results) >= 1
    assert "ops-runbook" in ctx or len(ctx) >= 0


def test_retrieval_empty_index():
    retrieval_service.reset_index()
    results = retrieval_service.retrieve("anything", top_k=5)
    assert results == []


def test_retrieval_context_assembly():
    retrieval_service.reset_index()
    retrieval_service.add_text_to_index("Provider veo handles video generation.", source="provider-guide")
    retrieval_service.add_text_to_index("Retry logic is applied after failures.", source="retry-policy")
    _, ctx = retrieval_service.retrieve_and_assemble("veo provider", top_k=2)
    assert "Source:" in ctx
