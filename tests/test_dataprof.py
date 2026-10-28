"""Schema card: deterministic profiling with role inference."""

from __future__ import annotations

import pandas as pd

from dataprof import build_schema_card, card_summary


def test_roles_are_inferred_deterministically():
    df = pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2024-01-01", "2024-01-02"] * 20),
            "revenue": [100.0 + i for i in range(40)],
            "region": ["AMER", "EMEA"] * 20,
            "order_id": [f"o-{i}" for i in range(40)],
        }
    )
    card = build_schema_card(df)
    roles = {c.name: c.role for c in card.columns}
    assert roles["order_date"] == "temporal"
    assert roles["revenue"] == "measure"
    assert roles["region"] == "dimension"
    assert roles["order_id"] == "identifier"


def test_profile_is_reproducible():
    df = pd.DataFrame({"a": [1, 2, 3, None], "b": ["x", "y", "x", None]})
    first = build_schema_card(df).render()
    second = build_schema_card(df).render()
    assert first == second
    assert "25% null" in first


def test_dimension_top_values():
    df = pd.DataFrame({"region": ["AMER"] * 3 + ["EMEA"] * 2 + ["APAC"]})
    card = build_schema_card(df)
    region = next(c for c in card.columns if c.name == "region")
    assert region.distinct == 3
    assert region.top_values[0].startswith("AMER (3)")


def test_render_is_bounded():
    df = pd.DataFrame({f"col_{i}": list(range(5)) for i in range(200)})
    card = build_schema_card(df, max_columns=60)
    text = card.render(max_chars=600)
    assert len(text) <= 700
    assert "truncated" in text or card.truncated


def test_card_summary_is_json_safe():
    import json

    df = pd.DataFrame({"a": [1.5, None, 3.0]})
    summary = card_summary(build_schema_card(df))
    json.dumps(summary)
    assert summary["row_count"] == 3
    assert summary["columns"][0]["null_rate"] > 0
