"""Semantic RAG pipeline: definitions, dictionary and documents.

This layer retrieves *meaning* — metric definitions, the data dictionary,
prior analyses, extracted document text. It never returns numbers that are
meant to be shown to a user; those come from the deterministic engine.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional

from .embeddings import DEFAULT_DIMENSIONS, embed_text, embed_texts
from .s3_vectors import S3VectorIndex, VectorRecord

logger = logging.getLogger(__name__)

KIND_DEFINITION = "definition"
KIND_DICTIONARY = "dictionary"
KIND_ANALYSIS = "analysis"
KIND_DOCUMENT = "document"


class SemanticIndex:
    """Tenant-scoped semantic store backed by S3 Vectors + Bedrock embeddings."""

    def __init__(
        self,
        bucket_name: str,
        index_name: str,
        tenant_id: str,
        model_id: Optional[str] = None,
        dimensions: int = DEFAULT_DIMENSIONS,
        region: Optional[str] = None,
        vector_client: Any = None,
        runtime_client: Any = None,
    ) -> None:
        if not tenant_id:
            raise ValueError("SemanticIndex needs a tenant id for isolation.")
        self.tenant_id = tenant_id
        self.model_id = model_id
        self.dimensions = dimensions
        self.region = region
        self.runtime_client = runtime_client
        self.index = S3VectorIndex(bucket_name, index_name, region=region, client=vector_client)

    def _key(self, doc_id: str, chunk_index: int) -> str:
        return f"{self.tenant_id}/{doc_id}/{chunk_index}"

    @staticmethod
    def _content_hash(text: str) -> str:
        # Non-cryptographic fingerprint for dedupe, not for security.
        return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]

    def ingest_text(
        self,
        text: str,
        doc_id: str,
        kind: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Chunk, embed and store one document. Returns vectors written."""
        from ingest.chunking import chunk_text

        chunks = chunk_text(text)
        if not chunks:
            return 0

        embeddings = embed_texts(
            [chunk.text for chunk in chunks],
            model_id=self.model_id,
            dimensions=self.dimensions,
            client=self.runtime_client,
            region=self.region,
        )

        records = []
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            records.append(
                VectorRecord(
                    key=self._key(doc_id, chunk.index),
                    embedding=embedding,
                    metadata={
                        "tenant_id": self.tenant_id,
                        "doc_id": str(doc_id),
                        "kind": kind,
                        "chunk_index": chunk.index,
                        "content_hash": self._content_hash(chunk.text),
                        **(metadata or {}),
                    },
                )
            )
        return self.index.put(records)

    def search(
        self,
        query: str,
        top_k: int = 5,
        kind: Optional[str] = None,
        extra_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Tenant-scoped semantic search. Returns hits with citations."""
        vector = embed_text(
            query,
            model_id=self.model_id,
            dimensions=self.dimensions,
            client=self.runtime_client,
            region=self.region,
        )
        conditions: List[Dict[str, Any]] = [{"tenant_id": {"$eq": self.tenant_id}}]
        if kind:
            conditions.append({"kind": {"$eq": kind}})
        if extra_filter:
            conditions.append(extra_filter)
        metadata_filter = conditions[0] if len(conditions) == 1 else {"$and": conditions}

        hits = self.index.query(vector, top_k=top_k, metadata_filter=metadata_filter)
        return [
            {
                "key": hit.key,
                "distance": hit.distance,
                "doc_id": hit.metadata.get("doc_id"),
                "kind": hit.metadata.get("kind"),
                "chunk_index": hit.metadata.get("chunk_index"),
                "content_hash": hit.metadata.get("content_hash"),
            }
            for hit in hits
        ]

    def forget(self, doc_id: str) -> int:
        """Remove every vector for a document owned by this tenant."""
        prefix = f"{self.tenant_id}/{doc_id}/"
        hits = self.index.query([0.0] * self.dimensions, top_k=10_000)
        keys = [hit.key for hit in hits if hit.key.startswith(prefix)]
        return self.index.delete(keys) if keys else 0


def catalog_as_documents(catalog: Any) -> List[Dict[str, str]]:
    """Render the metric catalogue as ingestable documents (deterministic)."""
    documents: List[Dict[str, str]] = []
    for name in sorted(catalog.metrics):
        metric = catalog.metrics[name]
        documents.append(
            {
                "doc_id": f"metric/{metric.name}",
                "kind": KIND_DEFINITION,
                "text": (
                    f"Metric {metric.name} (version {metric.version}, unit {metric.unit}). "
                    f"{metric.description} Formula: {metric.display_sql}."
                ),
            }
        )
    return documents
