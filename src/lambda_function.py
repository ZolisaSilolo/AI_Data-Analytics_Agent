"""
HTTP API handler (thin, fast).

Responsibilities: validate, authorize (Phase 1), enqueue, and read job state.
Heavy analysis runs in ``worker.lambda_handler`` so the API never approaches the
30 second HTTP API integration limit.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

import repository
import storage
from api.validation import (
    get_tenant_id,
    normalize_chart_type,
    normalize_discipline,
    parse_body,
    require_known_fields,
    validate_chart_columns,
    validate_dataset_key,
    validate_model_id,
    validate_page_context,
    validate_query,
    validate_sql,
    validate_upload_request,
)
from errors import AppError, bad_request, internal, not_found, payload_too_large
from storage import assert_owned_key

logger = Logger(service="data-analyst-api")
metrics = Metrics(namespace="DataAnalystAgent", service="data-analyst-api")
tracer = Tracer(service="data-analyst-api")

_BOTO_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=2, read_timeout=5)
_sqs = None

ANALYZE_FIELDS = {
    "query",
    "dataset_key",
    "discipline",
    "model_id",
    "chart_type",
    "chart_columns",
    "generate_chart",
    "page_context",
}
SQL_FIELDS = {"sql", "dataset_key", "page_context"}
UPLOAD_FIELDS = {"filename", "name", "size", "content_type"}

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")
DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
QUEUE_URL = os.environ.get("ANALYSIS_QUEUE_URL", "")
PRIMARY_MODEL = os.environ.get(
    "BEDROCK_PRIMARY_MODEL", "global.moonshotai.kimi-k3"
)
FALLBACK_MODEL = (os.environ.get("BEDROCK_FALLBACK_MODEL", "") or "").strip()
APP_VERSION = os.environ.get("APP_VERSION", "0.0.0")
COMMIT_SHA = os.environ.get("COMMIT_SHA", "unknown")


def _sqs_client():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs", config=_BOTO_CONFIG)
    return _sqs


def _json_default(value: Any) -> Any:
    """DynamoDB returns numbers as Decimal; keep them numeric in JSON."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return str(value)


def build_response(
    status_code: int,
    body: Dict[str, Any],
    request_id: str,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": (
            "Content-Type,Authorization,x-tenant-id,x-idempotency-key,x-correlation-id"
        ),
        "x-request-id": request_id,
    }
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=_json_default),
    }


def _request_id(context: Optional[LambdaContext], event: Dict[str, Any]) -> str:
    if context is not None and getattr(context, "aws_request_id", None):
        return context.aws_request_id
    return (
        event.get("requestContext", {}).get("requestId")
        or event.get("headers", {}).get("x-correlation-id")
        or "local-request"
    )


def _job_id(tenant_id: str, payload: Dict[str, Any], supplied: Optional[str]) -> str:
    if not supplied:
        return str(uuid.uuid4())
    seed = json.dumps(
        {"tenant": tenant_id, "key": supplied, "payload": payload}, sort_keys=True, default=str
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _headers(event: Dict[str, Any]) -> Dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (event.get("headers") or {}).items()}


def _route(event: Dict[str, Any]) -> Tuple[str, str]:
    """
    Resolve ``(method, path)`` independent of the API stage.

    For named stages API Gateway publishes ``rawPath`` *with* the stage segment
    (for example ``/dev/analyze``), so the configured stage prefix is stripped
    before routing. The ``$default`` stage needs no stripping.
    """
    context = event.get("requestContext") or {}
    method = context.get("http", {}).get("method") or event.get("httpMethod") or "POST"
    raw = event.get("rawPath") or event.get("path") or "/"

    stage = os.environ.get("STAGE_NAME", "")
    if stage and raw.startswith(f"/{stage}/"):
        raw = raw[len(stage) + 1:]

    return str(method).upper(), raw


# SQS rejects a message body larger than 256 KB. Validation keeps page context
# below this, and the check here makes the invariant explicit.
SQS_MAX_BODY_BYTES = 262_144


def _enqueue(tenant_id: str, job_id: str, mode: str, payload: Dict[str, Any]) -> None:
    if not QUEUE_URL:
        raise internal("ANALYSIS_QUEUE_URL is not configured")
    body = json.dumps(
        {"tenant_id": tenant_id, "job_id": job_id, "mode": mode, "payload": payload},
        default=str,
    )
    size = len(body.encode("utf-8"))
    if size > SQS_MAX_BODY_BYTES:
        raise payload_too_large(
            f"The job payload is {size} bytes, above the {SQS_MAX_BODY_BYTES} byte queue limit. "
            "Upload the dataset instead of extracting it from the page."
        )
    try:
        _sqs_client().send_message(QueueUrl=QUEUE_URL, MessageBody=body)
    except (ClientError, BotoCoreError) as exc:
        raise internal(f"enqueue failed: {exc}") from exc


def _submit(
    tenant_id: str,
    job_id: str,
    mode: str,
    payload: Dict[str, Any],
    created: Optional[Dict[str, Any]],
) -> None:
    """Enqueue a freshly created job, rolling the row back if publishing fails."""
    if created is None:
        return
    try:
        _enqueue(tenant_id, job_id, mode, payload)
    except AppError:
        # A QUEUED row with no message would never run, and an idempotent retry
        # would find the row and skip the enqueue again. Remove it so the retry
        # starts clean.
        repository.delete_job(tenant_id, job_id)
        raise


def _assert_dataset_exists(dataset_key: Optional[str]) -> None:
    """Fail fast when the upload never completed or has already expired."""
    if not dataset_key or not DATA_BUCKET:
        return
    if storage.head_object(DATA_BUCKET, dataset_key) is None:
        raise AppError(
            "DATASET_NOT_FOUND",
            "The uploaded dataset was not found. Upload the file again.",
            status=404,
        )


# -- route handlers ----------------------------------------------------------


def _health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "commit": COMMIT_SHA,
        "primary_model": PRIMARY_MODEL,
        "fallback_model": FALLBACK_MODEL or None,
        "queue_configured": bool(QUEUE_URL),
        "bucket_configured": bool(DATA_BUCKET),
    }


def _presign(event: Dict[str, Any], tenant_id: str) -> Tuple[int, Dict[str, Any]]:
    payload = parse_body(event)
    require_known_fields(payload, UPLOAD_FIELDS)
    spec = validate_upload_request(payload)
    if not DATA_BUCKET:
        raise internal("DATA_BUCKET is not configured")
    created = storage.create_upload(
        DATA_BUCKET, tenant_id, spec["ext"], spec["content_type"], spec["size"]
    )
    metrics.add_metric(name="PresignIssued", unit=MetricUnit.Count, value=1)
    return 200, created


def _analyze(event: Dict[str, Any], tenant_id: str) -> Tuple[int, Dict[str, Any]]:
    payload = parse_body(event)
    require_known_fields(payload, ANALYZE_FIELDS)

    query = validate_query(payload)
    dataset_key = validate_dataset_key(payload.get("dataset_key"), tenant_id)
    page_context = validate_page_context(payload.get("page_context"))
    if not dataset_key and not page_context:
        raise bad_request(
            "Attach a dataset before running an analysis.",
            code="DATASET_REQUIRED",
        )
    _assert_dataset_exists(dataset_key)

    discipline = normalize_discipline(payload.get("discipline"))
    model_id = validate_model_id(payload.get("model_id"), PRIMARY_MODEL)
    chart_type = normalize_chart_type(payload.get("chart_type"))
    chart_columns = validate_chart_columns(payload.get("chart_columns"))

    job_payload = {
        "query": query,
        "dataset_key": dataset_key,
        "page_context": page_context,
        "discipline": discipline,
        "model_id": model_id,
        "chart_type": chart_type,
        "chart_columns": chart_columns,
        "generate_chart": bool(payload.get("generate_chart", True)),
    }

    supplied = _headers(event).get("x-idempotency-key")
    # The whole normalized payload seeds the job id: the same key with a
    # different dataset, model or chart request is a different job, not a replay.
    job_id = _job_id(tenant_id, job_payload, supplied)
    created = repository.create_job(
        tenant_id=tenant_id,
        job_id=job_id,
        mode="analyze",
        query=query,
        dataset_key=dataset_key,
        discipline=discipline,
        model_id=model_id,
    )
    _submit(tenant_id, job_id, "analyze", job_payload, created)

    if created is not None:
        metrics.add_metric(name="AnalysisSubmitted", unit=MetricUnit.Count, value=1)
    return 202, {"status": "QUEUED", "job_id": job_id, "poll": f"/jobs/{job_id}"}


def _query(event: Dict[str, Any], tenant_id: str) -> Tuple[int, Dict[str, Any]]:
    payload = parse_body(event)
    require_known_fields(payload, SQL_FIELDS)

    sql = validate_sql(payload)
    dataset_key = validate_dataset_key(payload.get("dataset_key"), tenant_id, required=True)
    assert_owned_key(dataset_key, tenant_id)
    _assert_dataset_exists(dataset_key)

    job_payload = {"sql": sql, "dataset_key": dataset_key}
    supplied = _headers(event).get("x-idempotency-key")
    job_id = _job_id(tenant_id, job_payload, supplied)
    created = repository.create_job(
        tenant_id=tenant_id, job_id=job_id, mode="sql", query="direct sql execution", dataset_key=dataset_key
    )
    _submit(tenant_id, job_id, "sql", job_payload, created)

    if created is not None:
        metrics.add_metric(name="SqlSubmitted", unit=MetricUnit.Count, value=1)
    return 202, {"status": "QUEUED", "job_id": job_id, "poll": f"/jobs/{job_id}"}


def _get_job(event: Dict[str, Any], tenant_id: str) -> Tuple[int, Dict[str, Any]]:
    path_params = event.get("pathParameters") or {}
    job_id = path_params.get("job_id") or path_params.get("proxy") or ""
    try:
        uuid.UUID(str(job_id))
    except (ValueError, AttributeError, TypeError):
        raise bad_request("'job_id' must be a UUID.", code="INVALID_JOB_ID") from None

    job = repository.get_job(tenant_id, job_id)
    if not job:
        raise not_found("Analysis job not found.")

    body: Dict[str, Any] = {
        "job_id": job["job_id"],
        "status": job.get("status"),
        "mode": job.get("mode"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "attempts": job.get("attempts", 0),
    }
    if job.get("error"):
        body["error"] = job["error"]
    if job.get("usage"):
        body["usage"] = job["usage"]

    if job.get("status") == repository.STATUS_COMPLETED and job.get("result_key"):
        try:
            body["result"] = json.loads(storage.get_json(DATA_BUCKET, job["result_key"]))
        except AppError:
            body["status"] = repository.STATUS_FAILED
            body["error"] = {
                "code": "RESULT_UNAVAILABLE",
                "message": "The result artifact is no longer available.",
                "retryable": False,
            }
    return 200, body


# -- entry point -------------------------------------------------------------


@logger.inject_lambda_context(correlation_id_path='headers."x-correlation-id"')
@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    request_id = _request_id(context, event)
    started = time.time()
    metrics.add_metric(name="Requests", unit=MetricUnit.Count, value=1)

    method, path = _route(event)
    path = path.rstrip("/") or "/"
    if method == "OPTIONS":
        return build_response(204, {}, request_id)

    try:
        tenant_id = get_tenant_id(event)

        if path == "/health" and method == "GET":
            return build_response(200, _health(), request_id)

        if path == "/upload/presign" and method == "POST":
            status, body = _presign(event, tenant_id)
        elif path == "/analyze" and method == "POST":
            status, body = _analyze(event, tenant_id)
        elif path == "/query" and method == "POST":
            status, body = _query(event, tenant_id)
        elif path.endswith("/jobs") or "/jobs/" in path:
            status, body = _get_job(event, tenant_id)
        else:
            raise not_found(f"No route matches {method} {path}.")

        metrics.add_metric(
            name="ApiLatency", unit=MetricUnit.Milliseconds, value=(time.time() - started) * 1000
        )
        return build_response(status, body, request_id)

    except AppError as exc:
        logger.warning("Request failed code=%s status=%s", exc.code, exc.status)
        metrics.add_metric(name="ClientErrors", unit=MetricUnit.Count, value=1)
        return build_response(exc.status, exc.to_payload(request_id), request_id)

    except Exception as exc:  # pragma: no cover - defensive boundary
        logger.exception("Unhandled API error")
        metrics.add_metric(name="ServerErrors", unit=MetricUnit.Count, value=1)
        return build_response(500, internal(str(exc)).to_payload(request_id), request_id)
