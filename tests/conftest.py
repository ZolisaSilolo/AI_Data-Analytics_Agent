"""Shared test configuration: fake AWS env before any module import."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("JOBS_TABLE", "jobs")
os.environ.setdefault("DATA_BUCKET", "test-lakehouse")
os.environ.setdefault("ANALYSIS_QUEUE_URL", "http://queue")
os.environ.setdefault("ALLOWED_ORIGIN", "http://localhost:5173")
os.environ.setdefault("BEDROCK_PRIMARY_MODEL", "global.moonshotai.kimi-k3")

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)


class FakeContext:
    aws_request_id = "test-request-id"
    function_name = "test-function"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    log_group_name = "/aws/lambda/test"
    log_stream_name = "stream"

    def get_remaining_time_in_millis(self) -> int:  # noqa: D401
        return 300_000
