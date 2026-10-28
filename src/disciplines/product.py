"""
Product Analytics Discipline Module.

Funnels are *sequential*: a user counts at step N only if they completed every
earlier step. Counting each step's non-null flag independently (the previous
behaviour) can produce conversion above 100% and overstates late steps.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class ProductAnalytics:
    """Deterministic product & user engagement analytics."""

    @staticmethod
    def _flag(series: pd.Series) -> pd.Series:
        return series.notna() & (series != 0)

    @staticmethod
    def calculate_funnel(
        df: pd.DataFrame,
        step_columns: List[str],
        user_column: Optional[str] = None,
        order_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute a sequential funnel.

        Without ``user_column``/``order_column`` a row is one journey and steps
        are combined with AND. With both, each user's events are ordered by
        ``order_column`` and a step only counts if it happens after the previous
        one (first-occurrence semantics).
        """
        steps = [str(c) for c in step_columns]
        if not steps:
            raise ValueError("A funnel needs at least one step column.")
        missing = [c for c in steps if c not in df.columns]
        if missing:
            raise ValueError(f"Unknown funnel columns: {', '.join(missing)}")

        if user_column or order_column:
            if not (user_column and order_column):
                raise ValueError("Ordered funnels need both user_column and order_column.")
            for column in (user_column, order_column):
                if column not in df.columns:
                    raise ValueError(f"Unknown column: {column}")
            return ProductAnalytics._ordered_funnel(df, steps, user_column, order_column)

        counts: List[int] = []
        completed = pd.Series(True, index=df.index)
        for column in steps:
            completed = completed & ProductAnalytics._flag(df[column])
            counts.append(int(completed.sum()))

        return ProductAnalytics._shape(counts, steps, method="sequential_and")

    @staticmethod
    def _ordered_funnel(
        df: pd.DataFrame, steps: List[str], user_column: str, order_column: str
    ) -> Dict[str, Any]:
        work = df[[user_column, order_column, *steps]].copy()
        work[order_column] = pd.to_datetime(work[order_column], errors="coerce", format="mixed")
        work = work.dropna(subset=[order_column])
        work = work.sort_values([user_column, order_column], kind="mergesort")

        flags = work[steps].apply(ProductAnalytics._flag).to_numpy(dtype=bool)
        users = work[user_column].to_numpy()
        n_steps = len(steps)
        counts = [0] * n_steps

        stage = -1
        current_user = None
        for index in range(len(flags)):
            user = users[index]
            if user != current_user:
                if current_user is not None:
                    for step_index in range(stage + 1):
                        counts[step_index] += 1
                current_user = user
                stage = -1
            nxt = stage + 1
            if nxt < n_steps and flags[index][nxt]:
                stage = nxt
        if current_user is not None:
            for step_index in range(stage + 1):
                counts[step_index] += 1

        return ProductAnalytics._shape(counts, steps, method="sequential_ordered")

    @staticmethod
    def _shape(counts: List[int], steps: List[str], method: str) -> Dict[str, Any]:
        funnel_steps: List[Dict[str, Any]] = []
        first_count = counts[0] if counts else 0
        previous: Optional[int] = None
        for index, (column, count) in enumerate(zip(steps, counts, strict=False)):
            step_rate = (count / previous) if previous not in (None, 0) else 1.0
            overall = (count / first_count) if first_count else 0.0
            drop_off = (previous - count) if previous is not None else 0
            funnel_steps.append(
                {
                    "step_index": index + 1,
                    "step_name": column,
                    "users": int(count),
                    "step_conversion_rate": round(float(step_rate), 4),
                    "overall_conversion_rate": round(float(overall), 4),
                    "drop_off": int(max(0, drop_off)),
                }
            )
            previous = count

        return {
            "total_initial_users": int(first_count),
            "steps": funnel_steps,
            "method": method,
            "monotonic": all(
                funnel_steps[i]["users"] >= funnel_steps[i + 1]["users"]
                for i in range(len(funnel_steps) - 1)
            ),
        }

    @staticmethod
    def calculate_retention_matrix(
        df: pd.DataFrame,
        user_col: str,
        cohort_col: str,
        period_col: str,
        max_periods: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compute a cohort retention matrix.

        Periods are ordered numerically when possible and each cohort carries a
        ``complete`` flag: a cohort whose latest observed period is older than
        the global latest is complete, otherwise it is still accumulating and
        its right-hand edge must not be read as churn.
        """
        for column in (user_col, cohort_col, period_col):
            if column not in df.columns:
                raise ValueError(f"Unknown column: {column}")

        work = df[[user_col, cohort_col, period_col]].copy()
        work[period_col] = ProductAnalytics._sortable_period(work[period_col])
        work = work.dropna(subset=[period_col])

        grouped = work.groupby([cohort_col, period_col])[user_col].nunique()
        cohort_sizes = work.groupby(cohort_col)[user_col].nunique().to_dict()
        global_max = work[period_col].max()

        matrix: List[Dict[str, Any]] = []
        for cohort in sorted(cohort_sizes, key=str):
            size = int(cohort_sizes[cohort])
            rows = grouped.loc[cohort] if cohort in grouped.index.get_level_values(0) else None
            periods: Dict[str, Any] = {}
            observed = []
            if rows is not None:
                for period, count in rows.items():
                    if max_periods is not None and period > max_periods:
                        continue
                    observed.append(period)
                    periods[ProductAnalytics._period_label(period)] = {
                        "count": int(count),
                        "retention_rate": round(count / size, 4) if size else 0.0,
                    }
            matrix.append(
                {
                    "cohort": str(cohort),
                    "cohort_size": size,
                    "periods": periods,
                    "complete": bool(observed and max(observed) >= global_max),
                }
            )

        return {
            "matrix": matrix,
            "num_cohorts": len(cohort_sizes),
            "period_order": [ProductAnalytics._period_label(p) for p in sorted(work[period_col].unique())],
            "global_max_period": ProductAnalytics._period_label(global_max) if global_max is not None else None,
        }

    @staticmethod
    def _sortable_period(series: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().all():
            return numeric.astype("Int64")
        parsed = pd.to_datetime(series, errors="coerce", format="mixed")
        if parsed.notna().all():
            return parsed
        return series.astype(str)

    @staticmethod
    def _period_label(value: Any) -> str:
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            return str(pd.Timestamp(value))[:10]
        try:
            number = float(value)
            return str(int(number)) if number.is_integer() else f"{number:g}"
        except (TypeError, ValueError):
            return str(value)
