"""
Product Analytics Discipline Module.
Calculates Funnels, Cohort Retention, and Survival Drop-offs deterministically.
"""

from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd
import numpy as np


class ProductAnalytics:
    """Deterministic product & user engagement analytics."""

    @staticmethod
    def calculate_funnel(df: pd.DataFrame, step_columns: List[str]) -> Dict[str, Any]:
        """
        Compute step-by-step funnel conversion rates and absolute drop-offs.
        """
        funnel_steps = []
        prev_count = None
        first_count = None

        for idx, col in enumerate(step_columns):
            if col not in df.columns:
                continue
            # Count users who completed the step (non-null or positive)
            step_completed = df[col].notnull() & (df[col] != 0)
            count = int(step_completed.sum())

            if first_count is None:
                first_count = count
            
            conversion_from_start = (count / first_count) if first_count and first_count > 0 else 0.0
            step_to_step_conv = (count / prev_count) if prev_count and prev_count > 0 else 1.0
            drop_off_count = (prev_count - count) if prev_count is not None else 0

            funnel_steps.append({
                "step_index": idx + 1,
                "step_name": col,
                "users": count,
                "step_conversion_rate": round(step_to_step_conv, 4),
                "overall_conversion_rate": round(conversion_from_start, 4),
                "drop_off": max(0, drop_off_count)
            })
            prev_count = count

        return {
            "total_initial_users": first_count or 0,
            "steps": funnel_steps
        }

    @staticmethod
    def calculate_retention_matrix(
        df: pd.DataFrame,
        user_col: str,
        cohort_col: str,
        period_col: str
    ) -> Dict[str, Any]:
        """
        Compute cohort retention matrix with exact percentage retention per interval.
        """
        grouped = df.groupby([cohort_col, period_col])[user_col].nunique().reset_index()
        cohort_sizes = df.groupby(cohort_col)[user_col].nunique().to_dict()

        retention_matrix = []
        for cohort, size in cohort_sizes.items():
            cohort_data = grouped[grouped[cohort_col] == cohort]
            row = {"cohort": str(cohort), "cohort_size": int(size), "periods": {}}
            for _, r in cohort_data.iterrows():
                period = str(r[period_col])
                count = int(r[user_col])
                rate = round(count / size, 4) if size > 0 else 0.0
                row["periods"][period] = {"count": count, "retention_rate": rate}
            retention_matrix.append(row)

        return {
            "matrix": retention_matrix,
            "num_cohorts": len(cohort_sizes)
        }
