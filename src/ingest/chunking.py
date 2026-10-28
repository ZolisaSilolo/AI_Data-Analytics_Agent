"""Deterministic text chunking for the semantic RAG layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class TextChunk:
    index: int
    start: int
    end: int
    text: str
    page: Optional[int] = None


def chunk_text(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = CHUNK_OVERLAP,
    page: Optional[int] = None,
) -> List[TextChunk]:
    """
    Split text into overlapping, word-boundary-aware chunks.

    Deterministic: the same input always yields the same chunks, which keeps
    the embedding cache honest and makes retrieval reproducible.
    """
    if not isinstance(text, str):
        return []
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars.")

    chunks: List[TextChunk] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(length, start + max_chars)
        if end < length:
            boundary = cleaned.rfind(" ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        segment = cleaned[start:end].strip()
        if segment:
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    start=start,
                    end=start + len(segment),
                    text=segment,
                    page=page,
                )
            )
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks
