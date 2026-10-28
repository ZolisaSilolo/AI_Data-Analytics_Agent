"""
Centralized application error contract.

Every failure surfaced to a client is an ``AppError`` with a stable machine
readable ``code``, a human-safe ``message`` and an HTTP ``status``. Internal
detail (stack traces, bucket names, model errors) is logged server-side only.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AppError(Exception):
    """A safe, client-facing application error."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        retryable: bool = False,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.retryable = retryable
        self.retry_after = retry_after

    def to_payload(self, request_id: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
                "request_id": request_id,
                "retryable": self.retryable,
            }
        }
        if self.retry_after is not None:
            body["error"]["retry_after"] = self.retry_after
        return body


# --- Canonical constructors -------------------------------------------------

def bad_request(message: str, code: str = "BAD_REQUEST") -> AppError:
    return AppError(code, message, status=400)


def unauthorized(message: str = "Authentication required.") -> AppError:
    return AppError("UNAUTHORIZED", message, status=401)


def forbidden(message: str = "You do not have access to this resource.") -> AppError:
    return AppError("FORBIDDEN", message, status=403)


def not_found(message: str = "Resource not found.") -> AppError:
    return AppError("NOT_FOUND", message, status=404)


def payload_too_large(message: str) -> AppError:
    return AppError("PAYLOAD_TOO_LARGE", message, status=413)


def invalid_dataset_key() -> AppError:
    return AppError(
        "INVALID_DATASET_KEY",
        "The dataset key is not valid for this workspace.",
        status=400,
    )


def invalid_chart_columns(message: str) -> AppError:
    return AppError("INVALID_CHART_COLUMNS", message, status=400)


def query_rejected(message: str) -> AppError:
    return AppError("QUERY_REJECTED", message, status=422)


def sql_execution_error() -> AppError:
    return AppError(
        "SQL_EXECUTION_ERROR",
        "The SQL query could not be executed. Check table and column names.",
        status=422,
    )


def quota_exceeded(retry_after: int) -> AppError:
    return AppError(
        "QUOTA_EXCEEDED",
        "Daily analysis quota exceeded for this workspace.",
        status=429,
        retryable=True,
        retry_after=retry_after,
    )


def throttled(retry_after: int = 5) -> AppError:
    return AppError(
        "BEDROCK_THROTTLED",
        "The analysis service is busy. Please retry shortly.",
        status=429,
        retryable=True,
        retry_after=retry_after,
    )


def model_access_denied() -> AppError:
    return AppError(
        "MODEL_ACCESS_DENIED",
        "The requested foundation model is not enabled for this deployment.",
        status=503,
    )


def bedrock_unavailable() -> AppError:
    return AppError(
        "BEDROCK_UNAVAILABLE",
        "The analysis model is temporarily unavailable. Please retry shortly.",
        status=503,
        retryable=True,
        retry_after=10,
    )


def internal(detail: Optional[str] = None) -> AppError:
    if detail:
        logger.error("Internal error: %s", detail)
    return AppError(
        "INTERNAL",
        "An internal error occurred. Quote the request id when contacting support.",
        status=500,
    )
