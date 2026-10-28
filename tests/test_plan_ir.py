"""Typed analysis plans: validation, hashing and compilation."""

from __future__ import annotations

import pytest

from plan import PlanError, compile_plan, parse_plan, plan_schema
from semantic import load_catalog


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_parse_minimal_plan_is_stable():
    plan = parse_plan({"intent": "aggregate", "metrics": ["revenue"]})
    assert plan.intent == "aggregate"
    assert plan.metrics == ("revenue",)
    assert plan.plan_hash() == parse_plan({"metrics": ["revenue"], "intent": "aggregate"}).plan_hash()


def test_plan_hash_changes_with_semantics():
    left = parse_plan({"intent": "aggregate", "metrics": ["revenue"]})
    right = parse_plan({"intent": "aggregate", "metrics": ["order_count"]})
    assert left.plan_hash() != right.plan_hash()


def test_unknown_keys_are_rejected():
    with pytest.raises(PlanError):
        parse_plan({"intent": "aggregate", "metrics": ["revenue"], "where": "1=1"})


def test_trend_plan_needs_time_and_grain():
    with pytest.raises(PlanError):
        parse_plan({"intent": "trend", "metrics": ["revenue"], "grain": "month"})
    with pytest.raises(PlanError):
        parse_plan({"intent": "trend", "metrics": ["revenue"], "time_column": "dt", "grain": "fortnight"})


def test_limit_and_order_validation():
    with pytest.raises(PlanError):
        parse_plan({"intent": "aggregate", "metrics": ["revenue"], "limit": 0})
    with pytest.raises(PlanError):
        parse_plan({"intent": "aggregate", "metrics": ["revenue"], "order": "sideways"})


def test_compile_aggregate(catalog):
    plan = parse_plan(
        {
            "intent": "aggregate",
            "metrics": ["revenue"],
            "group_by": ["region"],
            "filters": [{"column": "region", "op": "=", "value": "AMER"}],
        }
    )
    bound = catalog.bind(["region", "revenue"])
    compiled = compile_plan(plan, bound, ["region", "revenue"])
    assert '"region" = \'AMER\'' in compiled.sql
    assert 'GROUP BY "region"' in compiled.sql
    assert compiled.metric == "revenue"
    assert compiled.plan_hash == plan.plan_hash()


def test_compile_trend_uses_date_trunc(catalog):
    plan = parse_plan(
        {
            "intent": "trend",
            "metrics": ["revenue"],
            "time_column": "order_date",
            "grain": "month",
        }
    )
    bound = catalog.bind(["order_date", "revenue"])
    compiled = compile_plan(plan, bound, ["order_date", "revenue"])
    assert "date_trunc('month'" in compiled.sql
    assert 'ORDER BY "period" ASC' in compiled.sql


def test_unknown_metric_reports_available(catalog):
    plan = parse_plan({"intent": "aggregate", "metrics": ["revenue"]})
    with pytest.raises(PlanError) as exc:
        compile_plan(plan, catalog.bind(["region"]), ["region"])
    assert "not defined" in str(exc.value)
    assert "order_count" in str(exc.value)


def test_filter_values_are_escaped(catalog):
    plan = parse_plan(
        {
            "intent": "aggregate",
            "metrics": ["revenue"],
            "filters": [{"column": "region", "op": "=", "value": "x'; DROP TABLE dataset;--"}],
        }
    )
    bound = catalog.bind(["region", "revenue"])
    compiled = compile_plan(plan, bound, ["region", "revenue"])
    assert "DROP TABLE dataset" in compiled.sql  # it is a quoted literal, not a statement
    assert "x''; DROP TABLE dataset;--'" in compiled.sql


def test_plan_schema_is_closed():
    schema = plan_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"intent", "metrics"}
