"""
Operations & Supply Chain Analytics Discipline Module.

Little's Law, lead-time distribution and SLA percentiles. Inputs are coerced
defensively because AWS returns ``Decimal`` and CSVs return strings.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
from scipy import stats


class OperationsAnalytics:
    """Deterministic operations and logistics analytics."""

    @staticmethod
    def calculate_littles_law(throughput_rate: float, cycle_time_hours: float) -> Dict[str, Any]:
        """Little's Law: WIP = throughput (lambda) * cycle time (W)."""
        if throughput_rate < 0 or cycle_time_hours < 0:
            return {"status": "ERROR", "error": "Throughput and cycle time must be non-negative."}
        wip = throughput_rate * cycle_time_hours
        return {
            "throughput_rate_units_per_hour": round(throughput_rate, 4),
            "cycle_time_hours": round(cycle_time_hours, 4),
            "theoretical_wip_units": round(wip, 2),
            "assumptions": [
                "The system is in steady state and conserved (no leaks or rework).",
                "Throughput and cycle time refer to the same boundary and period.",
            ],
        }

    @staticmethod
    def analyze_lead_times(lead_times: List[Any], sla_hours: float | None = None) -> Dict[str, Any]:
        """Summarise a lead-time distribution and SLA risk."""
        clean: List[float] = []
        dropped = 0
        for value in lead_times or []:
            try:
                number = float(value)
            except (TypeError, ValueError):
                dropped += 1
                continue
            if not math.isfinite(number) or number < 0:
                dropped += 1
                continue
            clean.append(number)

        if len(clean) < 5:
            return {
                "status": "ERROR",
                "error": "Insufficient data points for distribution fitting (need at least 5).",
                "sample_size": len(clean),
                "dropped_invalid": dropped,
            }

        arr = np.asarray(clean, dtype=float)
        result: Dict[str, Any] = {
            "sample_size": len(arr),
            "dropped_invalid": dropped,
            "mean_lead_time": round(float(np.mean(arr)), 2),
            "std_lead_time": round(float(np.std(arr, ddof=1)), 2),
            "p50_median": round(float(np.median(arr)), 2),
            "p90": round(float(np.percentile(arr, 90)), 2),
            "p95_buffer_target": round(float(np.percentile(arr, 95)), 2),
            "p99_worst_case": round(float(np.percentile(arr, 99)), 2),
            "skewness": round(float(stats.skew(arr)), 3),
            "assumptions": [
                "Percentiles are empirical (no fitted distribution).",
                "ddof=1 is used for the standard deviation.",
            ],
        }
        if sla_hours is not None:
            if sla_hours <= 0:
                return {"status": "ERROR", "error": "sla_hours must be positive."}
            breaches = int((arr > sla_hours).sum())
            result["sla_hours"] = sla_hours
            result["breach_count"] = breaches
            result["breach_rate"] = round(breaches / len(arr), 4)
        return result
