"""Analysis service contract: page-context datasets and stable error codes.

These run without AWS because a `page_context` dataset is built in memory.
"""

from __future__ import annotations

import pytest
from botocore.exceptions import ClientError

from errors import AppError
from services.analysis import _translate_bedrock_error, run_sql

PAGE_CONTEXT = {
    "tables": [
        {
            "headers": ["region", "revenue"],
            "rowCount": 2,
            "sampleRows": [["AMER", "100"], ["EMEA", "50"]],
        }
    ]
}


def _run(sql: str):
    return run_sql({"sql": sql, "page_context": PAGE_CONTEXT})


def test_run_sql_uses_the_extracted_page_table() -> None:
    result = _run(
        "SELECT region, CAST(revenue AS INTEGER) AS revenue "
        "FROM dataset ORDER BY revenue DESC"
    )

    assert result["status"] == "SUCCESS"
    assert result["row_count"] == 2
    assert result["data"][0]["region"] == "AMER"
    assert result["dataset"]["source"] == "page_context"
    assert result["dataset"]["row_count"] == 2
    # The page reported exactly the rows that were sent, so this is not a sample.
    assert result["dataset"]["sampled"] is False


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE dataset",
        "COPY dataset TO '/tmp/leak.csv'",
        "SELECT * FROM dataset; DROP TABLE dataset",
    ],
)
def test_rejected_sql_is_a_422(sql: str) -> None:
    with pytest.raises(AppError) as exc:
        _run(sql)

    assert exc.value.code == "QUERY_REJECTED"
    assert exc.value.status == 422


def test_unknown_column_is_a_422_execution_error() -> None:
    with pytest.raises(AppError) as exc:
        _run("SELECT missing_column FROM dataset")

    assert exc.value.code == "SQL_EXECUTION_ERROR"
    assert exc.value.status == 422


def test_bedrock_access_errors_map_to_a_stable_code() -> None:
    exc = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "gated"}}, "Converse"
    )
    mapped = _translate_bedrock_error(exc)

    assert mapped.code == "MODEL_ACCESS_DENIED"
    assert mapped.status == 503
    assert mapped.retryable is False


def test_bedrock_throttling_stays_retryable() -> None:
    exc = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "Converse"
    )
    mapped = _translate_bedrock_error(exc)

    assert mapped.code == "BEDROCK_THROTTLED"
    assert mapped.retryable is True


def test_unknown_bedrock_error_is_internal() -> None:
    exc = ClientError({"Error": {"Code": "SomethingNew", "Message": "?"}}, "Converse")

    assert _translate_bedrock_error(exc).code == "INTERNAL"
