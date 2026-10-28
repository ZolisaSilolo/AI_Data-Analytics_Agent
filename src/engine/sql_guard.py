"""
SQL guard for the deterministic sandbox.

The LLM compiles business questions into SQL. That SQL is untrusted input: it
must never be able to touch the filesystem, install extensions, attach external
databases, reach the network, or mutate state. This module allows read-only
analytical statements only and rejects every known escape hatch by name.
"""

from __future__ import annotations

import re
from typing import Iterable

import sqlglot
from sqlglot import exp

# Root expression types that represent a read-only query.
_ALLOWED_ROOTS = tuple(
    node
    for node in (
        getattr(exp, "Select", None),
        getattr(exp, "Union", None),
        getattr(exp, "Intersect", None),
        getattr(exp, "Except", None),
        getattr(exp, "Subquery", None),
        getattr(exp, "Values", None),
    )
    if node is not None
)

# Any statement-level node outside the read-only allow-list.
_FORBIDDEN_STATEMENTS = tuple(
    node
    for node in (
        getattr(exp, "Copy", None),
        getattr(exp, "Attach", None),
        getattr(exp, "Detach", None),
        getattr(exp, "Create", None),
        getattr(exp, "Insert", None),
        getattr(exp, "Update", None),
        getattr(exp, "Delete", None),
        getattr(exp, "Drop", None),
        getattr(exp, "Alter", None),
        getattr(exp, "Command", None),
        getattr(exp, "Pragma", None),
        getattr(exp, "Set", None),
        getattr(exp, "Use", None),
        getattr(exp, "Export", None),
        getattr(exp, "Load", None),
        getattr(exp, "Grant", None),
        getattr(exp, "Transaction", None),
    )
    if node is not None
)

# Functions that read/write the filesystem, network or other databases.
_BLOCKED_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_parquet",
    "parquet_scan",
    "read_json",
    "read_json_auto",
    "read_ndjson",
    "read_ndjson_auto",
    "read_text",
    "read_blob",
    "read_xlsx",
    "glob",
    "sniff_csv",
    "http_get",
    "http_post",
    "httpfs",
    "shell",
    "getenv",
    "query",
    "query_table",
    "sqlite_scan",
    "postgres_scan",
    "mysql_scan",
    "st_read",
    "iceberg_scan",
    "delta_scan",
    "duckdb_extensions",
}

_URL_SCHEME_RE = re.compile(r"^\s*(?:s3|s3a|https?|ftp|file|gcs|azure|hdfs)://", re.IGNORECASE)
_MAX_STATEMENTS = 1


class SqlRejected(Exception):
    """Raised when SQL falls outside the read-only analytical allow-list."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _function_name(node: exp.Expression) -> str:
    if isinstance(node, exp.Anonymous):
        return str(node.name or "").lower()
    try:
        return str(node.sql_name() or "").lower()
    except Exception:  # pragma: no cover - defensive against parser quirks
        return ""


def validate_sql(sql: str) -> None:
    """
    Validate that ``sql`` is a single read-only query with no file, network or
    extension access. Raises :class:`SqlRejected` with a safe reason string.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SqlRejected("The SQL statement is empty.")
    if "\x00" in sql:
        raise SqlRejected("The SQL statement contains invalid characters.")

    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except Exception as exc:
        raise SqlRejected("The SQL statement could not be parsed.") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) > _MAX_STATEMENTS:
        raise SqlRejected("Only one SQL statement may be executed per request.")
    if not statements:
        raise SqlRejected("The SQL statement is empty.")

    root = statements[0]

    if not isinstance(root, _ALLOWED_ROOTS):
        raise SqlRejected(
            f"Only read-only SELECT queries are permitted (received {type(root).__name__})."
        )

    _reject_forbidden_nodes(root.walk())
    _reject_unsafe_literals(root)
    _reject_unsafe_table_names(root)
    _reject_blocked_functions(root)


def _reject_unsafe_table_names(root: exp.Expression) -> None:
    """Reject table references that are actually file paths or URLs."""
    for node in root.find_all(exp.Table):
        name = str(node.name or "")
        if _URL_SCHEME_RE.match(name):
            raise SqlRejected("External file and network locations are not permitted.")
        if name.startswith(("/", "\\", "~")) or ".." in name:
            raise SqlRejected("File-system paths are not permitted in the sandbox.")
        if re.match(r"^[A-Za-z]:[\\/]", name):
            raise SqlRejected("File-system paths are not permitted in the sandbox.")


def _reject_forbidden_nodes(nodes: Iterable[exp.Expression]) -> None:
    for node in nodes:
        if isinstance(node, _FORBIDDEN_STATEMENTS):
            raise SqlRejected(
                f"Statement type '{type(node).__name__}' is not permitted in the sandbox."
            )


def _reject_unsafe_literals(root: exp.Expression) -> None:
    for node in root.find_all(exp.Literal):
        if node.is_string and _URL_SCHEME_RE.match(str(node.this)):
            raise SqlRejected("External file and network locations are not permitted.")


def _reject_blocked_functions(root: exp.Expression) -> None:
    for node in root.walk():
        if not isinstance(node, (exp.Func, exp.Anonymous)):
            continue
        name = _function_name(node)
        if name in _BLOCKED_FUNCTIONS:
            raise SqlRejected(f"Function '{name}' is not permitted in the sandbox.")
