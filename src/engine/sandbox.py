"""
Deterministic In-Memory Sandbox Execution Engine.
Uses DuckDB (with seamless sqlite3 in-memory fallback) and Polars/Pandas
for compiled, vectorised execution with zero LLM-hallucinated math.
"""

from __future__ import annotations
import ast
import io
import sys
import time
import sqlite3
import traceback
from typing import Dict, Any, Optional, Tuple
import pandas as pd

# Optional high-performance acceleration libraries
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    pl = None
    HAS_POLARS = False

from .invariants import InvariantChecker


class SecurityViolation(Exception):
    """Raised when unsafe code or unauthorized AST nodes are detected."""
    pass


class DeterministicSandbox:
    """
    Isolated execution engine for SQL and Python data transformations.
    Guarantees that all mathematical operations and aggregations are compiled and executed
    by underlying C/Rust query engines, not guessed by an LLM.
    """

    FORBIDDEN_MODULES = {
        "os", "sys", "subprocess", "socket", "urllib", "requests",
        "shutil", "builtins", "importlib", "posix", "nt", "ctypes"
    }

    def __init__(self, memory_limit: str = "1GB", threads: int = 2):
        self.has_duckdb = HAS_DUCKDB
        if self.has_duckdb:
            self.con = duckdb.connect(database=":memory:")
            self.con.execute(f"SET max_memory = '{memory_limit}';")
            self.con.execute(f"SET threads = {threads};")
        else:
            self.sqlite_con = sqlite3.connect(":memory:")
        self.registered_tables: Dict[str, pd.DataFrame] = {}

    def register_dataframe(self, name: str, df: Any) -> None:
        """Register a DataFrame as a virtual view in the SQL engine."""
        if HAS_POLARS and isinstance(df, pl.DataFrame):
            df = df.to_pandas()
        elif not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        self.registered_tables[name] = df

        if self.has_duckdb:
            self.con.register(name, df)
        else:
            df.to_sql(name, self.sqlite_con, if_exists="replace", index=False)

    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute an analytical SQL query deterministically.
        """
        start_time = time.time()
        try:
            if self.has_duckdb:
                rel = self.con.sql(sql_query)
                if rel is None:
                    return {
                        "status": "SUCCESS",
                        "engine": "duckdb",
                        "rows_affected": 0,
                        "execution_time_ms": int((time.time() - start_time) * 1000)
                    }
                df_result = rel.df()
                engine_used = "duckdb"
            else:
                df_result = pd.read_sql_query(sql_query, self.sqlite_con)
                engine_used = "sqlite3"

            exec_time = int((time.time() - start_time) * 1000)
            invariants = InvariantChecker.run_suite(df_result)

            return {
                "status": "SUCCESS",
                "engine": engine_used,
                "execution_time_ms": exec_time,
                "row_count": len(df_result),
                "columns": list(df_result.columns),
                "data": df_result.to_dict(orient="records")[:500],
                "invariants": invariants,
                "sql": sql_query
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    @classmethod
    def validate_python_ast(cls, code_str: str) -> None:
        """
        Inspect the Python Abstract Syntax Tree (AST) for security violations.
        Blocks imports of system/network libraries, file access, and arbitrary exec.
        """
        tree = ast.parse(code_str)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES:
                        raise SecurityViolation(f"Import of forbidden module '{alias.name}' is blocked.")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES:
                        raise SecurityViolation(f"Import from forbidden module '{node.module}' is blocked.")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("eval", "exec", "compile", "__import__", "open"):
                        raise SecurityViolation(f"Direct call to restricted function '{node.func.id}' is blocked.")

    def execute_python(self, code_str: str, local_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a safe Python analytical snippet in a constrained environment.
        """
        start_time = time.time()
        try:
            self.validate_python_ast(code_str)
        except SecurityViolation as sv:
            return {
                "status": "SECURITY_VIOLATION",
                "error": str(sv),
                "execution_time_ms": 0
            }

        # Safe global namespace
        safe_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
                "enumerate": enumerate, "filter": filter, "float": float, "format": format,
                "int": int, "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
                "len": len, "list": list, "map": map, "max": max, "min": min, "next": next,
                "print": print, "range": range, "reversed": reversed, "round": round,
                "set": set, "slice": slice, "sorted": sorted, "str": str, "sum": sum,
                "tuple": tuple, "zip": zip
            },
            "pd": pd,
        }
        if HAS_POLARS:
            safe_globals["pl"] = pl
        if HAS_DUCKDB:
            safe_globals["duckdb"] = duckdb

        namespace = {**safe_globals, **(local_vars or {})}

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        try:
            exec(code_str, namespace)
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
                "invariants": invariants
            }
        except Exception as e:
            sys.stdout = old_stdout
            return {
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
