"""Request validation contract tests."""

from __future__ import annotations

import uuid

import pytest

from api.validation import (
    get_tenant_id,
    normalize_chart_type,
    normalize_discipline,
    page_context_reported_rows,
    page_context_to_records,
    validate_chart_columns,
    validate_dataset_key,
    validate_model_id,
    validate_page_context,
    validate_upload_request,
)
from errors import AppError

KEY = f"uploads/public/{uuid.uuid4()}.csv"
CLAUDE = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"


def test_dataset_key_accepts_owned_upload() -> None:
    assert validate_dataset_key(KEY, "public") == KEY


@pytest.mark.parametrize(
    "key",
    [
        "datasets/sample.parquet",
        "../../etc/passwd",
        "uploads/public/not-a-uuid.csv",
        f"uploads/public/{uuid.uuid4()}.exe",
        f"uploads/public/{uuid.uuid4()}.csv.bak",
        f"uploads/public/{uuid.uuid4()}.csv/../secret",
    ],
)
def test_dataset_key_rejects_traversal_and_unknown_paths(key: str) -> None:
    with pytest.raises(AppError) as exc:
        validate_dataset_key(key, "public")
    assert exc.value.code == "INVALID_DATASET_KEY"


def test_dataset_key_is_tenant_scoped() -> None:
    with pytest.raises(AppError) as exc:
        validate_dataset_key(KEY, "alice")
    assert exc.value.status == 403


def test_dataset_key_optional_unless_required() -> None:
    assert validate_dataset_key(None, "public") is None
    with pytest.raises(AppError):
        validate_dataset_key(None, "public", required=True)


def test_tenant_resolution_prefers_jwt_claim() -> None:
    event = {
        "headers": {"x-tenant-id": "spoofed"},
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "alice"}}}},
    }
    assert get_tenant_id(event) == "alice"


def test_tenant_rejects_invalid_identifier() -> None:
    with pytest.raises(AppError):
        get_tenant_id({"headers": {"x-tenant-id": "bad tenant!"}})


def test_upload_limits_and_extensions() -> None:
    spec = validate_upload_request({"filename": "data.CSV", "size": 1024})
    assert spec["ext"] == "csv"

    with pytest.raises(AppError):
        validate_upload_request({"filename": "data.exe", "size": 1024})
    with pytest.raises(AppError) as exc:
        validate_upload_request({"filename": "data.csv", "size": 999 * 1024 * 1024})
    assert exc.value.code == "PAYLOAD_TOO_LARGE"


def test_chart_and_model_validation(monkeypatch):
    assert normalize_chart_type(None) is None
    assert normalize_chart_type("BAR") == "bar"
    assert validate_chart_columns(["a", "b"]) == {"x": "a", "y": "b", "color": None}
    assert normalize_discipline("Financial & RevOps") == "financial"
    assert validate_model_id(None, "global.moonshotai.kimi-k3") == "global.moonshotai.kimi-k3"
    assert validate_model_id(None, "us.amazon.nova-pro-v1:0") == "us.amazon.nova-pro-v1:0"

    # Only the model verified for this build is accepted out of the box; anything
    # else must be enabled for the deployment.
    with pytest.raises(AppError) as exc:
        validate_model_id(CLAUDE, "global.moonshotai.kimi-k3")
    assert exc.value.code == "MODEL_NOT_APPROVED"

    monkeypatch.setenv("BEDROCK_ALLOWED_MODELS", CLAUDE)
    assert validate_model_id(CLAUDE, "global.moonshotai.kimi-k3") == CLAUDE

    with pytest.raises(AppError):
        validate_model_id("gpt-4o", "us.amazon.nova-pro-v1:0")
    with pytest.raises(AppError):
        validate_model_id("global.openai.gpt-5.4", "us.amazon.nova-pro-v1:0")
    with pytest.raises(AppError):
        validate_model_id("anthropic.claude-opus-5-5", "us.amazon.nova-pro-v1:0")


def test_page_context_merges_split_tables_and_skips_unrelated_ones() -> None:
    page_context = {
        "tables": [
            {"headers": ["unrelated"], "rowCount": 1, "sampleRows": [["9"]]},
            {"headers": ["a", "b"], "rowCount": 2, "sampleRows": [["1", "2"], ["3", "4"]]},
            {"headers": ["a", "b"], "rowCount": 2, "sampleRows": [["5", "6"]]},
        ]
    }
    assert page_context_to_records(page_context) == [
        {"a": "1", "b": "2"},
        {"a": "3", "b": "4"},
        {"a": "5", "b": "6"},
    ]
    # The page said 4 rows for the analysed table, even though it sent 3.
    assert page_context_reported_rows(page_context) == 4


def test_page_context_accepts_objects_columns_and_empty_tables() -> None:
    assert page_context_to_records(None) == []
    assert page_context_to_records({"tables": []}) == []
    assert page_context_to_records({"tables": [{"headers": [], "sampleRows": []}]}) == []
    assert page_context_to_records(
        {"tables": [{"headers": ["a"], "sampleRows": [["1"]]}, {"headers": ["a"], "sampleRows": [{"a": "2"}]}]}
    ) == [{"a": "1"}, {"a": "2"}]


def test_page_context_size_is_measured_in_bytes() -> None:
    # 150k characters, but 300 KB once UTF-8 encoded: over the 200 KB limit even
    # though the string length is below it.
    with pytest.raises(AppError) as exc:
        validate_page_context({"tables": [], "blob": "é" * 150_000})
    assert exc.value.code == "PAYLOAD_TOO_LARGE"

    # 90k characters is 180 KB, so it fits.
    assert validate_page_context({"tables": [], "blob": "é" * 90_000})["tables"] == []
