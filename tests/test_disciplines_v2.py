"""Correctness tests for the hardened discipline analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from disciplines.clinical import ClinicalAnalytics
from disciplines.financial import FinancialAnalytics
from disciplines.growth import GrowthAnalytics
from disciplines.operations import OperationsAnalytics
from disciplines.product import ProductAnalytics

# ---------------------------------------------------------------- funnel

def test_funnel_sequential_and_is_monotonic():
    df = pd.DataFrame(
        {
            "signup": [1, 1, 1, 1],
            "onboarded": [1, 0, 1, 0],
            "paid": [1, 1, 0, 0],
        }
    )
    funnel = ProductAnalytics.calculate_funnel(df, ["signup", "onboarded", "paid"])
    assert [s["users"] for s in funnel["steps"]] == [4, 2, 1]
    assert funnel["monotonic"] is True
    assert funnel["method"] == "sequential_and"


def test_ordered_funnel_respects_sequence():
    rows = [
        ("u1", "2024-01-01", 1, 0, 0),
        ("u1", "2024-01-02", 0, 1, 0),
        ("u1", "2024-01-03", 0, 0, 1),
        ("u2", "2024-01-01", 1, 0, 0),
        ("u2", "2024-01-03", 0, 0, 1),  # paid without onboarding: does not count
        ("u3", "2024-01-02", 0, 1, 0),  # onboarded without signup: does not count
    ]
    df = pd.DataFrame(rows, columns=["user", "ts", "signup", "onboarded", "paid"])
    funnel = ProductAnalytics.calculate_funnel(
        df, ["signup", "onboarded", "paid"], user_column="user", order_column="ts"
    )
    assert [s["users"] for s in funnel["steps"]] == [2, 1, 1]
    assert funnel["method"] == "sequential_ordered"


def test_funnel_rejects_unknown_columns():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError):
        ProductAnalytics.calculate_funnel(df, ["a", "missing"])


# ---------------------------------------------------------------- retention

def test_retention_matrix_is_sorted_and_flags_incomplete_cohorts():
    df = pd.DataFrame(
        {
            "user": ["u1", "u2", "u1", "u1", "u3", "u3"],
            "cohort": ["A", "A", "A", "A", "B", "B"],
            "period": [0, 0, 1, 2, 0, 1],
        }
    )
    result = ProductAnalytics.calculate_retention_matrix(df, "user", "cohort", "period")
    cohorts = {row["cohort"]: row for row in result["matrix"]}
    assert cohorts["A"]["periods"]["2"]["retention_rate"] == 0.5
    assert cohorts["A"]["complete"] is True
    assert cohorts["B"]["complete"] is False
    assert result["period_order"] == ["0", "1", "2"]


# ---------------------------------------------------------------- growth

def test_multi_touch_attribution_first_last_linear():
    df = pd.DataFrame(
        {
            "user": ["u1", "u1", "u1", "u2", "u2"],
            "ts": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-01", "2024-01-02"],
            "channel": ["search", "social", "search", "email", "search"],
            "conversion": [0, 0, 1, 0, 1],
        }
    )
    result = GrowthAnalytics.calculate_attribution_models(
        df, "channel", "conversion", user_column="user", timestamp_column="ts"
    )
    assert result["multi_touch_available"] is True
    models = result["models"]
    assert models["first_touch"] == {"email": 0.5, "search": 0.5}
    assert models["last_touch"] == {"search": 1.0}
    assert models["linear"]["search"] == pytest.approx(0.5833, abs=1e-3)
    assert models["linear"]["social"] == pytest.approx(0.1667, abs=1e-3)
    assert models["linear"]["email"] == pytest.approx(0.25, abs=1e-3)


def test_single_touch_is_labelled_honestly():
    df = pd.DataFrame({"channel": ["a", "a", "b"], "conversion": [1, 1, 1]})
    result = GrowthAnalytics.calculate_attribution_models(df, "channel", "conversion")
    assert result["attribution_model"] == "single_touch_channel_share"
    assert result["multi_touch_available"] is False
    assert result["channel_shares"] == {"a": pytest.approx(2 / 3, abs=1e-4), "b": pytest.approx(1 / 3, abs=1e-4)}


def test_unit_economics_handles_zero_cac():
    result = GrowthAnalytics.calculate_unit_economics(0.0, 100.0, 0.8, 0.05)
    assert result["ltv_cac_ratio"] is None
    assert result["warnings"]


# ---------------------------------------------------------------- financial

def test_waterfall_stated_ending_mismatch_fails_reconciliation():
    result = FinancialAnalytics.calculate_arr_waterfall(
        1_000_000.0, 200_000.0, 150_000.0, 30_000.0, 70_000.0,
        stated_ending_arr=1_200_000.0,
    )
    assert result["reconciled"] is False
    assert result["reconciliation"]["stated_ending_arr"]["passed"] is False
    assert result["nrr"] == 1.05


def test_runway_is_deterministic_and_seeded():
    args = dict(current_cash=500_000.0, monthly_burn_mean=25_000.0, monthly_burn_std=5_000.0)
    first = FinancialAnalytics.run_runway_simulation(**args)
    second = FinancialAnalytics.run_runway_simulation(**args)
    assert first["p50_median_runway_months"] == second["p50_median_runway_months"]
    assert first["seed"] == 42
    assert first["distribution"] == "truncated_normal"

    lognormal = FinancialAnalytics.run_runway_simulation(**args, distribution="lognormal")
    assert lognormal["distribution"] == "lognormal"
    assert 0 < lognormal["p10_runway_months"] <= lognormal["p90_runway_months"]


def test_runway_rejects_non_positive_cash():
    result = FinancialAnalytics.run_runway_simulation(0.0, 25_000.0, 5_000.0)
    assert result["status"] == "ERROR"


# ---------------------------------------------------------------- clinical

def test_clinical_zero_cells_use_correction():
    result = ClinicalAnalytics.calculate_contingency_statistics(10, 0, 2, 88)
    assert any("Haldane" in w for w in result["warnings"])
    assert np.isfinite(result["odds_ratio"])
    assert result["odds_ratio_95_ci"][0] < result["odds_ratio"] < result["odds_ratio_95_ci"][1]


def test_clinical_reports_methods_and_intervals():
    result = ClinicalAnalytics.calculate_contingency_statistics(20, 80, 5, 95)
    assert result["p_value_method"] == "fisher_exact_two_sided"
    assert result["relative_risk_95_ci"] is not None
    assert result["sample_size"] == 200
    assert result["fisher_exact_p_value"] < 0.05


# ---------------------------------------------------------------- operations

def test_operations_coerces_mixed_inputs_and_reports_sla():
    values = [10, "12.5", np.float64(8.0), None, -1, 15, 9, 11, 13, 14, 10.5]
    result = OperationsAnalytics.analyze_lead_times(values, sla_hours=13)
    assert result["sample_size"] == 9
    assert result["dropped_invalid"] == 2
    assert result["breach_count"] == 2
    assert result["breach_rate"] == pytest.approx(2 / 9, abs=1e-4)


def test_littles_law_rejects_negative_inputs():
    result = OperationsAnalytics.calculate_littles_law(-1.0, 2.0)
    assert result["status"] == "ERROR"
