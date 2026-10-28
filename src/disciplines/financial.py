"""
Financial & RevOps Analytics Discipline Module.

Every result declares its assumptions and runs the identity it claims to
reconcile. The previous version returned ``reconciled: True`` unconditionally.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from engine.invariants import InvariantChecker


class FinancialAnalytics:
    """Deterministic financial revenue and runway analytics."""

    @staticmethod
    def calculate_arr_waterfall(
        beginning_arr: float,
        new_arr: float,
        expansion_arr: float,
        contraction_arr: float,
        churn_arr: float,
        stated_ending_arr: Optional[float] = None,
    ) -> Dict[str, Any]:
        """ARR waterfall with NRR/GRR and an explicit reconciliation check."""
        net_arr_change = new_arr + expansion_arr - contraction_arr - churn_arr
        ending_arr = beginning_arr + net_arr_change

        nrr = (
            (beginning_arr + expansion_arr - contraction_arr - churn_arr) / beginning_arr
            if beginning_arr > 0
            else None
        )
        grr = (
            (beginning_arr - contraction_arr - churn_arr) / beginning_arr
            if beginning_arr > 0
            else None
        )

        identity = InvariantChecker.verify_reconciliation(
            beginning_arr, new_arr + expansion_arr, contraction_arr + churn_arr, ending_arr
        )
        reconciliation: Dict[str, Any] = {
            "identity": identity,
            "identity_passed": bool(identity["passed"]),
        }

        reconciled = bool(identity["passed"])
        if stated_ending_arr is not None:
            stated = InvariantChecker.verify_reconciliation(
                beginning_arr,
                new_arr + expansion_arr,
                contraction_arr + churn_arr,
                stated_ending_arr,
            )
            reconciliation["stated_ending_arr"] = stated
            reconciled = reconciled and bool(stated["passed"])

        warnings = []
        if beginning_arr <= 0:
            warnings.append("Beginning ARR is not positive; NRR and GRR are undefined.")

        return {
            "beginning_arr": round(beginning_arr, 2),
            "new_arr": round(new_arr, 2),
            "expansion_arr": round(expansion_arr, 2),
            "contraction_arr": round(contraction_arr, 2),
            "churn_arr": round(churn_arr, 2),
            "net_arr_change": round(net_arr_change, 2),
            "ending_arr": round(ending_arr, 2),
            "nrr": round(nrr, 4) if nrr is not None else None,
            "grr": round(grr, 4) if grr is not None else None,
            "reconciled": reconciled,
            "reconciliation": reconciliation,
            "warnings": warnings,
            "assumptions": [
                "All amounts are in the same currency unit and period.",
                "NRR excludes new ARR by definition; GRR excludes expansion and new ARR.",
            ],
        }

    @staticmethod
    def run_runway_simulation(
        current_cash: float,
        monthly_burn_mean: float,
        monthly_burn_std: float,
        num_simulations: int = 2000,
        seed: int = 42,
        max_months: int = 120,
        distribution: str = "truncated_normal",
    ) -> Dict[str, Any]:
        """
        Deterministic Monte Carlo runway.

        Uses a local ``Generator`` (not the global NumPy RNG), records the seed
        and the distribution in the output, and clips burn at zero.
        """
        if current_cash <= 0:
            return {"status": "ERROR", "error": "Current cash must be positive."}
        if monthly_burn_mean <= 0:
            return {"status": "ERROR", "error": "Mean monthly burn must be positive."}
        if monthly_burn_std < 0:
            return {"status": "ERROR", "error": "Monthly burn standard deviation cannot be negative."}
        if distribution not in ("truncated_normal", "lognormal"):
            return {"status": "ERROR", "error": "distribution must be 'truncated_normal' or 'lognormal'."}

        simulations = max(1, min(int(num_simulations), 20000))
        horizon = max(1, min(int(max_months), 600))
        rng = np.random.default_rng(seed)

        if distribution == "lognormal":
            if monthly_burn_mean <= 0 or monthly_burn_std <= 0:
                return {"status": "ERROR", "error": "Lognormal burn needs a positive mean and standard deviation."}
            sigma = np.sqrt(np.log(1 + (monthly_burn_std / monthly_burn_mean) ** 2))
            mu = np.log(monthly_burn_mean) - 0.5 * sigma**2
            draws = rng.lognormal(mu, sigma, size=(simulations, horizon))
        else:
            draws = rng.normal(monthly_burn_mean, monthly_burn_std, size=(simulations, horizon))
            draws = np.clip(draws, 0.0, None)

        cumulative = np.cumsum(draws, axis=1)
        runway = (cumulative < current_cash).sum(axis=1).astype(float)

        return {
            "current_cash": current_cash,
            "monthly_burn_mean": monthly_burn_mean,
            "monthly_burn_std": monthly_burn_std,
            "p10_runway_months": float(np.percentile(runway, 10)),
            "p50_median_runway_months": float(np.percentile(runway, 50)),
            "p90_runway_months": float(np.percentile(runway, 90)),
            "probability_survive_12m": float(np.mean(runway >= 12)),
            "probability_survive_24m": float(np.mean(runway >= 24)),
            "seed": int(seed),
            "num_simulations": simulations,
            "max_months": horizon,
            "distribution": distribution,
            "assumptions": [
                "Burn is independent month to month with constant mean and standard deviation.",
                "Revenue is not modelled; burn is treated as net burn.",
                "Runway is capped at max_months; longer survivals are reported as the cap.",
            ],
        }
