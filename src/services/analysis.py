"""Shared analysis pipeline used by the async worker and direct SQL mode."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from botocore.exceptions import ClientError

from agent.bedrock_core import DATASET_TABLE, BedrockAgentCore
from api.validation import (
    DISCIPLINES,
    page_context_reported_rows,
    page_context_to_records,
    validate_chart_columns,
)
from core.data_handler import DataHandler
from dataprof.schema_card import build_schema_card, card_summary
from engine.invariants import InvariantChecker
from engine.sandbox import DeterministicSandbox
from errors import (
    AppError,
    bad_request,
    bedrock_unavailable,
    internal,
    invalid_chart_columns,
    model_access_denied,
    query_rejected,
    sql_execution_error,
    throttled,
)
from semantic import load_catalog
from verify.claims import verify_claims

logger = logging.getLogger(__name__)

MAX_CHART_ROWS = 5000
MAX_DIRECT_ROWS = 200

# Bedrock failures that mean "this deployment cannot use the model" rather than
# "the analysis was wrong". Mapped to a stable client error instead of INTERNAL
# so the client learns the cause and the job is not retried into the same wall.
_MODEL_ACCESS_ERRORS = {
    "AccessDeniedException",
    "ResourceNotFoundException",
    "ModelNotReadyException",
}
_TRANSIENT_BEDROCK_ERRORS = {
    "ThrottlingException",
    "TooManyRequestsException",
    "ServiceQuotaExceededException",
}
_UNAVAILABLE_BEDROCK_ERRORS = {
    "ModelTimeoutException",
    "ModelErrorException",
    "InternalServerException",
    "ServiceUnavailableException",
}

_CATALOG = None


def _catalog():
    """Load the metric catalogue once per process."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_catalog()
    return _CATALOG


def _translate_bedrock_error(exc: ClientError) -> AppError:
    code = exc.response.get("Error", {}).get("Code", "")
    if code in _TRANSIENT_BEDROCK_ERRORS:
        return throttled()
    if code in _MODEL_ACCESS_ERRORS:
        return model_access_denied()
    if code in _UNAVAILABLE_BEDROCK_ERRORS:
        return bedrock_unavailable()
    return internal(f"bedrock call failed: {code}")


def _bucket() -> str:
    bucket = os.environ.get("DATA_BUCKET", "")
    if not bucket:
        raise bad_request("The data lakehouse is not configured.", code="NOT_CONFIGURED")
    return bucket


def load_dataset(payload: Dict[str, Any]) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Resolve the request's dataset: a validated S3 key takes precedence, then
    tables extracted by the browser extension.
    """
    dataset_key = payload.get("dataset_key")
    if dataset_key:
        df = DataHandler().load_from_s3(_bucket(), dataset_key)
        if df.empty:
            raise bad_request("The uploaded dataset is empty.", code="EMPTY_DATASET")
        return df, dataset_key

    records = page_context_to_records(payload.get("page_context"))
    if records:
        df = pd.DataFrame(records)
        if df.empty:
            raise bad_request("The extracted page contained no usable rows.", code="EMPTY_DATASET")
        return df, None

    raise bad_request(
        "No dataset is attached. Upload a CSV/Parquet file or extract a table first.",
        code="DATASET_REQUIRED",
    )


def _infer_chart_type(df: pd.DataFrame) -> str:
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric = [c for c in df.columns if c not in numeric]
    if len(df.columns) == 1 and numeric:
        return "histogram"
    if len(numeric) >= 2 and not non_numeric:
        return "scatter"
    if len(numeric) >= 2 and non_numeric:
        return "bar"
    if numeric:
        return "histogram"
    return "bar"


def _build_chart(
    agent: BedrockAgentCore,
    request_query: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    last = getattr(agent, "last_sql_result", None)
    if not last or last.get("status") != "SUCCESS":
        return None
    rows = last.get("data") or []
    columns = last.get("columns") or []
    if not rows or not columns:
        return None

    df = pd.DataFrame(rows)
    df = df.head(MAX_CHART_ROWS)

    requested = validate_chart_columns(request_query.get("chart_columns"))
    chart_type = request_query.get("chart_type") or _infer_chart_type(df)

    for label, column in requested.items():
        if column is not None and column not in df.columns:
            raise invalid_chart_columns(
                f"Chart column '{column}' ({label}) does not exist in the query result. "
                f"Available columns: {', '.join(map(str, df.columns))}."
            )

    x_column = requested["x"] or (columns[0] if columns else None)
    y_column = requested["y"]
    if y_column is None and chart_type not in ("histogram", "correlation_matrix") and len(columns) > 1:
        y_column = columns[1]

    from core.visualizations import VisualizationGenerator

    fig = VisualizationGenerator.generate_chart(
        df,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        color_column=requested["color"],
    )
    return VisualizationGenerator.export_figure_json(fig)


def run_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the Bedrock agent over a dataset and return a client-safe result."""
    started = time.time()
    df, dataset_key = load_dataset(payload)

    sandbox = DeterministicSandbox()
    sandbox.register_dataframe(DATASET_TABLE, df)

    discipline_key = payload.get("discipline") or "general"
    if discipline_key not in DISCIPLINES:
        discipline_key = "general"

    card = build_schema_card(df)
    catalog = _catalog()
    bound = catalog.bind(df.columns)

    agent = BedrockAgentCore(
        sandbox=sandbox,
        primary_model=payload.get("model_id"),
        discipline=discipline_key,
        schema_card=card.render(),
        metrics=bound,
        metric_prompt=catalog.render_prompt(bound),
    )
    try:
        agent_result = agent.run_conversation(user_prompt=payload["query"])
    except ClientError as exc:
        raise _translate_bedrock_error(exc) from exc

    narrative_facts = [float(len(df)), float(len(df.columns))]
    narrative_facts.extend(agent_result.get("facts") or [])
    verification = verify_claims(agent_result.get("analysis") or "", narrative_facts)
    warnings = []
    if verification["status"] == "REVIEW":
        warnings.append(
            f"{verification['unsupported_count']} number(s) in the narrative are not "
            "backed by a tool result; review before sharing."
        )
    if card.truncated:
        warnings.append(f"Only the first {len(card.columns)} columns were profiled.")

    chart_spec = None
    chart_error = None
    if payload.get("generate_chart", True):
        try:
            chart_spec = _build_chart(agent, payload)
        except Exception as exc:  # charting must never fail the analysis
            logger.warning("Chart generation skipped: %s", type(exc).__name__)
            chart_error = str(exc)

    last_sql = getattr(agent, "last_sql_result", None) or {}
    # Check the frame the answer is actually based on: the last SQL result when
    # the model ran one, otherwise the dataset itself.
    invariants = last_sql.get("invariants") or InvariantChecker.run_suite(df)

    reported_rows = page_context_reported_rows(payload.get("page_context"))
    dataset: Dict[str, Any] = {
        "key": dataset_key,
        "source": "s3" if dataset_key else "page_context",
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
        # The extension transmits at most 200 rows per table, so say so instead
        # of implying the whole page was analysed.
        "sampled": bool(not dataset_key and reported_rows > len(df)),
    }
    if reported_rows and not dataset_key:
        dataset["reported_row_count"] = reported_rows

    result: Dict[str, Any] = {
        "status": agent_result.get("status", "SUCCESS"),
        "mode": "analyze",
        "analysis": agent_result.get("analysis"),
        "model_used": agent_result.get("model_used"),
        "usage": agent_result.get("usage", {}),
        "rounds": agent_result.get("rounds"),
        "tool_executions": agent_result.get("tool_executions", []),
        "chart_spec": chart_spec,
        "chart_error": chart_error,
        "invariants": invariants,
        "verification": verification,
        "warnings": warnings,
        "dataset": dataset,
        "dataset_profile": card_summary(card),
        "metrics": {
            "catalog_version": catalog.version,
            "available": sorted(bound),
        },
        "discipline": discipline_key,
        "execution_time_seconds": round(time.time() - started, 3),
    }
    return result


def run_sql(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single guarded read-only SQL statement (no LLM cost)."""
    started = time.time()
    df, dataset_key = load_dataset(payload)

    sandbox = DeterministicSandbox()
    sandbox.register_dataframe(DATASET_TABLE, df)
    execution = sandbox.execute_sql(payload["sql"])

    if execution.get("status") == "SECURITY_VIOLATION":
        raise query_rejected(execution.get("error", "Query rejected."))
    if execution.get("status") == "ERROR":
        raise sql_execution_error()

    rows = execution.get("data") or []
    return {
        "status": "SUCCESS",
        "mode": "sql",
        "engine": execution.get("engine"),
        "columns": execution.get("columns", []),
        "row_count": execution.get("row_count", 0),
        "truncated": execution.get("truncated", False) or len(rows) > MAX_DIRECT_ROWS,
        "data": rows[:MAX_DIRECT_ROWS],
        "invariants": execution.get("invariants"),
        "execution_time_ms": execution.get("execution_time_ms", 0),
        "dataset": {
            "key": dataset_key,
            "source": "s3" if dataset_key else "page_context",
            "row_count": int(len(df)),
            "sampled": False,
        },
        "execution_time_seconds": round(time.time() - started, 3),
    }
