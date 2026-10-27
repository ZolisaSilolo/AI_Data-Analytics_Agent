"""
Operations & Supply Chain Analytics Discipline Module.
Implements Little's Law, Queueing Theory, and Lead-Time Variance fitting.
"""

from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from scipy import stats


class OperationsAnalytics:
    """Deterministic operations & logistics analytics."""

    @staticmethod
    def calculate_littles_law(throughput_rate: float, cycle_time_hours: float) -> Dict[str, Any]:
        """
        Little's Law: Work in Progress (WIP) = Throughput (lambda) * Cycle Time (W).
        """
        wip = throughput_rate * cycle_time_hours
        return {
            "throughput_rate_units_per_hour": round(throughput_rate, 4),
            "cycle_time_hours": round(cycle_time_hours, 4),
            "theoretical_wip_units": round(wip, 2)
        }

    @staticmethod
    def analyze_lead_times(lead_times: List[float]) -> Dict[str, Any]:
        """
        Fit lead-time distribution and evaluate SLA breach risks.
        """
        clean = [x for x in lead_times if x is not None and not np.isnan(x) and x >= 0]
        if len(clean) < 5:
            return {"error": "Insufficient data points for distribution fitting"}

        arr = np.array(clean)
        mean_lt = float(np.mean(arr))
        std_lt = float(np.std(arr))
        p95_lt = float(np.percentile(arr, 95))
        p99_lt = float(np.percentile(arr, 99))

        return {
            "sample_size": len(arr),
            "mean_lead_time": round(mean_lt, 2),
            "std_lead_time": round(std_lt, 2),
            "p50_median": round(float(np.median(arr)), 2),
            "p95_buffer_target": round(p95_lt, 2),
            "p99_worst_case": round(p99_lt, 2),
            "skewness": round(float(stats.skew(arr)), 3)
        }
