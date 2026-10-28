"""Sandbox isolation tests: SQL and Python escape vectors must be blocked."""

from __future__ import annotations

import pandas as pd
import pytest

from engine.sandbox import DeterministicSandbox


@pytest.fixture()
def sandbox() -> DeterministicSandbox:
    box = DeterministicSandbox()
    box.register_dataframe("dataset", pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
    return box


@pytest.mark.parametrize(
    "sql",
    [
        "COPY (SELECT 1) TO '/tmp/exfil.csv'",
        "COPY dataset TO '/tmp/dataset.csv'",
        "INSTALL httpfs",
        "LOAD httpfs",
        "ATTACH '/tmp/evil.db' AS evil",
        "DETACH dataset",
        "CREATE TABLE evil AS SELECT 1",
        "INSERT INTO dataset VALUES (4, 'w')",
        "UPDATE dataset SET a = 0",
        "DELETE FROM dataset",
        "DROP TABLE dataset",
        "PRAGMA database_list",
        "SET enable_external_access = true",
        "EXPORT DATABASE '/tmp/export'",
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM read_csv('s3://other-bucket/key.csv')",
        "SELECT * FROM read_parquet('https://evil.example/data.parquet')",
        "SELECT * FROM glob('/etc/*')",
        "SELECT * FROM 'https://evil.example/data.csv'",
        "SELECT 1; DROP TABLE dataset",
    ],
)
def test_destructive_sql_is_blocked(sandbox: DeterministicSandbox, sql: str) -> None:
    result = sandbox.execute_sql(sql)
    assert result["status"] == "SECURITY_VIOLATION", result
    assert "error" in result


@pytest.mark.parametrize(
    "code",
    [
        "import os\nos.system('id')",
        "import subprocess",
        "open('/etc/passwd').read()",
        "eval('1+1')",
        "__import__('os').system('id')",
        "getattr(__builtins__, 'eval')('1')",
        "().__class__.__bases__[0].__subclasses__()",
        "pandas.read_csv('/etc/passwd')",
    ],
)
def test_python_escapes_are_blocked(sandbox: DeterministicSandbox, code: str) -> None:
    result = sandbox.execute_python(code)
    assert result["status"] == "SECURITY_VIOLATION", result


def test_safe_select_still_works(sandbox: DeterministicSandbox) -> None:
    result = sandbox.execute_sql(
        "WITH filtered AS (SELECT a FROM dataset WHERE a > 1) SELECT SUM(a) AS total FROM filtered"
    )
    assert result["status"] == "SUCCESS", result
    assert result["row_count"] == 1
    assert result["data"][0]["total"] == 5


def test_result_rows_are_capped(sandbox: DeterministicSandbox) -> None:
    box = DeterministicSandbox()
    box.register_dataframe("big", pd.DataFrame({"n": list(range(50_000))}))
    result = box.execute_sql("SELECT n FROM big")
    assert result["status"] == "SUCCESS"
    assert result["row_count"] <= 5000
    assert result["truncated"] is True
