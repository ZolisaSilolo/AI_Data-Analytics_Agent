"""Request validation, tenant scoping and payload limits."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from errors import (
    AppError,
    bad_request,
    forbidden,
    invalid_dataset_key,
    payload_too_large,
)

MAX_QUERY_CHARS = int(os.environ.get("MAX_QUERY_CHARS", "4000"))
MAX_SQL_CHARS = int(os.environ.get("MAX_SQL_CHARS", "20000"))
# The worker receives the job over SQS, whose body limit is 256 KB. Keep the
# accepted page context well below it so validation, not the queue, rejects an
# oversized extraction.
MAX_PAGE_CONTEXT_BYTES = int(os.environ.get("MAX_PAGE_CONTEXT_BYTES", "200000"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
# Hard ceiling on rows lifted out of extracted page tables (not configurable:
# the extension already caps each table, this bounds a multi-table payload).
MAX_PAGE_CONTEXT_RECORDS = 5000

PUBLIC_TENANT = "public"

DATASET_KEY_RE = re.compile(
    r"^uploads/(?P<tenant>[A-Za-z0-9_-]{1,64})/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(?P<ext>csv|parquet)$"
)

DISCIPLINES = {
    "general": "General Exploratory",
    "product": "Product Analytics",
    "financial": "Financial & RevOps",
    "operations": "Operations & Supply Chain",
    "growth": "Marketing & Growth",
    "clinical": "Clinical & Biotech",
}

DISCIPLINE_ALIASES = {
    "general exploratory": "general",
    "general": "general",
    "product analytics": "product",
    "product": "product",
    "financial & revops": "financial",
    "financial": "financial",
    "operations & supply chain": "operations",
    "operations": "operations",
    "marketing & growth": "growth",
    "growth": "growth",
    "clinical & biotech": "clinical",
    "clinical": "clinical",
}

CHART_TYPES = {
    "histogram",
    "bar",
    "line",
    "scatter",
    "box",
    "correlation_matrix",
    "waterfall",
}

# Models this build has been reviewed against, in the reference account and
# region. Matching is exact: prefix matching would let a caller select any model
# the account happens to have enabled, including ones the prompt and tool schema
# were never tuned for. Anything else (for example an Anthropic model after the
# use-case form is approved) must be enabled explicitly through
# ``BEDROCK_PRIMARY_MODEL``, ``BEDROCK_FALLBACK_MODEL`` or
# ``BEDROCK_ALLOWED_MODELS`` for that deployment.
_VERIFIED_MODELS = ("global.moonshotai.kimi-k3",)


def allowed_model_ids() -> frozenset:
    """Exact allow-list: reviewed models plus whatever this stack is configured with."""
    ids = set(_VERIFIED_MODELS)
    for var in ("BEDROCK_PRIMARY_MODEL", "BEDROCK_FALLBACK_MODEL"):
        configured = (os.environ.get(var) or "").strip()
        if configured:
            ids.add(configured)
    extra = os.environ.get("BEDROCK_ALLOWED_MODELS", "")
    ids.update(part.strip() for part in extra.split(",") if part.strip())
    return frozenset(ids)


def get_tenant_id(event: Dict[str, Any]) -> str:
    """
    Resolve the caller's tenant.

    Phase 1 replaces this with a Cognito JWT authorizer claim. Until then the
    value is taken from the authorizer context when present, otherwise from the
    ``x-tenant-id`` header, otherwise the isolated ``public`` workspace. The
    dataset key regex always binds a key to the resolved tenant.
    """
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    candidate = claims.get("sub") or _headers(event).get("x-tenant-id")
    if not candidate:
        return PUBLIC_TENANT
    candidate = str(candidate).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", candidate):
        raise forbidden("Invalid workspace identity.")
    return candidate


def _headers(event: Dict[str, Any]) -> Dict[str, str]:
    raw = event.get("headers") or {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a JSON request body, tolerating API Gateway v1/v2 and direct invokes."""
    raw = event.get("body")
    if raw is None:
        return event if isinstance(event, dict) and "query" in event else {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        if len(raw) > MAX_PAGE_CONTEXT_BYTES * 2:
            raise payload_too_large("Request body exceeds the maximum allowed size.")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise bad_request(f"Request body is not valid JSON: {exc.msg}.") from exc
        if not isinstance(parsed, dict):
            raise bad_request("Request body must be a JSON object.")
        return parsed
    raise bad_request("Unsupported request body type.")


def validate_query(payload: Dict[str, Any]) -> str:
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise bad_request("'query' is required and must be a non-empty string.")
    query = query.strip()
    if len(query) > MAX_QUERY_CHARS:
        raise bad_request(
            f"'query' exceeds the maximum length of {MAX_QUERY_CHARS} characters."
        )
    return query


def validate_sql(payload: Dict[str, Any]) -> str:
    sql = payload.get("sql")
    if not isinstance(sql, str) or not sql.strip():
        raise bad_request("'sql' is required and must be a non-empty string.")
    sql = sql.strip()
    if len(sql) > MAX_SQL_CHARS:
        raise bad_request(f"'sql' exceeds the maximum length of {MAX_SQL_CHARS} characters.")
    return sql


def normalize_discipline(value: Any) -> str:
    if value is None:
        return "general"
    if not isinstance(value, str):
        raise bad_request("'discipline' must be a string.")
    key = DISCIPLINE_ALIASES.get(value.strip().lower())
    if not key:
        raise bad_request(
            "'discipline' must be one of: " + ", ".join(sorted(DISCIPLINES.values())) + "."
        )
    return key


def validate_model_id(value: Any, default: str) -> str:
    if value is None or value == "":
        return default
    if not isinstance(value, str) or len(value) > 200:
        raise bad_request("'model_id' must be a string.")
    model_id = value.strip()
    if model_id not in allowed_model_ids():
        raise bad_request(
            "'model_id' is not approved for this deployment. Deploy with "
            "BedrockModelId/BedrockAllowedModels set to that model id first.",
            code="MODEL_NOT_APPROVED",
        )
    return model_id


def normalize_chart_type(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or value.strip().lower() not in CHART_TYPES:
        raise bad_request("'chart_type' must be one of: " + ", ".join(sorted(CHART_TYPES)) + ".")
    return value.strip().lower()


def validate_chart_columns(columns: Any) -> Dict[str, Optional[str]]:
    if columns is None:
        return {"x": None, "y": None, "color": None}
    if isinstance(columns, list):
        x = columns[0] if len(columns) > 0 else None
        y = columns[1] if len(columns) > 1 else None
        color = columns[2] if len(columns) > 2 else None
    elif isinstance(columns, dict):
        x, y, color = columns.get("x"), columns.get("y"), columns.get("color")
    else:
        raise bad_request("'chart_columns' must be a list or object.")
    for name, val in (("x", x), ("y", y), ("color", color)):
        if val is not None and (not isinstance(val, str) or len(val) > 128):
            raise bad_request(f"'chart_columns.{name}' must be a column name string.")
    return {"x": x, "y": y, "color": color}


def validate_dataset_key(value: Any, tenant_id: str, required: bool = False) -> Optional[str]:
    if value is None or value == "":
        if required:
            raise bad_request("'dataset_key' is required. Upload a dataset first.")
        return None
    if not isinstance(value, str):
        raise invalid_dataset_key()
    key = value.strip()
    match = DATASET_KEY_RE.fullmatch(key)
    if not match:
        raise invalid_dataset_key()
    if match.group("tenant") != tenant_id:
        raise forbidden("The dataset belongs to a different workspace.")
    return key


def validate_page_context(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise bad_request("'page_context' must be an object.")
    tables = value.get("tables")
    if tables is not None and not isinstance(tables, list):
        raise bad_request("'page_context.tables' must be a list.")
    try:
        size = len(
            json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
    except (TypeError, ValueError):
        raise bad_request("'page_context' must contain JSON-serialisable values.") from None
    if size > MAX_PAGE_CONTEXT_BYTES:
        raise payload_too_large("'page_context' exceeds the maximum allowed size.")
    return value


def validate_upload_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    filename = payload.get("filename") or payload.get("name")
    if not isinstance(filename, str) or not filename.strip():
        raise bad_request("'filename' is required.")
    filename = filename.strip()
    if len(filename) > 255:
        raise bad_request("'filename' is too long.")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"csv", "parquet"}:
        raise bad_request("Only .csv and .parquet uploads are supported.")

    try:
        size = int(payload.get("size") or 0)
    except (TypeError, ValueError):
        raise bad_request("'size' must be an integer number of bytes.") from None
    if size <= 0:
        raise bad_request("'size' must be greater than zero.")
    if size > MAX_UPLOAD_BYTES:
        raise payload_too_large(
            f"Uploads are limited to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    content_type = payload.get("content_type") or (
        "text/csv" if ext == "csv" else "application/vnd.apache.parquet"
    )
    if not isinstance(content_type, str) or len(content_type) > 128:
        raise bad_request("'content_type' is invalid.")

    return {"ext": ext, "size": size, "content_type": content_type}


def _table_parts(table: Any) -> Tuple[List[str], List[Any], int]:
    """Return ``(headers, rows, reported_rows)`` for one extracted table."""
    if not isinstance(table, dict):
        return [], [], 0
    headers = table.get("headers") or table.get("columns") or []
    rows = table.get("sampleRows") or table.get("sample_records") or []
    if not isinstance(headers, list) or not isinstance(rows, list):
        return [], [], 0
    try:
        reported = int(table.get("rowCount") or len(rows))
    except (TypeError, ValueError):
        reported = len(rows)
    return [str(h) for h in headers], rows, max(reported, 0)


def select_page_table(page_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Pick the table group worth analysing from an extracted page.

    A page usually holds several unrelated tables, and merging them blindly would
    mix schemas into one frame. Tables that share an identical header set are
    concatenated (the common paginated/split-table case). The group with the most
    reported rows wins, tie-broken by transmitted rows and then document order, so
    a large table that was only sampled is not beaten by a small complete one.
    """
    if not page_context:
        return None
    tables = page_context.get("tables") or []
    if not isinstance(tables, list):
        return None

    groups: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    order: List[Tuple[str, ...]] = []
    for table in tables:
        headers, rows, reported = _table_parts(table)
        if not headers or not rows:
            continue
        signature = tuple(headers)
        if signature not in groups:
            groups[signature] = {"headers": headers, "rows": [], "reported": 0}
            order.append(signature)
        groups[signature]["rows"].extend(rows)
        groups[signature]["reported"] += reported

    if not groups:
        return None

    best = max(
        order,
        key=lambda sig: (
            groups[sig]["reported"],
            len(groups[sig]["rows"]),
            -order.index(sig),
        ),
    )
    return groups[best]


def page_context_to_records(page_context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten the selected page table group into records."""
    selection = select_page_table(page_context)
    if not selection:
        return []

    headers = selection["headers"]
    records: List[Dict[str, Any]] = []
    for row in selection["rows"][:MAX_PAGE_CONTEXT_RECORDS]:
        if isinstance(row, dict):
            records.append({str(k): v for k, v in row.items()})
        elif isinstance(row, (list, tuple)):
            records.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
    return records


def page_context_reported_rows(page_context: Optional[Dict[str, Any]]) -> int:
    """Rows the page reported for the analysed table, even if only a sample was sent."""
    selection = select_page_table(page_context)
    return int(selection["reported"]) if selection else 0


def require_known_fields(payload: Dict[str, Any], allowed: set) -> None:
    """Reject unknown top-level fields to keep the contract tight."""
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise AppError(
            "UNKNOWN_FIELDS",
            "Unsupported request fields: " + ", ".join(unknown) + ".",
            status=400,
        )
