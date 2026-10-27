"""
Financial & RevOps Analytics Discipline Module.
Calculates ARR/MRR Waterfall, NRR, Gross Margin, and Runway Monte Carlo simulations.
"""

from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd
import numpy as np


class FinancialAnalytics:
    """Deterministic financial revenue and runway analytics."""

    @staticmethod
    def calculate_arr_waterfall(
        beginning_arr: float,
        new_arr: float,
        expansion_arr: float,
        contraction_arr: float,
        churn_arr: float
    ) -> Dict[str, Any]:
        """
        Compute GAAP/SaaS ARR Waterfall with reconciled Net ARR and NRR.
        """
        net_arr_change = new_arr + expansion_arr - contraction_arr - churn_arr
        ending_arr = beginning_arr + net_arr_change
        
        # Net Revenue Retention (NRR) = (Beginning ARR + Expansion - Contraction - Churn) / Beginning ARR
        nrr = ((beginning_arr + expansion_arr - contraction_arr - churn_arr) / beginning_arr) if beginning_arr > 0 else 0.0
        # Gross Revenue Retention (GRR) = (Beginning ARR - Contraction - Churn) / Beginning ARR
        grr = ((beginning_arr - contraction_arr - churn_arr) / beginning_arr) if beginning_arr > 0 else 0.0

        return {
            "beginning_arr": round(beginning_arr, 2),
            "new_arr": round(new_arr, 2),
            "expansion_arr": round(expansion_arr, 2),
            "contraction_arr": round(contraction_arr, 2),
            "churn_arr": round(churn_arr, 2),
            "net_arr_change": round(net_arr_change, 2),
            "ending_arr": round(ending_arr, 2),
            "nrr": round(nrr, 4),
            "grr": round(grr, 4),
            "reconciled": True
        }

    @staticmethod
    def run_runway_simulation(
        current_cash: float,
        monthly_burn_mean: float,
        monthly_burn_std: float,
        num_simulations: int = 2000,
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Deterministic Monte Carlo simulation of cash runway distribution.
        """
        np.random.seed(seed)
        simulated_runways = []

        for _ in range(num_simulations):
            cash = current_cash
            months = 0
            while cash > 0 and months < 120:
                burn = max(0, np.random.normal(monthly_burn_mean, monthly_burn_std))
                cash -= burn
                months += 1
            simulated_runways.append(months)

        arr = np.array(simulated_runways)
        return {
            "current_cash": current_cash,
            "monthly_burn_mean": monthly_burn_mean,
            "p10_runway_months": float(np.percentile(arr, 10)),
            "p50_median_runway_months": float(np.percentile(arr, 50)),
            "p90_runway_months": float(np.percentile(arr, 90)),
            "probability_survive_12m": float(np.mean(arr >= 12)),
            "probability_survive_24m": float(np.mean(arr >= 24))
        }
