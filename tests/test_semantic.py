"""Semantic layer: catalogue loading, binding and deterministic SQL."""

from __future__ import annotations

import pandas as pd
import pytest

from semantic import compile_metric_query, load_catalog
from semantic.catalog import CatalogError, MetricCatalog
from semantic.query import MetricFilter, MetricQueryError


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_catalog_loads_and_is_valid(catalog):
    assert len(catalog.metrics) >= 10
    assert "revenue" in catalog.metrics
    assert catalog.metrics["aov"].formula


def test_bind_resolves_aliases(catalog):
    bound = catalog.bind(["region", "sales", "order_id"])
    assert "revenue" in bound
    assert bound["revenue"].sql == 'SUM(TRY_CAST("sales" AS DOUBLE))'
    assert "aov" in bound  # derived metric resolves through revenue


def test_bind_omits_unavailable_metrics(catalog):
    bound = catalog.bind(["region"])
    assert "revenue" not in bound
    assert "nrr" not in bound
    assert "order_count" in bound  # no columns required


def test_bind_marks_ambiguous_columns_unavailable(catalog):
    bound = catalog.bind(["revenue", "Revenue"])
    assert "revenue" not in bound


def test_render_prompt_is_bounded_and_sorted(catalog):
    bound = catalog.bind(["region", "revenue", "user_id"])
    prompt = catalog.render_prompt(bound, max_chars=400)
    assert "METRIC CATALOG" in prompt
    assert len(prompt) <= 500

    full = catalog.render_prompt(bound)
    names = [
        line.split()[1]
        for line in full.splitlines()
        if line.startswith("- ") and "truncated" not in line
    ]
    assert names == sorted(names)


def test_invalid_catalogue_fails_at_load(tmp_path):
    raw = {"version": 1, "metrics": [{"name": "Bad Name", "unit": "count", "sql": "1"}]}
    with pytest.raises(CatalogError):
        MetricCatalog.from_dict(raw)


def test_compile_metric_query_grouped(catalog):
    bound = catalog.bind(["region", "revenue"])
    sql = compile_metric_query(
        bound["revenue"],
        columns=["region", "revenue"],
        group_by=["region"],
        order="desc",
        limit=50,
    )
    assert sql == (
        'SELECT "region", SUM(TRY_CAST("revenue" AS DOUBLE)) AS "revenue" '
        'FROM dataset GROUP BY "region" ORDER BY "revenue" DESC LIMIT 50'
    )


def test_compile_metric_query_filters_are_escaped(catalog):
    bound = catalog.bind(["region", "revenue"])
    filters = [
        MetricFilter("region", "=", "O'Brien"),
        MetricFilter("revenue", ">=", 1000.5),
        MetricFilter("region", "in", ["AMER", "EMEA"]),
        MetricFilter("region", "not_null"),
    ]
    sql = compile_metric_query(
        bound["revenue"], columns=["region", "revenue"], filters=filters
    )
    assert "\"region\" = 'O''Brien'" in sql
    assert '"revenue" >= 1000.5' in sql
    assert '"region" IN (\'AMER\', \'EMEA\')' in sql
    assert '"region" IS NOT NULL' in sql


def test_compile_metric_query_rejects_unknown_columns(catalog):
    bound = catalog.bind(["region", "revenue"])
    with pytest.raises(MetricQueryError):
        compile_metric_query(bound["revenue"], columns=["region", "revenue"], group_by=["missing"])
    with pytest.raises(MetricQueryError):
        compile_metric_query(
            bound["revenue"],
            columns=["region", "revenue"],
            filters=[MetricFilter("missing", "=", 1)],
        )


def test_compile_metric_query_caps_limit(catalog):
    bound = catalog.bind(["region", "revenue"])
    sql = compile_metric_query(bound["revenue"], columns=["region", "revenue"], limit=99999)
    assert sql.endswith("LIMIT 1000")


def test_compiled_sql_runs_in_the_sandbox(catalog):
    from engine.sandbox import DeterministicSandbox

    df = pd.DataFrame({"region": ["AMER", "AMER", "EMEA"], "revenue": [100.0, 200.0, 50.0]})
    bound = catalog.bind(df.columns)
    sql = compile_metric_query(bound["revenue"], columns=list(df.columns), group_by=["region"])

    sandbox = DeterministicSandbox()
    sandbox.register_dataframe("dataset", df)
    result = sandbox.execute_sql(sql)

    assert result["status"] == "SUCCESS"
    rows = {row["region"]: row["revenue"] for row in result["data"]}
    assert rows == {"AMER": 300.0, "EMEA": 50.0}
