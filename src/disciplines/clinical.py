"""
Clinical & Biostatistical Analytics Discipline Module.

Implements odds ratios with a Haldane-Anscombe correction for zero cells, a
log-normal confidence interval, relative risk with its own interval, and
Fisher's exact test. Small-sample behaviour is stated, not hidden.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
from scipy import stats

from engine.invariants import InvariantChecker


class ClinicalAnalytics:
    """Deterministic clinical, biomedical and epidemiological analytics."""

    @staticmethod
    def calculate_contingency_statistics(
        exposed_cases: int,
        exposed_non_cases: int,
        unexposed_cases: int,
        unexposed_non_cases: int,
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Compute OR, RR and Fisher's exact p-value for a 2x2 table::

                         Cases      Non-Cases
            Exposed:       a            b
            Unexposed:     c            d
        """
        values = [exposed_cases, exposed_non_cases, unexposed_cases, unexposed_non_cases]
        if any(int(v) != v or v < 0 for v in values):
            return {"status": "ERROR", "error": "Contingency cells must be non-negative integers."}
        a, b, c, d = (int(v) for v in values)
        if a + b == 0 or c + d == 0:
            return {"status": "ERROR", "error": "Each exposure group needs at least one observation."}

        table = [[a, b], [c, d]]
        _, p_value = stats.fisher_exact(table)

        warnings: List[str] = []
        zero_cells = any(cell == 0 for cell in (a, b, c, d))
        a2, b2, c2, d2 = (cell + 0.5 for cell in (a, b, c, d)) if zero_cells else (a, b, c, d)
        if zero_cells:
            warnings.append("Zero cell(s): odds ratio and its interval use a Haldane-Anscombe +0.5 correction.")
        if min(a, b, c, d) < 5:
            warnings.append("At least one cell is below 5; Fisher's exact test is the appropriate choice (used).")

        odds_ratio = (a2 * d2) / (b2 * c2)
        log_or = math.log(odds_ratio)
        se_log_or = math.sqrt(1 / a2 + 1 / b2 + 1 / c2 + 1 / d2)
        z = float(stats.norm.ppf(1 - alpha / 2))
        ci_lower = math.exp(log_or - z * se_log_or)
        ci_upper = math.exp(log_or + z * se_log_or)

        risk_exposed = a / (a + b)
        risk_unexposed = c / (c + d)
        relative_risk = risk_exposed / risk_unexposed if risk_unexposed > 0 else None

        rr_ci = None
        if relative_risk is not None and a > 0 and c > 0:
            se_log_rr = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
            rr_ci = [
                round(math.exp(math.log(relative_risk) - z * se_log_rr), 4),
                round(math.exp(math.log(relative_risk) + z * se_log_rr), 4),
            ]

        sample_size = a + b + c + d
        invariants = InvariantChecker.verify_sample_size(sample_size)

        return {
            "contingency_table": {"exposed": [a, b], "unexposed": [c, d]},
            "sample_size": sample_size,
            "odds_ratio": round(float(odds_ratio), 4),
            "odds_ratio_95_ci": [round(float(ci_lower), 4), round(float(ci_upper), 4)],
            "odds_ratio_ci_method": "log_normal_wald"
            + ("_haldane_anscombe" if zero_cells else ""),
            "relative_risk": round(float(relative_risk), 4) if relative_risk is not None else None,
            "relative_risk_95_ci": rr_ci,
            "fisher_exact_p_value": float(p_value),
            "p_value_method": "fisher_exact_two_sided",
            "alpha": alpha,
            "statistically_significant_at_05": bool(p_value < alpha),
            "invariants": invariants,
            "warnings": warnings,
            "assumptions": [
                "Observations are independent; exposure and outcome are binary.",
                "No adjustment for confounders; this is an unstratified 2x2 analysis.",
                "No multiple-comparison correction is applied for a single test.",
            ],
        }

    @staticmethod
    def odds_ratio_from_rates(
        rate_exposed: float, rate_unexposed: float
    ) -> Dict[str, Any]:
        """Odds ratio implied by two risks, with the same interval convention."""
        if not (0 <= rate_exposed <= 1 and 0 <= rate_unexposed <= 1):
            return {"status": "ERROR", "error": "Rates must lie in [0, 1]."}
        if rate_exposed in (0.0, 1.0) or rate_unexposed in (0.0, 1.0):
            return {"status": "ERROR", "error": "Rates at 0 or 1 make the odds ratio undefined."}
        odds_exposed = rate_exposed / (1 - rate_exposed)
        odds_unexposed = rate_unexposed / (1 - rate_unexposed)
        return {
            "odds_ratio": round(odds_exposed / odds_unexposed, 4),
            "odds_exposed": round(odds_exposed, 4),
            "odds_unexposed": round(odds_unexposed, 4),
            "assumptions": ["Derived from risks; no sampling variance is available."],
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("nan")

    @staticmethod
    def normal_approximation_available(cells: List[int], minimum: int = 5) -> bool:
        return all(cell >= minimum for cell in cells) and bool(np.all(np.array(cells) >= 0))
