"""
Deterministic SQL builder for ``query_metric``.

The model supplies *which* metric, *how to group*, and typed filters. This
module supplies the formula and the quoting, so a defined metric cannot drift
between runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .catalog import BoundMetric, quote_identifier

_ALLOWED_OPS = {
    "=": "=",
    "!=": "<>",
    ">": ">",
    ">=": ">=",
    "<": "<",
    "<=": "<=",
    "in": "IN",
    "not_in": "NOT IN",
    "is_null": "IS NULL",
    "not_null": "IS NOT NULL",
}
MAX_LIMIT = 1000


class MetricQueryError(ValueError):
    """Raised when a metric query cannot be compiled deterministically."""


@dataclass(frozen=True)
class MetricFilter:
    column: str
    op: str
    value: Any = None


def _literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise MetricQueryError("Non-finite numeric filter values are not allowed.")
        return repr(value)
    text = str(value)
    if len(text) > 200:
        raise MetricQueryError("Filter values must be 200 characters or fewer.")
    return "'" + text.replace("'", "''") + "'"


def filter_sql(filters: Sequence[MetricFilter], columns: Iterable[str]) -> str:
    known = list(columns)
    clauses: List[str] = []
    for item in filters:
        if item.column not in known:
            raise MetricQueryError(f"Unknown filter column: {item.column}")
        op = str(item.op or "").lower()
        if op not in _ALLOWED_OPS:
            raise MetricQueryError(f"Unsupported filter operator: {item.op}")
        column = quote_identifier(item.column)
        if op in ("is_null", "not_null"):
            clauses.append(f"{column} {_ALLOWED_OPS[op]}")
            continue
        if op in ("in", "not_in"):
            values = item.value if isinstance(item.value, (list, tuple)) else [item.value]
            if not values:
                raise MetricQueryError("IN filters need at least one value.")
            rendered = ", ".join(_literal(v) for v in values[:100])
            clauses.append(f"{column} {_ALLOWED_OPS[op]} ({rendered})")
            continue
        clauses.append(f"{column} {_ALLOWED_OPS[op]} {_literal(item.value)}")
    return " AND ".join(clauses)


def compile_metric_query(
    metric: BoundMetric,
    columns: Sequence[str],
    group_by: Optional[Sequence[str]] = None,
    filters: Optional[Sequence[MetricFilter]] = None,
    order: str = "desc",
    limit: int = 100,
) -> str:
    """Build a single read-only SELECT for one bound metric."""
    known = list(columns)
    group = list(group_by or [])
    if len(group) != len(set(group)):
        raise MetricQueryError("group_by contains duplicate columns.")
    for column in group:
        if column not in known:
            raise MetricQueryError(f"Unknown group_by column: {column}")

    direction = "ASC" if str(order).lower() == "asc" else "DESC"
    try:
        safe_limit = max(1, min(int(limit), MAX_LIMIT))
    except (TypeError, ValueError) as exc:
        raise MetricQueryError("limit must be an integer.") from exc

    select = [quote_identifier(c) for c in group]
    select.append(f"{metric.sql} AS {quote_identifier(metric.name)}")
    where = filter_sql(list(filters or []), known)

    # All identifiers are validated against the dataset schema and quoted, and all
    # values are escaped by filter_sql; this is guarded construction, not injection.
    sql = "SELECT " + ", ".join(select) + " FROM dataset"  # noqa: S608
    if where:
        sql += " WHERE " + where
    if group:
        sql += " GROUP BY " + ", ".join(quote_identifier(c) for c in group)
    sql += f" ORDER BY {quote_identifier(metric.name)} {direction}"
    sql += f" LIMIT {safe_limit}"
    return sql


def metric_names(metrics: Dict[str, BoundMetric]) -> Tuple[str, ...]:
    return tuple(sorted(metrics))


def normalize_metric_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(name or "").lower())
