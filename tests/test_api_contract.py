"""End-to-end API contract tests against mocked AWS (moto)."""

from __future__ import annotations

import json
import uuid

import boto3
import pytest
from moto import mock_aws

import lambda_function
import repository
import worker

BUCKET = "test-lakehouse"
TABLE = "jobs"
ORIGIN = "http://localhost:5173"


class Ctx:
    aws_request_id = "test-request-id"
    function_name = "test-api"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    log_group_name = "/aws/lambda/test"
    log_stream_name = "stream"

    def get_remaining_time_in_millis(self) -> int:
        return 300_000


def event(path: str, body=None, method: str = "POST", headers=None, path_params=None):
    return {
        "rawPath": path,
        "requestContext": {"http": {"method": method}, "requestId": "req-1"},
        "headers": {"x-correlation-id": "corr-1", **(headers or {})},
        "body": json.dumps(body) if body is not None else None,
        "pathParameters": path_params or {},
    }


def payload(response):
    return json.loads(response["body"])


def upload(key: str) -> str:
    """Create the S3 object the API now HEAD-checks before enqueueing."""
    boto3.client("s3", region_name="us-east-1").put_object(
        Bucket=BUCKET, Key=key, Body=b"region,revenue\nAMER,100\nEMEA,50\n"
    )
    return key


@pytest.fixture()
def aws_env(monkeypatch):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName=TABLE,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "tenant_id", "AttributeType": "S"},
                {"AttributeName": "job_id", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "tenant_id", "KeyType": "HASH"},
                {"AttributeName": "job_id", "KeyType": "RANGE"},
            ],
        )
        queue_url = boto3.client("sqs", region_name="us-east-1").create_queue(
            QueueName="analysis"
        )["QueueUrl"]

        monkeypatch.setattr(lambda_function, "DATA_BUCKET", BUCKET)
        monkeypatch.setattr(lambda_function, "QUEUE_URL", queue_url)
        monkeypatch.setattr(lambda_function, "ALLOWED_ORIGIN", ORIGIN)
        monkeypatch.setattr(worker, "DATA_BUCKET", BUCKET)
        monkeypatch.setattr(repository, "_TABLE", TABLE)

        yield {"queue_url": queue_url}


def test_health(aws_env):
    res = lambda_function.lambda_handler(event("/health", method="GET"), Ctx())
    assert res["statusCode"] == 200
    body = payload(res)
    assert body["status"] == "ok"
    assert body["queue_configured"] is True
    assert res["headers"]["Access-Control-Allow-Origin"] == ORIGIN


def test_unknown_route_returns_404(aws_env):
    res = lambda_function.lambda_handler(event("/nope"), Ctx())
    assert res["statusCode"] == 404
    assert payload(res)["error"]["code"] == "NOT_FOUND"


def test_stage_prefixed_path_is_routed(aws_env, monkeypatch):
    """API Gateway named stages put the stage in rawPath (/dev/health)."""
    monkeypatch.setenv("STAGE_NAME", "dev")
    staged = event("/dev/health", method="GET")
    res = lambda_function.lambda_handler(staged, Ctx())
    assert res["statusCode"] == 200
    assert payload(res)["status"] == "ok"


def test_route_key_wins_over_raw_path(aws_env, monkeypatch):
    """A staged /analyze path still resolves to the analyze route."""
    monkeypatch.setenv("STAGE_NAME", "dev")
    staged = event("/dev/analyze", {"query": "hi"})
    res = lambda_function.lambda_handler(staged, Ctx())
    assert res["statusCode"] == 400
    assert payload(res)["error"]["code"] == "DATASET_REQUIRED"


def test_presign_returns_tenant_scoped_key(aws_env):
    res = lambda_function.lambda_handler(
        event("/upload/presign", {"filename": "sales.csv", "size": 2048}), Ctx()
    )
    assert res["statusCode"] == 200
    body = payload(res)
    assert body["dataset_key"].startswith("uploads/public/")
    assert body["dataset_key"].endswith(".csv")
    assert "upload_url" in body and "upload_fields" in body


def test_presign_rejects_oversize(aws_env):
    res = lambda_function.lambda_handler(
        event("/upload/presign", {"filename": "big.csv", "size": 51 * 1024 * 1024}), Ctx()
    )
    assert res["statusCode"] == 413
    assert payload(res)["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_analyze_requires_dataset(aws_env):
    res = lambda_function.lambda_handler(
        event("/analyze", {"query": "What is revenue?"}), Ctx()
    )
    assert res["statusCode"] == 400
    assert payload(res)["error"]["code"] == "DATASET_REQUIRED"


def test_analyze_enqueues_and_is_idempotent(aws_env):
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    body = {"query": "Summarize revenue", "dataset_key": key, "discipline": "Financial & RevOps"}
    headers = {"x-idempotency-key": "abc-123"}

    first = lambda_function.lambda_handler(event("/analyze", body, headers=headers), Ctx())
    second = lambda_function.lambda_handler(event("/analyze", body, headers=headers), Ctx())

    assert first["statusCode"] == 202
    assert payload(first)["job_id"] == payload(second)["job_id"]

    job = repository.get_job("public", payload(first)["job_id"])
    assert job is not None
    assert job["status"] == repository.STATUS_QUEUED
    assert job["discipline"] == "financial"


def test_idempotency_key_is_scoped_to_the_whole_payload(aws_env):
    """The same key with a different dataset is a new job, not a silent replay."""
    first_key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    second_key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    headers = {"x-idempotency-key": "abc-123"}

    first = lambda_function.lambda_handler(
        event("/analyze", {"query": "Summarize revenue", "dataset_key": first_key}, headers=headers),
        Ctx(),
    )
    second = lambda_function.lambda_handler(
        event("/analyze", {"query": "Summarize revenue", "dataset_key": second_key}, headers=headers),
        Ctx(),
    )

    assert payload(first)["job_id"] != payload(second)["job_id"]


def test_analyze_rejects_missing_dataset_object(aws_env):
    res = lambda_function.lambda_handler(
        event("/analyze", {"query": "hi", "dataset_key": f"uploads/public/{uuid.uuid4()}.csv"}),
        Ctx(),
    )
    assert res["statusCode"] == 404
    assert payload(res)["error"]["code"] == "DATASET_NOT_FOUND"


def test_analyze_rejects_page_context_above_the_queue_budget(aws_env):
    res = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "page_context": {"tables": [], "blob": "x" * 210_000}}),
        Ctx(),
    )
    assert res["statusCode"] == 413
    assert payload(res)["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_oversized_job_envelope_fails_before_enqueue(aws_env):
    """SQS caps a body at 256 KB; the API must say so instead of returning 500."""
    with pytest.raises(lambda_function.AppError) as exc:
        lambda_function._enqueue(
            "public", "job-1", "analyze", {"page_context": {"blob": "x" * 300_000}}
        )
    assert exc.value.code == "PAYLOAD_TOO_LARGE"


def test_enqueue_failure_rolls_back_the_job_row(aws_env, monkeypatch):
    """A QUEUED row with no message would make every retry a no-op."""
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    headers = {"x-idempotency-key": "rollback-1"}
    original = lambda_function._enqueue

    def boom(*args, **kwargs):
        raise lambda_function.internal("sqs unavailable")

    monkeypatch.setattr(lambda_function, "_enqueue", boom)
    res = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "dataset_key": key}, headers=headers), Ctx()
    )
    assert res["statusCode"] == 500

    monkeypatch.setattr(lambda_function, "_enqueue", original)
    retry = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "dataset_key": key}, headers=headers), Ctx()
    )
    assert retry["statusCode"] == 202
    job = repository.get_job("public", payload(retry)["job_id"])
    assert job["status"] == repository.STATUS_QUEUED


def test_analyze_rejects_cross_tenant_key(aws_env):
    key = f"uploads/bob/{uuid.uuid4()}.csv"
    res = lambda_function.lambda_handler(
        event("/analyze", {"query": "hi", "dataset_key": key}, headers={"x-tenant-id": "alice"}),
        Ctx(),
    )
    assert res["statusCode"] == 403


def test_job_lifecycle_worker_completes(aws_env, monkeypatch):
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    submitted = lambda_function.lambda_handler(
        event("/analyze", {"query": "How many rows?", "dataset_key": key}), Ctx()
    )
    job_id = payload(submitted)["job_id"]

    monkeypatch.setattr(
        worker,
        "run_analysis",
        lambda request: {
            "status": "SUCCESS",
            "mode": "analyze",
            "analysis": "There are 3 rows.",
            "model_used": "global.moonshotai.kimi-k3",
            "usage": {"total_tokens": 42},
            "tool_executions": [],
            "dataset": {"row_count": 3},
        },
    )

    record = {
        "body": json.dumps(
            {
                "tenant_id": "public",
                "job_id": job_id,
                "mode": "analyze",
                "payload": {"query": "How many rows?", "dataset_key": key},
            }
        ),
        "attributes": {"ApproximateReceiveCount": "1"},
    }
    worker._process(record)

    res = lambda_function.lambda_handler(
        event(f"/jobs/{job_id}", method="GET", path_params={"job_id": job_id}), Ctx()
    )
    assert res["statusCode"] == 200
    body = payload(res)
    assert body["status"] == "COMPLETED"
    assert body["usage"]["total_tokens"] == 42
    assert body["result"]["analysis"] == "There are 3 rows."


def test_job_isolation_between_tenants(aws_env):
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    submitted = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "dataset_key": key}), Ctx()
    )
    job_id = payload(submitted)["job_id"]

    res = lambda_function.lambda_handler(
        event(f"/jobs/{job_id}", method="GET", path_params={"job_id": job_id},
              headers={"x-tenant-id": "alice"}),
        Ctx(),
    )
    assert res["statusCode"] == 404


def test_staged_job_path_resolves(aws_env, monkeypatch):
    monkeypatch.setenv("STAGE_NAME", "dev")
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    submitted = lambda_function.lambda_handler(
        event("/dev/analyze", {"query": "q", "dataset_key": key}), Ctx()
    )
    job_id = payload(submitted)["job_id"]

    res = lambda_function.lambda_handler(
        event(f"/dev/jobs/{job_id}", method="GET", path_params={"job_id": job_id}), Ctx()
    )
    assert res["statusCode"] == 200
    assert payload(res)["job_id"] == job_id


def test_worker_marks_failed_only_on_the_final_attempt(aws_env, monkeypatch):
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    submitted = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "dataset_key": key}), Ctx()
    )
    job_id = payload(submitted)["job_id"]

    def boom(request):
        raise RuntimeError("transient")

    monkeypatch.setattr(worker, "run_analysis", boom)
    record = {
        "body": json.dumps({"tenant_id": "public", "job_id": job_id, "mode": "analyze", "payload": {}}),
        "attributes": {"ApproximateReceiveCount": "1"},
    }
    with pytest.raises(RuntimeError):
        worker._process(record)

    # A retry is still coming, so the client must not see a terminal failure.
    job = repository.get_job("public", job_id)
    assert job["status"] == repository.STATUS_RETRYING
    assert job["error"]["retryable"] is True

    record["attributes"]["ApproximateReceiveCount"] = "3"
    with pytest.raises(RuntimeError):
        worker._process(record)

    job = repository.get_job("public", job_id)
    assert job["status"] == repository.STATUS_FAILED
    assert job["error"]["retryable"] is True
    assert int(job["attempts"]) == 2


def test_worker_skips_redelivery_of_a_completed_job(aws_env, monkeypatch):
    """SQS is at-least-once; a redelivery must not re-bill Bedrock."""
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    submitted = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "dataset_key": key}), Ctx()
    )
    job_id = payload(submitted)["job_id"]

    calls = []

    def fake_run(request):
        calls.append(request)
        return {
            "status": "SUCCESS",
            "mode": "analyze",
            "analysis": "done",
            "usage": {"total_tokens": 1},
            "tool_executions": [],
            "dataset": {"row_count": 2},
        }

    monkeypatch.setattr(worker, "run_analysis", fake_run)
    record = {
        "body": json.dumps({"tenant_id": "public", "job_id": job_id, "mode": "analyze", "payload": {}}),
        "attributes": {"ApproximateReceiveCount": "1"},
    }
    worker._process(record)
    worker._process(record)

    assert len(calls) == 1
    job = repository.get_job("public", job_id)
    assert job["status"] == repository.STATUS_COMPLETED
    assert int(job["attempts"]) == 1


def test_batch_handler_reports_only_failed_message_ids(aws_env, monkeypatch):
    key = upload(f"uploads/public/{uuid.uuid4()}.csv")
    submitted = lambda_function.lambda_handler(
        event("/analyze", {"query": "q", "dataset_key": key}), Ctx()
    )
    job_id = payload(submitted)["job_id"]

    def boom(request):
        raise RuntimeError("transient")

    monkeypatch.setattr(worker, "run_analysis", boom)
    event_body = {
        "Records": [
            {
                "messageId": "message-1",
                "body": json.dumps(
                    {"tenant_id": "public", "job_id": job_id, "mode": "analyze", "payload": {}}
                ),
                "attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    }
    result = worker.lambda_handler(event_body, Ctx())
    assert result == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
