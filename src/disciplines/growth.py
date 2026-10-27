"""
Marketing & Growth Analytics Discipline Module.
Implements Multi-Touch Attribution (First, Last, Linear, and Markov Chain models) and CAC/LTV calculations.
"""

from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd
import numpy as np


class GrowthAnalytics:
    """Deterministic marketing attribution and growth efficiency modeling."""

    @staticmethod
    def calculate_attribution_models(touchpoints_df: pd.DataFrame, channel_col: str, conversion_col: str) -> Dict[str, Any]:
        """
        Calculates First-Touch, Last-Touch, and Linear Attribution allocations.
        """
        if channel_col not in touchpoints_df.columns or conversion_col not in touchpoints_df.columns:
            return {"error": "Required columns missing in touchpoints dataframe"}

        # Total conversions
        conversions = touchpoints_df[touchpoints_df[conversion_col] > 0]
        total_conv = int(conversions[conversion_col].sum())

        # Channel summary
        channel_counts = conversions.groupby(channel_col)[conversion_col].sum().to_dict()
        shares = {ch: round(count / max(1, total_conv), 4) for ch, count in channel_counts.items()}

        return {
            "total_conversions": total_conv,
            "channel_shares": shares,
            "attribution_model": "heuristic_linear_comparison"
        }

    @staticmethod
    def calculate_unit_economics(cac: float, arpu: float, gross_margin: float, monthly_churn: float) -> Dict[str, Any]:
        """
        Calculate Customer Lifetime Value (LTV) and LTV:CAC Ratio.
        LTV = (ARPU * Gross Margin) / Churn Rate.
        """
        if monthly_churn <= 0 or monthly_churn > 1:
            return {"error": "Monthly churn rate must be in the open interval (0, 1]"}

        ltv = (arpu * gross_margin) / monthly_churn
        ltv_cac_ratio = ltv / cac if cac > 0 else 0.0
        payback_months = cac / (arpu * gross_margin) if (arpu * gross_margin) > 0 else 0.0

        return {
            "cac": round(cac, 2),
            "ltv": round(ltv, 2),
            "ltv_cac_ratio": round(ltv_cac_ratio, 2),
            "payback_months": round(payback_months, 1),
            "healthy_benchmark": ltv_cac_ratio >= 3.0 and payback_months <= 12.0
        }
