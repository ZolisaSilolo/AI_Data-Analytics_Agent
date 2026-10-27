"""
Deterministic Invariant Checker for Data Analysis.
Enforces statistical, schema, and logical invariants before any claim or metric is presented to users.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class InvariantViolation(Exception):
    """Raised when an analytical assertion or statistical invariant fails."""
    pass


class InvariantChecker:
    """Automated data quality and statistical sanity verification."""

    @staticmethod
    def verify_sample_size(n: int, min_threshold: int = 30) -> Dict[str, Any]:
        """Verify sample size satisfies minimum statistical power requirements."""
        passed = n >= min_threshold
        return {
            "name": "sample_size_check",
            "passed": passed,
            "sample_size": n,
            "threshold": min_threshold,
            "warning": None if passed else f"Sample size ({n}) is below recommended threshold ({min_threshold}) for asymptotic normality."
        }

    @staticmethod
    def verify_probabilities(values: List[float], col_name: str = "metric") -> Dict[str, Any]:
        """Assert that values representing rates or probabilities strictly fall within [0.0, 1.0]."""
        invalid = [v for v in values if v is not None and (v < 0.0 or v > 1.0 or math.isnan(v))]
        passed = len(invalid) == 0
        return {
            "name": f"probability_range_check_{col_name}",
            "passed": passed,
            "invalid_count": len(invalid),
            "warning": None if passed else f"Detected {len(invalid)} values outside valid [0, 1] probability range in '{col_name}'."
        }

    @staticmethod
    def verify_non_negative(values: List[float], col_name: str = "metric") -> Dict[str, Any]:
        """Assert that values representing counts, durations, or revenues are non-negative."""
        invalid = [v for v in values if v is not None and (v < 0.0 or math.isnan(v))]
        passed = len(invalid) == 0
        return {
            "name": f"non_negative_check_{col_name}",
            "passed": passed,
            "invalid_count": len(invalid),
            "warning": None if passed else f"Detected {len(invalid)} negative values in non-negative metric '{col_name}'."
        }

    @staticmethod
    def verify_reconciliation(
        beginning_val: float,
        additions: float,
        subtractions: float,
        ending_val: float,
        tolerance: float = 1e-4
    ) -> Dict[str, Any]:
        """Verify mathematical reconciliation (e.g., beginning ARR + new - churn == ending ARR)."""
        expected = beginning_val + additions - subtractions
        diff = abs(expected - ending_val)
        passed = diff <= tolerance
        return {
            "name": "reconciliation_check",
            "passed": passed,
            "expected": expected,
            "actual": ending_val,
            "discrepancy": diff,
            "warning": None if passed else f"Reconciliation discrepancy of {diff:.4f} between calculated ({expected:.2f}) and stated ({ending_val:.2f}) amounts."
        }

    @classmethod
    def run_suite(cls, df: pd.DataFrame, rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Execute a complete verification suite against a resulting dataframe.
        """
        results: List[Dict[str, Any]] = []
        all_passed = True

        # Baseline checks
        n_rows = len(df)
        sz_check = cls.verify_sample_size(n_rows)
        results.append(sz_check)
        if not sz_check["passed"]:
            all_passed = False

        # Null-rate check across all columns
        null_rates = (df.isnull().sum() / max(1, n_rows)).to_dict()
        for col, rate in null_rates.items():
            if rate > 0.5:
                results.append({
                    "name": f"high_null_rate_{col}",
                    "passed": False,
                    "warning": f"Column '{col}' has {rate*100:.1f}% missing values."
                })
                all_passed = False

        return {
            "all_passed": all_passed,
            "checks": results,
            "row_count": n_rows,
            "columns": list(df.columns)
        }
