"""
Marketing & Growth Analytics Discipline Module.

Attribution is only computed as multi-touch when the data can support it (a
user key and an ordered timestamp). Otherwise the result is explicitly labelled
as a single-touch channel share instead of pretending to be first/last/linear.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


class GrowthAnalytics:
    """Deterministic marketing attribution and growth efficiency modelling."""

    @staticmethod
    def calculate_attribution_models(
        touchpoints_df: pd.DataFrame,
        channel_col: str,
        conversion_col: str,
        user_column: Optional[str] = None,
        timestamp_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        for column in (channel_col, conversion_col):
            if column not in touchpoints_df.columns:
                return {"status": "ERROR", "error": f"Required column missing: {column}"}

        frame = touchpoints_df
        conversions = frame[pd.to_numeric(frame[conversion_col], errors="coerce").fillna(0) > 0]
        total_conv = float(pd.to_numeric(conversions[conversion_col], errors="coerce").sum())

        channel_totals = (
            pd.to_numeric(conversions[conversion_col], errors="coerce")
            .groupby(conversions[channel_col].astype(str))
            .sum()
            .sort_index()
        )
        shares = {
            str(channel): round(float(value) / max(1.0, total_conv), 4)
            for channel, value in channel_totals.items()
        }

        result: Dict[str, Any] = {
            "total_conversions": int(total_conv) if float(total_conv).is_integer() else round(total_conv, 4),
            "channel_shares": shares,
            "attribution_model": "single_touch_channel_share",
            "multi_touch_available": False,
            "notes": [
                "This is a share of converted rows by channel, not a multi-touch model."
            ],
        }

        if user_column and timestamp_column:
            model = GrowthAnalytics._multi_touch(
                frame, channel_col, conversion_col, user_column, timestamp_column
            )
            if model.get("status") == "SUCCESS":
                result["attribution_model"] = "multi_touch"
                result["multi_touch_available"] = True
                result["models"] = model["models"]
                result["converting_users"] = model["converting_users"]
                result["notes"] = model["notes"]
            else:
                result["notes"].append(model.get("error", "Multi-touch attribution unavailable."))
        else:
            result["notes"].append(
                "Pass user_column and timestamp_column for first/last/linear attribution."
            )

        return result

    @staticmethod
    def _multi_touch(
        df: pd.DataFrame,
        channel_col: str,
        conversion_col: str,
        user_col: str,
        time_col: str,
    ) -> Dict[str, Any]:
        for column in (user_col, time_col):
            if column not in df.columns:
                return {"status": "ERROR", "error": f"Required column missing: {column}"}

        work = df[[user_col, time_col, channel_col, conversion_col]].copy()
        work[time_col] = pd.to_datetime(work[time_col], errors="coerce", format="mixed")
        work[conversion_col] = pd.to_numeric(work[conversion_col], errors="coerce").fillna(0)
        work = work.dropna(subset=[time_col, channel_col, user_col])
        if work.empty:
            return {"status": "ERROR", "error": "No usable touchpoints after cleaning."}

        converting = set(work.loc[work[conversion_col] > 0, user_col])
        if not converting:
            return {"status": "ERROR", "error": "No converting users in this dataset."}

        touches = work[work[user_col].isin(converting)].sort_values(
            [user_col, time_col], kind="mergesort"
        )

        models: Dict[str, Dict[str, float]] = {
            "first_touch": {},
            "last_touch": {},
            "linear": {},
            "position_based": {},
        }
        for _, group in touches.groupby(user_col, sort=False):
            channels = group[channel_col].astype(str).tolist()
            ordered = [c for i, c in enumerate(channels) if i == 0 or c != channels[i - 1]]
            if not ordered:
                continue
            weight = 1.0 / len(ordered)
            models["first_touch"][ordered[0]] = models["first_touch"].get(ordered[0], 0.0) + 1.0
            models["last_touch"][ordered[-1]] = models["last_touch"].get(ordered[-1], 0.0) + 1.0
            for channel in ordered:
                models["linear"][channel] = models["linear"].get(channel, 0.0) + weight
            if len(ordered) == 1:
                models["position_based"][ordered[0]] = models["position_based"].get(ordered[0], 0.0) + 1.0
            elif len(ordered) == 2:
                for channel in ordered:
                    models["position_based"][channel] = models["position_based"].get(channel, 0.0) + 0.5
            else:
                models["position_based"][ordered[0]] = models["position_based"].get(ordered[0], 0.0) + 0.4
                models["position_based"][ordered[-1]] = models["position_based"].get(ordered[-1], 0.0) + 0.4
                middle = 0.2 / (len(ordered) - 2)
                for channel in ordered[1:-1]:
                    models["position_based"][channel] = models["position_based"].get(channel, 0.0) + middle

        n_users = float(len(converting))
        rounded = {
            name: {channel: round(value / n_users, 4) for channel, value in sorted(values.items())}
            for name, values in models.items()
        }
        return {
            "status": "SUCCESS",
            "converting_users": len(converting),
            "models": rounded,
            "notes": [
                "Shares are per converting user, deduplicated consecutive channels.",
                "Position-based uses 40/20/40 for three or more touchpoints.",
            ],
        }

    @staticmethod
    def calculate_unit_economics(
        cac: float, arpu: float, gross_margin: float, monthly_churn: float
    ) -> Dict[str, Any]:
        """LTV = (ARPU * gross margin) / monthly churn."""
        if monthly_churn <= 0 or monthly_churn > 1:
            return {"status": "ERROR", "error": "Monthly churn rate must be in the open interval (0, 1]."}
        if arpu < 0 or gross_margin < 0 or gross_margin > 1:
            return {"status": "ERROR", "error": "ARPU must be non-negative and gross margin in [0, 1]."}

        ltv = (arpu * gross_margin) / monthly_churn
        ltv_cac = ltv / cac if cac > 0 else None
        payback = cac / (arpu * gross_margin) if (arpu * gross_margin) > 0 else None

        warnings: List[str] = []
        if cac <= 0:
            warnings.append("CAC is not positive; the LTV:CAC ratio is undefined.")
        if payback is None:
            warnings.append("Payback is undefined because contribution margin per month is zero.")

        return {
            "cac": round(cac, 2),
            "ltv": round(ltv, 2),
            "ltv_cac_ratio": round(ltv_cac, 2) if ltv_cac is not None else None,
            "payback_months": round(payback, 1) if payback is not None else None,
            "healthy_benchmark": bool(
                ltv_cac is not None and payback is not None and ltv_cac >= 3.0 and payback <= 12.0
            ),
            "assumptions": [
                "LTV uses a constant monthly churn rate (no cohort curve).",
                "Gross margin is applied to ARPU, not to revenue net of discounts.",
            ],
            "warnings": warnings,
        }
