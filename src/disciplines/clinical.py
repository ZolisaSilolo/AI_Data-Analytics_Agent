"""
Clinical & Biostatistical Analytics Discipline Module.
Implements Odds Ratios, Relative Risks, and Fisher's Exact / Chi-Square hypothesis testing.
"""

from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np
from scipy import stats


class ClinicalAnalytics:
    """Deterministic clinical, biomedical, and epidemiology analytics."""

    @staticmethod
    def calculate_contingency_statistics(
        exposed_cases: int,
        exposed_non_cases: int,
        unexposed_cases: int,
        unexposed_non_cases: int
    ) -> Dict[str, Any]:
        """
        Compute Odds Ratio (OR), Relative Risk (RR), and Fisher's Exact Test p-value
        from a standard 2x2 contingency table:
                     Cases      Non-Cases
        Exposed:       a            b
        Unexposed:     c            d
        """
        a, b, c, d = exposed_cases, exposed_non_cases, unexposed_cases, unexposed_non_cases
        table = [[a, b], [c, d]]

        # Odds Ratio = (a * d) / (b * c)
        odds_ratio, p_value = stats.fisher_exact(table)

        # 95% Confidence Interval for Odds Ratio (Wald's approximation)
        if a > 0 and b > 0 and c > 0 and d > 0:
            log_or = np.log(odds_ratio)
            se_log_or = np.sqrt(1/a + 1/b + 1/c + 1/d)
            ci_lower = np.exp(log_or - 1.96 * se_log_or)
            ci_upper = np.exp(log_or + 1.96 * se_log_or)
        else:
            ci_lower, ci_upper = None, None

        # Relative Risk = [a / (a + b)] / [c / (c + d)]
        risk_exposed = a / (a + b) if (a + b) > 0 else 0.0
        risk_unexposed = c / (c + d) if (c + d) > 0 else 0.0
        relative_risk = (risk_exposed / risk_unexposed) if risk_unexposed > 0 else None

        return {
            "contingency_table": {"exposed": [a, b], "unexposed": [c, d]},
            "odds_ratio": round(float(odds_ratio), 4),
            "odds_ratio_95_ci": [round(float(ci_lower), 4), round(float(ci_upper), 4)] if ci_lower else None,
            "relative_risk": round(float(relative_risk), 4) if relative_risk else None,
            "fisher_exact_p_value": float(p_value),
            "statistically_significant_at_05": bool(p_value < 0.05)
        }
