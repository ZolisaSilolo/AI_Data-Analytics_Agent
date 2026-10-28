"""Semantic RAG: S3 Vectors + Bedrock embeddings."""

from .embeddings import DEFAULT_DIMENSIONS, DEFAULT_EMBED_MODEL, embed_text, embed_texts
from .pipeline import SemanticIndex, catalog_as_documents
from .s3_vectors import S3VectorIndex, VectorHit, VectorRecord

__all__ = [
    "DEFAULT_DIMENSIONS",
    "DEFAULT_EMBED_MODEL",
    "S3VectorIndex",
    "SemanticIndex",
    "VectorHit",
    "VectorRecord",
    "catalog_as_documents",
    "embed_text",
    "embed_texts",
]
