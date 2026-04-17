"""Document chunker for the RAG pipeline.

Splits plain-text or markdown documents into overlapping text passages
(chunks) suitable for embedding and retrieval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class DocumentChunk:
    """A single passage extracted from a source document."""

    chunk_id: str
    source: str          # file path or logical label
    text: str
    char_start: int
    char_end: int
    metadata: dict = field(default_factory=dict)


def _clean_text(text: str) -> str:
    """Normalise whitespace without collapsing meaningful newlines."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    *,
    source: str = "unknown",
    chunk_size: int = 400,
    overlap: int = 80,
    metadata: dict | None = None,
) -> list[DocumentChunk]:
    """Split *text* into overlapping chunks.

    Parameters
    ----------
    text       : Source text.
    source     : Label for the originating document.
    chunk_size : Approximate maximum character length of each chunk.
    overlap    : Number of characters carried over from the previous chunk.
    metadata   : Extra metadata merged into every chunk.
    """
    text = _clean_text(text)
    if not text:
        return []

    metadata = metadata or {}
    chunks: list[DocumentChunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break on a sentence or paragraph boundary.
        if end < len(text):
            for boundary in ("\n\n", "\n", ". ", "! ", "? ", " "):
                pos = text.rfind(boundary, start, end)
                if pos > start:
                    end = pos + len(boundary)
                    break

        chunk_text_str = text[start:end].strip()
        if chunk_text_str:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{source}::chunk{idx:04d}",
                    source=source,
                    text=chunk_text_str,
                    char_start=start,
                    char_end=end,
                    metadata=dict(metadata),
                )
            )
            idx += 1

        if end >= len(text):
            break
        start = max(start + 1, end - overlap)

    return chunks


def chunk_file(
    path: Path,
    *,
    chunk_size: int = 400,
    overlap: int = 80,
    extra_metadata: dict | None = None,
) -> list[DocumentChunk]:
    """Read a text/markdown file and return its chunks."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    meta = {"file": str(path), **(extra_metadata or {})}
    return chunk_text(text, source=str(path), chunk_size=chunk_size, overlap=overlap, metadata=meta)


def chunk_directory(
    root: Path,
    *,
    extensions: tuple[str, ...] = (".md", ".txt", ".rst"),
    chunk_size: int = 400,
    overlap: int = 80,
) -> Iterator[DocumentChunk]:
    """Walk a directory tree and yield chunks for all matching files."""
    for p in root.rglob("*"):
        if p.suffix.lower() in extensions and p.is_file():
            yield from chunk_file(p, chunk_size=chunk_size, overlap=overlap)
