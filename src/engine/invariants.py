"""
Deterministic Invariant Checker for Data Analysis.
Enforces statistical, schema, and logical invariants before any claim or metric is presented to users.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pandas as pd


class InvariantViolation(Exception):
    """Raised when an analytical assertion or statistical invariant fails."""
    pass


def _as_float(value: Any) -> Optional[float]:
    """Coerce a cell to a finite float, or return None.

    DynamoDB returns ``Decimal`` and DuckDB returns NumPy scalars; calling
    ``math.isnan`` on either used to raise instead of reporting a violation.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


class InvariantChecker:
    """Automated data quality and statistical sanity verification."""

    @staticmethod
    def verify_sample_size(n: int, min_threshold: int = 30) -> Dict[str, Any]:
        """Verify sample size satisfies minimum statistical power requirements."""
        passed = n >= min_threshold
        warning = (
            None
            if passed
            else f"Sample size ({n}) is below recommended threshold "
            f"({min_threshold}) for asymptotic normality."
        )
        return {
            "name": "sample_size_check",
            "passed": passed,
            "sample_size": n,
            "threshold": min_threshold,
            "warning": warning,
        }

    @staticmethod
    def verify_probabilities(values: List[float], col_name: str = "metric") -> Dict[str, Any]:
        """Assert that values representing rates or probabilities strictly fall within [0.0, 1.0]."""
        parsed = [_as_float(v) for v in values]
        invalid = [v for v in parsed if v is not None and (v < 0.0 or v > 1.0)]
        passed = len(invalid) == 0
        warning = (
            None
            if passed
            else f"Detected {len(invalid)} values outside valid [0, 1] probability "
            f"range in '{col_name}'."
        )
        return {
            "name": f"probability_range_check_{col_name}",
            "passed": passed,
            "invalid_count": len(invalid),
            "warning": warning,
        }

    @staticmethod
    def verify_non_negative(values: List[float], col_name: str = "metric") -> Dict[str, Any]:
        """Assert that values representing counts, durations, or revenues are non-negative."""
        parsed = [_as_float(v) for v in values]
        invalid = [v for v in parsed if v is not None and v < 0.0]
        passed = len(invalid) == 0
        warning = (
            None
            if passed
            else f"Detected {len(invalid)} negative values in non-negative "
            f"metric '{col_name}'."
        )
        return {
            "name": f"non_negative_check_{col_name}",
            "passed": passed,
            "invalid_count": len(invalid),
            "warning": warning,
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
        warning = (
            None
            if passed
            else f"Reconciliation discrepancy of {diff:.4f} between calculated "
            f"({expected:.2f}) and stated ({ending_val:.2f}) amounts."
        )
        return {
            "name": "reconciliation_check",
            "passed": passed,
            "expected": expected,
            "actual": ending_val,
            "discrepancy": diff,
            "warning": warning,
        }

    @classmethod
    def _apply_rule(cls, df: pd.DataFrame, rule: Any) -> Optional[Dict[str, Any]]:
        """Run one declarative rule; unknown or malformed rules fail loudly."""
        if not isinstance(rule, dict):
            return {
                "name": "invalid_rule",
                "passed": False,
                "warning": "Invariant rules must be objects.",
            }
        kind = str(rule.get("type") or "").lower()

        if kind in {"probability", "non_negative"}:
            column = str(rule.get("column") or "")
            if column not in df.columns:
                return {
                    "name": f"{kind}_check_{column}",
                    "passed": False,
                    "warning": f"Column '{column}' is not present in the result.",
                }
            values: List[float] = []
            for value in df[column].tolist():
                try:
                    if value is None or pd.isna(value):
                        continue
                    values.append(float(value))
                except (TypeError, ValueError):
                    continue
            if kind == "probability":
                return cls.verify_probabilities(values, column)
            return cls.verify_non_negative(values, column)

        if kind == "reconciliation":
            try:
                return cls.verify_reconciliation(
                    float(rule["beginning"]),
                    float(rule["additions"]),
                    float(rule["subtractions"]),
                    float(rule["ending"]),
                    float(rule.get("tolerance", 1e-4)),
                )
            except (KeyError, TypeError, ValueError):
                return {
                    "name": "reconciliation_check",
                    "passed": False,
                    "warning": "Reconciliation rule needs numeric beginning, "
                    "additions, subtractions and ending values.",
                }

        return {
            "name": f"unknown_rule_{kind or 'unnamed'}",
            "passed": False,
            "warning": f"Unsupported invariant rule type '{kind or 'unnamed'}'.",
        }

    @classmethod
    def run_suite(
        cls,
        df: pd.DataFrame,
        rules: Optional[List[Dict[str, Any]]] = None,
        enforce_sample_size: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a complete verification suite against a resulting dataframe.

        ``enforce_sample_size`` must be False when the frame is itself an
        aggregate (a one-row ``SELECT SUM(...)``), because a row-count threshold
        says nothing about the data behind it.

        ``rules`` adds optional declarative checks:
        ``{"type": "probability", "column": "rate"}``,
        ``{"type": "non_negative", "column": "revenue"}`` or
        ``{"type": "reconciliation", "beginning": .., "additions": ..,
        "subtractions": .., "ending": ..}``.
        """
        results: List[Dict[str, Any]] = []
        all_passed = True

        # Baseline checks
        n_rows = len(df)
        if enforce_sample_size:
            sz_check = cls.verify_sample_size(n_rows)
        else:
            sz_check = {
                "name": "sample_size_check",
                "passed": True,
                "applicable": False,
                "sample_size": n_rows,
                "warning": None,
            }
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

        for rule in rules or []:
            check = cls._apply_rule(df, rule)
            if check is None:
                continue
            results.append(check)
            if not check["passed"]:
                all_passed = False

        return {
            "all_passed": all_passed,
            "checks": results,
            "row_count": n_rows,
            "columns": list(df.columns)
        }
