"""
Deterministic In-Memory Sandbox Execution Engine.

DuckDB (with a sqlite3 in-memory fallback) and Polars/Pandas provide compiled,
vectorised execution so analytical arithmetic is never produced by an LLM.

Isolation model:
* SQL passes through :mod:`engine.sql_guard` (read-only, no file/network access).
* DuckDB is configured with external access and extension autoloading disabled
  and its configuration locked, so a query cannot re-enable either.
* Python execution is not exposed to the model. It remains available for
  internal, first-party callers and still enforces an AST allow-list.
"""

from __future__ import annotations

import ast
import io
import sqlite3
import sys
import time
from typing import Any, Dict, Optional

import pandas as pd

try:
    import duckdb

    HAS_DUCKDB = True
except ImportError:  # pragma: no cover - exercised only on minimal installs
    duckdb = None
    HAS_DUCKDB = False

try:
    import polars as pl

    HAS_POLARS = True
except ImportError:  # pragma: no cover
    pl = None
    HAS_POLARS = False

from .invariants import InvariantChecker
from .sql_guard import SqlRejected, validate_sql

MAX_RESULT_ROWS = 5000


class SecurityViolation(Exception):
    """Raised when unsafe code or unauthorized AST nodes are detected."""


class DeterministicSandbox:
    """
    Isolated execution engine for SQL and Python data transformations.

    Guarantees that all mathematical operations and aggregations are compiled
    and executed by the underlying query engine, not guessed by an LLM.
    """

    FORBIDDEN_MODULES = {
        "os",
        "sys",
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "shutil",
        "builtins",
        "importlib",
        "posix",
        "nt",
        "ctypes",
        "http",
        "ftplib",
    }

    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "breakpoint",
        "input",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "memoryview",
    }

    def __init__(self, memory_limit: str = "1GB", threads: int = 2):
        self.has_duckdb = HAS_DUCKDB
        self.registered_tables: Dict[str, pd.DataFrame] = {}

        if self.has_duckdb:
            self.con = duckdb.connect(
                database=":memory:",
                config={
                    "memory_limit": memory_limit,
                    "threads": str(threads),
                    "enable_external_access": "false",
                    "autoinstall_known_extensions": "false",
                    "autoload_known_extensions": "false",
                    "allow_community_extensions": "false",
                    "lock_configuration": "true",
                },
            )
        else:
            self.sqlite_con = sqlite3.connect(":memory:")

    # -- data registration -------------------------------------------------

    def register_dataframe(self, name: str, df: Any) -> None:
        """Register a DataFrame as a queryable table in the SQL engine."""
        if HAS_POLARS and isinstance(df, pl.DataFrame):
            df = df.to_pandas()
        elif not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        if not str(name).isidentifier():
            raise SecurityViolation("Table names must be simple identifiers.")

        self.registered_tables[name] = df
        if self.has_duckdb:
            self.con.register(name, df)
        else:
            df.to_sql(name, self.sqlite_con, if_exists="replace", index=False)

    def register_records(self, name: str, records: list) -> None:
        if not records:
            self.register_dataframe(name, pd.DataFrame())
            return
        self.register_dataframe(name, pd.DataFrame(records))

    def has_table(self, name: str) -> bool:
        return name in self.registered_tables

    # -- SQL ---------------------------------------------------------------

    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """Validate and execute a read-only analytical query deterministically."""
        start_time = time.time()

        try:
            validate_sql(sql_query)
        except SqlRejected as rejection:
            return {
                "status": "SECURITY_VIOLATION",
                "error": rejection.reason,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        try:
            if self.has_duckdb:
                rel = self.con.sql(sql_query)
                if rel is None:
                    return {
                        "status": "SUCCESS",
                        "engine": "duckdb",
                        "rows_affected": 0,
                        "row_count": 0,
                        "execution_time_ms": int((time.time() - start_time) * 1000),
                    }
                limited = rel.limit(MAX_RESULT_ROWS + 1)
                df_result = limited.df()
                engine_used = "duckdb"
            else:
                df_result = pd.read_sql_query(sql_query, self.sqlite_con)
                engine_used = "sqlite3"

            truncated = len(df_result) > MAX_RESULT_ROWS
            if truncated:
                df_result = df_result.head(MAX_RESULT_ROWS)

            exec_time = int((time.time() - start_time) * 1000)
            # A one-row result is usually a scalar aggregate, not a sample.
            invariants = InvariantChecker.run_suite(
                df_result, enforce_sample_size=len(df_result) > 1
            )

            return {
                "status": "SUCCESS",
                "engine": engine_used,
                "execution_time_ms": exec_time,
                "row_count": len(df_result),
                "truncated": truncated,
                "columns": [str(c) for c in df_result.columns],
                "data": df_result.to_dict(orient="records"),
                "invariants": invariants,
                "sql": sql_query,
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "error": str(exc),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

    # -- Python (internal first-party use only) ----------------------------

    @classmethod
    def validate_python_ast(cls, code_str: str) -> None:
        """Reject imports, dynamic execution, IO and dunder attribute access."""
        tree = ast.parse(code_str)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES:
                        raise SecurityViolation(
                            f"Import of forbidden module '{alias.name}' is blocked."
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES:
                        raise SecurityViolation(
                            f"Import from forbidden module '{node.module}' is blocked."
                        )
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_CALLS:
                    raise SecurityViolation(
                        f"Direct call to restricted function '{node.func.id}' is blocked."
                    )
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "system",
                    "popen",
                    "spawn",
                    "execv",
                    "read_csv",
                    "read_parquet",
                    "read_json",
                    "to_csv",
                    "to_parquet",
                }:
                    raise SecurityViolation(
                        f"Call to restricted method '{node.func.attr}' is blocked."
                    )
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith("__") and node.attr.endswith("__"):
                    raise SecurityViolation(
                        f"Access to dunder attribute '{node.attr}' is blocked."
                    )

    def execute_python(
        self, code_str: str, local_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a constrained Python snippet for internal callers only."""
        start_time = time.time()
        try:
            self.validate_python_ast(code_str)
        except (SecurityViolation, SyntaxError) as violation:
            return {
                "status": "SECURITY_VIOLATION",
                "error": str(violation),
                "execution_time_ms": 0,
            }

        safe_globals: Dict[str, Any] = {
            "__builtins__": {
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "dict": dict,
                "enumerate": enumerate,
                "filter": filter,
                "float": float,
                "format": format,
                "int": int,
                "isinstance": isinstance,
                "issubclass": issubclass,
                "iter": iter,
                "len": len,
                "list": list,
                "map": map,
                "max": max,
                "min": min,
                "next": next,
                "print": print,
                "range": range,
                "reversed": reversed,
                "round": round,
                "set": set,
                "slice": slice,
                "sorted": sorted,
                "str": str,
                "sum": sum,
                "tuple": tuple,
                "zip": zip,
            }
        }

        namespace = {**safe_globals, **(local_vars or {})}

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        try:
            exec(code_str, namespace)  # noqa: S102 - guarded by validate_python_ast
            sys.stdout = old_stdout
            stdout_text = redirected_output.getvalue()

            result_val = namespace.get("result", None)
            serialized_result = None
            invariants = None

            if isinstance(result_val, pd.DataFrame):
                invariants = InvariantChecker.run_suite(result_val)
                serialized_result = result_val.head(100).to_dict(orient="records")
            elif isinstance(result_val, (dict, list, int, float, str, bool)):
                serialized_result = result_val

            return {
                "status": "SUCCESS",
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "stdout": stdout_text,
                "result": serialized_result,
                "invariants": invariants,
            }
        except Exception as exc:
            sys.stdout = old_stdout
            return {
                "status": "ERROR",
                "error": str(exc),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }
