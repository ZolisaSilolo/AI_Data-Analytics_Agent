"""
SQS worker: the only place heavy (multi-second) analysis runs.

Invoked by ``AnalysisQueue`` with one record per job. The worker owns the
300 second budget, so Bedrock tool loops and DuckDB scans never collide with
the HTTP API 30 second integration limit.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

import repository
import storage
from errors import AppError
from services.analysis import run_analysis, run_sql

logger = Logger(service="data-analyst-worker")
metrics = Metrics(namespace="DataAnalystAgent", service="data-analyst-worker")
tracer = Tracer(service="data-analyst-worker")

DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
# Must match the queue's RedrivePolicy.maxReceiveCount: the last delivery is the
# one that is allowed to write a terminal FAILED state.
MAX_RECEIVE_COUNT = int(os.environ.get("MAX_RECEIVE_COUNT", "3"))


def _process(record: Dict[str, Any]) -> None:
    envelope = json.loads(record["body"])
    tenant_id = envelope["tenant_id"]
    job_id = envelope["job_id"]
    mode = envelope.get("mode", "analyze")
    payload = envelope.get("payload") or {}

    attempt = int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))
    final_attempt = attempt >= MAX_RECEIVE_COUNT

    # SQS is at-least-once. A redelivery of a finished job must not re-bill
    # Bedrock or overwrite a terminal status.
    existing = repository.get_job(tenant_id, job_id)
    if existing is not None and existing.get("status") in repository.TERMINAL_STATUSES:
        logger.info("Skipping job already in terminal state %s", existing.get("status"))
        metrics.add_metric(name="JobDeliverySkipped", unit=MetricUnit.Count, value=1)
        return

    repository.increment_attempts(tenant_id, job_id)
    logger.append_keys(job_id=job_id, tenant_id=tenant_id, mode=mode)

    started = time.time()
    try:
        if mode == "sql":
            result = run_sql(payload)
        else:
            result = run_analysis(payload)

        result["job_id"] = job_id
        result["completed_at"] = int(time.time())

        artifact_key = storage.build_artifact_key(tenant_id, job_id)
        storage.put_json(DATA_BUCKET, artifact_key, json.dumps(result, default=str))

        repository.update_job(
            tenant_id,
            job_id,
            status=repository.STATUS_COMPLETED,
            result_key=artifact_key,
            usage=result.get("usage") or {"total_tokens": 0},
            completed_at=int(time.time()),
        )

        metrics.add_metric(name="JobCompleted", unit=MetricUnit.Count, value=1)
        metrics.add_metric(
            name="JobDuration", unit=MetricUnit.Seconds, value=time.time() - started
        )

    except AppError as exc:
        if exc.retryable and not final_attempt:
            # Recoverable (for example Bedrock throttling): back off through SQS
            # rather than telling the client the analysis is dead.
            logger.warning("Job deferred code=%s attempt=%s", exc.code, attempt)
            repository.mark_retrying(tenant_id, job_id, exc.code, exc.message)
            metrics.add_metric(name="JobRetrying", unit=MetricUnit.Count, value=1)
            raise

        # Permanent, actionable failure: do not burn retries.
        logger.warning("Job rejected code=%s attempt=%s", exc.code, attempt)
        repository.mark_failed(tenant_id, job_id, exc.code, exc.message, retryable=exc.retryable)
        metrics.add_metric(name="JobRejected", unit=MetricUnit.Count, value=1)

    except Exception:
        # Transient/unknown: record it, then re-raise so SQS retries and the DLQ
        # captures the poison message after maxReceiveCount. The job is only
        # marked FAILED on the final delivery.
        logger.exception("Job failed (attempt %s of %s)", attempt, MAX_RECEIVE_COUNT)
        if final_attempt:
            repository.mark_failed(
                tenant_id, job_id, "INTERNAL", "Analysis failed unexpectedly.", retryable=True
            )
            metrics.add_metric(name="JobFailed", unit=MetricUnit.Count, value=1)
        else:
            repository.mark_retrying(
                tenant_id, job_id, "INTERNAL", "Analysis failed; it will be retried."
            )
            metrics.add_metric(name="JobRetrying", unit=MetricUnit.Count, value=1)
        raise


@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    metrics.add_metric(name="WorkerInvocations", unit=MetricUnit.Count, value=1)
    failures: List[Dict[str, str]] = []
    for record in event.get("Records", []):
        try:
            _process(record)
        except Exception:
            message_id = record.get("messageId")
            if not message_id:  # pragma: no cover - SQS always supplies it
                raise
            # Reported instead of raised so sibling messages in the batch are
            # acknowledged; the redrive policy handles the poison message.
            failures.append({"itemIdentifier": str(message_id)})
    return {"batchItemFailures": failures}
