"""Embeddings via Amazon Bedrock (Titan Text Embeddings V2 by default).

The embedding model is a dependency of the retrieval layer, not of the
deterministic engine, so it can change without invalidating analytical results.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, List, Optional, Sequence

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_DIMENSIONS = 512  # ~99% of the 1024-dim accuracy at half the storage

_CONFIG = Config(retries={"max_attempts": 3, "mode": "adaptive"}, read_timeout=30)


def _client(client: Any, region: Optional[str]) -> Any:
    if client is not None:
        return client
    return boto3.client(
        "bedrock-runtime",
        region_name=region or os.environ.get("AWS_REGION", "us-east-1"),
        config=_CONFIG,
    )


def embed_text(
    text: str,
    model_id: Optional[str] = None,
    dimensions: int = DEFAULT_DIMENSIONS,
    normalize: bool = True,
    client: Any = None,
    region: Optional[str] = None,
) -> List[float]:
    """Embed one string. Empty input returns a zero vector, not an API call."""
    if not isinstance(text, str) or not text.strip():
        return [0.0] * dimensions
    runtime = _client(client, region)
    body = {
        "inputText": text[:30_000],
        "dimensions": dimensions,
        "normalize": normalize,
    }
    response = runtime.invoke_model(
        modelId=model_id or os.environ.get("EMBED_MODEL_ID", DEFAULT_EMBED_MODEL),
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    return list(payload["embedding"])


def embed_texts(
    texts: Sequence[str],
    model_id: Optional[str] = None,
    dimensions: int = DEFAULT_DIMENSIONS,
    normalize: bool = True,
    client: Any = None,
    region: Optional[str] = None,
) -> List[List[float]]:
    """Embed a batch of strings (one invocation each; Titan v2 is single-input)."""
    runtime = _client(client, region)
    return [
        embed_text(text, model_id, dimensions, normalize, runtime) for text in texts
    ]
