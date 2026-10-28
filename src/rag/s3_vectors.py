"""Thin S3 Vectors client.

S3 Vectors is the vector store for the semantic RAG layer: billion-scale,
~100 ms warm queries, pay-per-query, and natively supported by Bedrock
Knowledge Bases. This wrapper keeps the API surface tiny so a change in the
control plane is a one-line fix.

Limits this module honours (us-east-1, verified against S3 docs):

* up to 500 vectors per ``PutVectors`` call
* filterable metadata per vector up to 2 KB (35 keys when used by Bedrock KB)
* ``topK`` up to 10,000
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

import boto3

logger = logging.getLogger(__name__)

_PUT_BATCH = 500
_METADATA_KEYS_LIMIT = 35
_METADATA_CHARS_LIMIT = 1024  # stay under the Bedrock KB filterable budget


@dataclass(frozen=True)
class VectorRecord:
    key: str
    embedding: Sequence[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorHit:
    key: str
    distance: Optional[float]
    metadata: Dict[str, Any]


class S3VectorIndex:
    """A single vector index in one S3 vector bucket."""

    def __init__(
        self,
        bucket_name: str,
        index_name: str,
        region: Optional[str] = None,
        client: Any = None,
    ) -> None:
        if not bucket_name or not index_name:
            raise ValueError("S3VectorIndex needs a vector bucket name and an index name.")
        self.bucket_name = bucket_name
        self.index_name = index_name
        self.client = client or boto3.client(
            "s3vectors",
            region_name=region or os.environ.get("AWS_REGION", "us-east-1"),
        )

    @staticmethod
    def _trim_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Keep metadata inside the filterable budget (S3 Vectors rejects over)."""
        trimmed: Dict[str, Any] = {}
        for key, value in metadata.items():
            if len(trimmed) >= _METADATA_KEYS_LIMIT:
                break
            if isinstance(value, bool) or isinstance(value, (int, float)) or value is None:
                trimmed[str(key)] = value
            else:
                text = str(value)
                trimmed[str(key)] = text[: _METADATA_CHARS_LIMIT // 2]
        return trimmed

    def put(self, records: Iterable[VectorRecord]) -> int:
        items = list(records)
        written = 0
        for start in range(0, len(items), _PUT_BATCH):
            batch = items[start : start + _PUT_BATCH]
            self.client.put_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                vectors=[
                    {
                        "key": str(record.key),
                        "data": {"float32": [float(v) for v in record.embedding]},
                        "metadata": self._trim_metadata(record.metadata),
                    }
                    for record in batch
                ],
            )
            written += len(batch)
        return written

    def query(
        self,
        embedding: Sequence[float],
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[VectorHit]:
        request: Dict[str, Any] = {
            "vectorBucketName": self.bucket_name,
            "indexName": self.index_name,
            "queryVector": {"float32": [float(v) for v in embedding]},
            "topK": max(1, min(int(top_k), 10_000)),
            "returnMetadata": True,
            "returnDistance": True,
        }
        if metadata_filter:
            request["filter"] = metadata_filter
        response = self.client.query_vectors(**request)
        hits: List[VectorHit] = []
        for item in response.get("vectors", []):
            hits.append(
                VectorHit(
                    key=str(item.get("key", "")),
                    distance=item.get("distance"),
                    metadata=dict(item.get("metadata") or {}),
                )
            )
        return hits

    def delete(self, keys: Iterable[str]) -> int:
        batch = [str(key) for key in keys]
        removed = 0
        for start in range(0, len(batch), _PUT_BATCH):
            chunk = batch[start : start + _PUT_BATCH]
            self.client.delete_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                keys=chunk,
            )
            removed += len(chunk)
        return removed
