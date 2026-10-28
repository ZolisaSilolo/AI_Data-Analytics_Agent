"""
Declarative Visualization Engine.
Produces Plotly JSON and Vega-Lite specifications for interactive rendering,
with optional headless image export for static S3 reports.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class VisualizationGenerator:
    """Modern declarative visual grammar for multi-discipline data analysis."""

    MAX_CHART_ROWS = 5000

    @staticmethod
    def generate_chart(
        df: pd.DataFrame,
        chart_type: str = "histogram",
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        color_column: Optional[str] = None,
        title: Optional[str] = None
    ) -> go.Figure:
        """
        Generate a declarative Plotly figure based on data distribution and chart type.
        """
        if df is None or df.empty:
            raise ValueError("Cannot chart an empty result set.")

        df = df.head(VisualizationGenerator.MAX_CHART_ROWS)
        cols = list(df.columns)
        if not cols:
            raise ValueError("Cannot chart a result set with no columns.")

        for label, column in (("x", x_column), ("y", y_column), ("color", color_column)):
            if column is not None and column not in cols:
                raise ValueError(
                    f"Chart {label} column '{column}' is not in the result columns: "
                    + ", ".join(map(str, cols))
                )

        if not x_column and cols:
            x_column = cols[0]
        if not y_column and len(cols) > 1 and chart_type not in ("histogram", "funnel"):
            y_column = cols[1]

        chart_title = title or f"{chart_type.capitalize()}: {x_column}" + (f" vs {y_column}" if y_column else "")

        if chart_type == "histogram":
            fig = px.histogram(
                df, x=x_column, color=color_column,
                title=chart_title, marginal="box",
                template="plotly_white"
            )
        elif chart_type == "bar":
            fig = px.bar(
                df, x=x_column, y=y_column, color=color_column,
                title=chart_title, template="plotly_white"
            )
        elif chart_type == "scatter":
            fig = px.scatter(
                df, x=x_column, y=y_column, color=color_column,
                trendline="ols" if len(df) > 10 else None,
                title=chart_title, template="plotly_white"
            )
        elif chart_type == "line":
            fig = px.line(
                df, x=x_column, y=y_column, color=color_column,
                markers=True, title=chart_title, template="plotly_white"
            )
        elif chart_type == "box":
            fig = px.box(
                df, x=x_column, y=y_column, color=color_column,
                points="outliers", title=chart_title, template="plotly_white"
            )
        elif chart_type == "correlation_matrix":
            numeric_df = df.select_dtypes(include=["number"])
            if numeric_df.empty:
                raise ValueError("No numeric columns available for correlation matrix.")
            corr = numeric_df.corr().round(3)
            fig = px.imshow(
                corr, text_auto=True, aspect="auto",
                color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                title="Correlation Matrix", template="plotly_white"
            )
        elif chart_type == "waterfall":
            # Waterfall for Financial ARR / variance analysis
            fig = go.Figure(go.Waterfall(
                name="Variance", orientation="v",
                measure=df.get("measure", ["relative"] * len(df)),
                x=df[x_column],
                y=df[y_column],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            ))
            fig.update_layout(title=chart_title, template="plotly_white")
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        return fig

    @classmethod
    def export_figure_bytes(cls, fig: go.Figure, format: str = "png") -> bytes:
        """Export Plotly figure to static image bytes."""
        return fig.to_image(format=format)

    @classmethod
    def export_figure_json(cls, fig: go.Figure) -> Dict[str, Any]:
        """Export Plotly figure to declarative JSON for frontend/extension rendering."""
        return json.loads(fig.to_json())
