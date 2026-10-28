"""S3 key construction, ownership validation and presigned uploads."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from api.validation import DATASET_KEY_RE, invalid_dataset_key
from errors import internal

_BOTO_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=3,
    read_timeout=10,
)

PRESIGN_EXPIRES_SECONDS = int(os.environ.get("PRESIGN_EXPIRES_SECONDS", "900"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))


def _client():
    return boto3.client("s3", config=_BOTO_CONFIG)


def build_dataset_key(tenant_id: str, ext: str) -> str:
    """Server-generated key. Clients never choose their own object key."""
    if ext not in {"csv", "parquet"}:
        raise invalid_dataset_key()
    return f"uploads/{tenant_id}/{uuid.uuid4()}.{ext}"


def build_artifact_key(tenant_id: str, job_id: str) -> str:
    return f"artifacts/{tenant_id}/{job_id}/result.json"


def assert_owned_key(key: str, tenant_id: str) -> None:
    match = DATASET_KEY_RE.fullmatch(key or "")
    if not match or match.group("tenant") != tenant_id:
        raise invalid_dataset_key()


def create_upload(
    bucket: str,
    tenant_id: str,
    ext: str,
    content_type: str,
    size: int,
) -> Dict[str, Any]:
    """Create a size-constrained presigned POST for a single dataset object."""
    key = build_dataset_key(tenant_id, ext)
    max_size = min(size, MAX_UPLOAD_BYTES)
    try:
        presigned = _client().generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_size],
            ],
            ExpiresIn=PRESIGN_EXPIRES_SECONDS,
        )
    except ClientError as exc:
        raise internal(f"presign failed: {exc}") from exc

    return {
        "upload_url": presigned["url"],
        "upload_fields": presigned["fields"],
        "dataset_key": key,
        "expires_in": PRESIGN_EXPIRES_SECONDS,
        "max_bytes": max_size,
    }


def put_json(bucket: str, key: str, payload: str) -> None:
    _client().put_object(
        Bucket=bucket,
        Key=key,
        Body=payload.encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


def get_json(bucket: str, key: str) -> str:
    try:
        resp = _client().get_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        raise internal(f"artifact read failed: {exc}") from exc
    return resp["Body"].read().decode("utf-8")


def head_object(bucket: str, key: str) -> Optional[Dict[str, Any]]:
    """Return object metadata when the object exists, otherwise ``None``."""
    try:
        return _client().head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise internal(f"head_object failed: {exc}") from exc
