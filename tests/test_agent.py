"""
Unit and Integration Test Suite for OmniAnalyst Platform.
Verifies determinism, security boundaries, and discipline analytics.
"""

import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from engine.sandbox import DeterministicSandbox, SecurityViolation
from engine.invariants import InvariantChecker
from disciplines.product import ProductAnalytics
from disciplines.financial import FinancialAnalytics
from disciplines.operations import OperationsAnalytics
from disciplines.growth import GrowthAnalytics
from disciplines.clinical import ClinicalAnalytics


def test_sandbox_sql_execution():
    """Verify DuckDB executes analytical queries deterministically."""
    df = pd.DataFrame({
        "category": ["A", "A", "B", "B", "C"],
        "revenue": [100.0, 200.0, 150.0, 300.0, 50.0]
    })
    sandbox = DeterministicSandbox()
    sandbox.register_dataframe("sales", df)

    result = sandbox.execute_sql("SELECT category, SUM(revenue) as total_rev FROM sales GROUP BY category ORDER BY total_rev DESC")
    assert result["status"] == "SUCCESS"
    assert result["row_count"] == 3
    assert result["data"][0]["category"] == "B"
    assert result["data"][0]["total_rev"] == 450.0


def test_sandbox_security_ast_blocking():
    """Verify AST inspector rejects malicious code injection."""
    sandbox = DeterministicSandbox()
    malicious_code = "import os\nos.system('echo compromised')"
    res = sandbox.execute_python(malicious_code)
    assert res["status"] == "SECURITY_VIOLATION"


def test_invariant_reconciliation():
    """Verify mathematical reconciliation assertions."""
    # Reconciled case: 1000 + 200 - 50 = 1150
    recon_pass = InvariantChecker.verify_reconciliation(1000.0, 200.0, 50.0, 1150.0)
    assert recon_pass["passed"] is True

    # Discrepancy case:
    recon_fail = InvariantChecker.verify_reconciliation(1000.0, 200.0, 50.0, 1100.0)
    assert recon_fail["passed"] is False


def test_product_funnel_analytics():
    """Verify Funnel conversion calculations."""
    df = pd.DataFrame({
        "signup": [1, 1, 1, 1, 1],
        "onboarded": [1, 1, 1, 0, 0],
        "paid": [1, 1, 0, 0, 0]
    })
    funnel = ProductAnalytics.calculate_funnel(df, ["signup", "onboarded", "paid"])
    assert funnel["total_initial_users"] == 5
    assert funnel["steps"][0]["users"] == 5
    assert funnel["steps"][1]["users"] == 3
    assert funnel["steps"][2]["users"] == 2
    assert funnel["steps"][2]["overall_conversion_rate"] == 0.4


def test_financial_waterfall():
    """Verify SaaS ARR waterfall and NRR calculation."""
    res = FinancialAnalytics.calculate_arr_waterfall(
        beginning_arr=1000000.0,
        new_arr=200000.0,
        expansion_arr=150000.0,
        contraction_arr=30000.0,
        churn_arr=70000.0
    )
    assert res["ending_arr"] == 1250000.0
    assert res["nrr"] == 1.05  # (1,000,000 + 150,000 - 30,000 - 70,000) / 1,000,000 = 1.05
    assert res["reconciled"] is True


def test_clinical_fisher_exact():
    """Verify 2x2 contingency table Fisher's Exact test."""
    res = ClinicalAnalytics.calculate_contingency_statistics(
        exposed_cases=20,
        exposed_non_cases=80,
        unexposed_cases=5,
        unexposed_non_cases=95
    )
    assert "odds_ratio" in res
    assert res["odds_ratio"] > 1.0
    assert res["fisher_exact_p_value"] < 0.05
    assert res["statistically_significant_at_05"] is True
