"""Semantic RAG: vector client behaviour and pipeline, with fake AWS clients."""

from __future__ import annotations

import io
import json

from rag import S3VectorIndex, SemanticIndex, VectorRecord, catalog_as_documents
from semantic import load_catalog


class FakeRuntime:
    def __init__(self, dims: int = 8):
        self.dims = dims
        self.calls = []

    def invoke_model(self, modelId, body, contentType, accept):  # noqa: A002
        payload = json.loads(body)
        self.calls.append(payload)
        dims = payload.get("dimensions", self.dims)
        return {
            "body": io.BytesIO(
                json.dumps({"embedding": [round(1.0 / dims, 8)] * dims}).encode()
            )
        }


class FakeVectors:
    def __init__(self):
        self.puts = []
        self.queries = []
        self.deletes = []

    def put_vectors(self, **kwargs):
        self.puts.append(kwargs)
        return {}

    def query_vectors(self, **kwargs):
        self.queries.append(kwargs)
        return {
            "vectors": [
                {
                    "key": "t/doc/0",
                    "distance": 0.01,
                    "metadata": {"tenant_id": "t", "doc_id": "doc", "kind": "definition"},
                }
            ]
        }

    def delete_vectors(self, **kwargs):
        self.deletes.append(kwargs)
        return {}


def test_put_batches_at_five_hundred():
    vectors = FakeVectors()
    index = S3VectorIndex("bucket", "index", client=vectors)
    records = [VectorRecord(key=f"k{i}", embedding=[0.1, 0.2]) for i in range(1200)]
    written = index.put(records)
    assert written == 1200
    assert len(vectors.puts) == 3
    assert len(vectors.puts[0]["vectors"]) == 500
    assert len(vectors.puts[-1]["vectors"]) == 200


def test_metadata_is_trimmed_to_the_filterable_budget():
    index = S3VectorIndex("bucket", "index", client=FakeVectors())
    record = VectorRecord(
        key="k",
        embedding=[0.0],
        metadata={"text": "x" * 5000, "kind": "definition", "count": 3},
    )
    trimmed = index._trim_metadata(record.metadata)
    assert len(trimmed["text"]) <= 512
    assert trimmed["kind"] == "definition"
    assert trimmed["count"] == 3


def test_query_passes_filter_and_caps_top_k():
    vectors = FakeVectors()
    index = S3VectorIndex("bucket", "index", client=vectors)
    hits = index.query([0.1, 0.2], top_k=99_999, metadata_filter={"tenant_id": {"$eq": "t"}})
    assert vectors.queries[0]["topK"] == 10_000
    assert vectors.queries[0]["filter"] == {"tenant_id": {"$eq": "t"}}
    assert hits[0].metadata["kind"] == "definition"


def test_semantic_index_ingests_and_scopes_search_to_the_tenant():
    vectors = FakeVectors()
    runtime = FakeRuntime()
    index = SemanticIndex(
        "bucket", "index", tenant_id="t",
        vector_client=vectors, runtime_client=runtime, dimensions=8,
    )
    written = index.ingest_text("Revenue is the sum of the revenue column. " * 30, "metric/revenue", "definition")
    assert written >= 2
    keys = [v["key"] for batch in vectors.puts for v in batch["vectors"]]
    assert all(key.startswith("t/metric/revenue/") for key in keys)

    hits = index.search("what is revenue?", kind="definition")
    assert hits
    metadata_filter = vectors.queries[0]["filter"]
    assert metadata_filter == {
        "$and": [{"tenant_id": {"$eq": "t"}}, {"kind": {"$eq": "definition"}}]
    }


def test_empty_text_embeds_to_a_zero_vector_without_api_calls():
    runtime = FakeRuntime()
    index = SemanticIndex(
        "bucket", "index", tenant_id="t",
        vector_client=FakeVectors(), runtime_client=runtime, dimensions=8,
    )
    assert index.ingest_text("   ", "empty", "document") == 0
    assert runtime.calls == []


def test_catalog_documents_are_sorted_and_informative():
    catalog = load_catalog()
    documents = catalog_as_documents(catalog)
    assert len(documents) == len(catalog.metrics)
    doc_ids = [doc["doc_id"] for doc in documents]
    assert doc_ids == sorted(doc_ids)
    revenue = next(doc for doc in documents if doc["doc_id"] == "metric/revenue")
    assert "SUM" in revenue["text"]
    assert revenue["kind"] == "definition"
