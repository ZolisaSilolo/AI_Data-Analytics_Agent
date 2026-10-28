"""DynamoDB persistence for analysis jobs."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from errors import internal

_TABLE = os.environ.get("JOBS_TABLE", "")
_JOB_TTL_DAYS = int(os.environ.get("JOB_TTL_DAYS", "90"))

_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=2, read_timeout=5)

STATUS_QUEUED = "QUEUED"
STATUS_RUNNING = "RUNNING"
# A transient failure that SQS will redeliver. Kept distinct from FAILED so a
# client polling the job does not stop before the retry lands, and distinct from
# QUEUED so the UI can show that an attempt has already been billed.
STATUS_RETRYING = "RETRYING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_FAILED)


def _table():
    if not _TABLE:
        raise internal("JOBS_TABLE is not configured")
    return boto3.resource("dynamodb", config=_CONFIG).Table(_TABLE)


def _now() -> int:
    return int(time.time())


def create_job(
    tenant_id: str,
    job_id: str,
    mode: str,
    query: str,
    dataset_key: Optional[str] = None,
    discipline: str = "general",
    model_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a job. Returns ``None`` when the job already exists, which makes
    idempotent retries cheap (no duplicate queue messages).
    """
    now = _now()
    item: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "job_id": job_id,
        "status": STATUS_QUEUED,
        "mode": mode,
        "query": query[:4000],
        "discipline": discipline,
        "created_at": now,
        "updated_at": now,
        "attempts": 0,
        "ttl": now + _JOB_TTL_DAYS * 86400,
    }
    if dataset_key:
        item["dataset_key"] = dataset_key
    if model_id:
        item["model_id"] = model_id
    try:
        _table().put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(job_id)",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return None
        raise
    return item


def get_job(tenant_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    resp = _table().get_item(Key={"tenant_id": tenant_id, "job_id": job_id})
    return resp.get("Item")


def update_job(tenant_id: str, job_id: str, **fields: Any) -> None:
    fields["updated_at"] = _now()
    names, values, assignments = {}, {}, []
    for idx, (key, value) in enumerate(fields.items()):
        names[f"#f{idx}"] = key
        values[f":v{idx}"] = value
        assignments.append(f"#f{idx} = :v{idx}")
    _table().update_item(
        Key={"tenant_id": tenant_id, "job_id": job_id},
        UpdateExpression="SET " + ", ".join(assignments),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def increment_attempts(tenant_id: str, job_id: str) -> int:
    """
    Count a delivery attempt, moving the job to ``RUNNING``.

    A terminal job is never resurrected: SQS is at-least-once, so a redelivery
    after completion must not flip ``COMPLETED`` back to ``RUNNING``. In that
    case only the attempt counter advances.
    """
    try:
        resp = _table().update_item(
            Key={"tenant_id": tenant_id, "job_id": job_id},
            UpdateExpression="ADD attempts :one SET #s = :running, updated_at = :now",
            ConditionExpression="attribute_not_exists(#s) OR #s IN (:queued, :retrying, :running)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":one": 1,
                ":running": STATUS_RUNNING,
                ":queued": STATUS_QUEUED,
                ":retrying": STATUS_RETRYING,
                ":now": _now(),
            },
            ReturnValues="UPDATED_NEW",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        resp = _table().update_item(
            Key={"tenant_id": tenant_id, "job_id": job_id},
            UpdateExpression="ADD attempts :one SET updated_at = :now",
            ExpressionAttributeValues={":one": 1, ":now": _now()},
            ReturnValues="UPDATED_NEW",
        )
    return int(resp.get("Attributes", {}).get("attempts", 1))


def mark_retrying(tenant_id: str, job_id: str, code: str, message: str) -> None:
    """Record a transient failure without claiming the job is finished."""
    try:
        update_job(
            tenant_id,
            job_id,
            status=STATUS_RETRYING,
            error={"code": code, "message": message[:1000], "retryable": True},
        )
    except ClientError as exc:
        raise internal(f"failed to persist job retry: {exc}") from exc


def delete_job(tenant_id: str, job_id: str) -> None:
    """
    Remove a job that was persisted but never enqueued, so an idempotent retry
    can enqueue it instead of finding a permanent ``QUEUED`` record.

    The delete is conditional: if a worker already claimed the message the row is
    left alone and the job completes normally.
    """
    try:
        _table().delete_item(
            Key={"tenant_id": tenant_id, "job_id": job_id},
            ConditionExpression="#s = :queued",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":queued": STATUS_QUEUED},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return
        raise internal(f"failed to roll back job: {exc}") from exc


def mark_failed(tenant_id: str, job_id: str, code: str, message: str, retryable: bool) -> None:
    try:
        update_job(
            tenant_id,
            job_id,
            status=STATUS_FAILED,
            error={"code": code, "message": message[:1000], "retryable": retryable},
        )
    except ClientError as exc:
        raise internal(f"failed to persist job failure: {exc}") from exc
