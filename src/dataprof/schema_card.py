"""Schema card: a deterministic profile injected before the model plans.

Without this, the planner burns tool rounds discovering column names by trial
and error, and guesses at dtypes. The card is bounded in size and contains no
row-level payload, so it is safe to put in a system prompt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

import pandas as pd

MAX_COLUMNS = 60
MAX_TOP_VALUES = 3
MAX_CELL_CHARS = 40


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    dtype: str
    role: str
    null_rate: float
    distinct: int
    minimum: Optional[str] = None
    maximum: Optional[str] = None
    mean: Optional[float] = None
    top_values: Tuple[str, ...] = ()

    def render(self) -> str:
        parts = [f"- {self.name} [{self.role}, {self.dtype}]"]
        if self.top_values:
            parts.append(f"{self.distinct} distinct; top " + ", ".join(self.top_values))
        elif self.role in ("measure", "temporal"):
            parts.append(f"{self.distinct} distinct")
        if self.minimum is not None or self.maximum is not None:
            parts.append(f"range {self.minimum}..{self.maximum}")
        if self.mean is not None:
            parts.append(f"mean {self.mean:g}")
        parts.append(f"{self.null_rate * 100:.0f}% null")
        return "; ".join(parts)


@dataclass(frozen=True)
class SchemaCard:
    row_count: int
    column_count: int
    columns: Tuple[ColumnProfile, ...]
    truncated: bool = False

    def render(self, max_chars: int = 2000) -> str:
        header = f"Dataset profile: {self.row_count} rows x {self.column_count} columns"
        lines = [header]
        for column in self.columns:
            line = column.render()
            if len("\n".join(lines + [line])) > max_chars:
                lines.append("- (profile truncated; query the remaining columns explicitly)")
                break
            lines.append(line)
        return "\n".join(lines)


def _safe_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    return text[:MAX_CELL_CHARS] + ("…" if len(text) > MAX_CELL_CHARS else "")


def _role(series: pd.Series, distinct: int, rows: int) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "temporal"
    if pd.api.types.is_bool_dtype(series):
        return "dimension"
    if pd.api.types.is_numeric_dtype(series):
        return "measure"
    sample = series.dropna().astype(str).head(200)
    if not sample.empty:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().mean() >= 0.8:
            return "temporal"
    if rows >= 20 and distinct >= rows * 0.95:
        return "identifier"
    return "dimension"


def build_schema_card(
    df: pd.DataFrame,
    max_columns: int = MAX_COLUMNS,
    max_top_values: int = MAX_TOP_VALUES,
) -> SchemaCard:
    """Profile a frame deterministically (no sampling, no randomness)."""
    rows = int(len(df))
    columns: List[ColumnProfile] = []

    for name in list(df.columns)[:max_columns]:
        series = df[name]
        distinct = int(series.nunique(dropna=True))
        null_rate = float(series.isna().mean()) if rows else 0.0
        dtype = str(series.dtype)
        role = _role(series, distinct, rows)

        minimum = maximum = None
        mean = None
        top_values: Tuple[str, ...] = ()

        if role == "measure":
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                minimum = f"{numeric.min():g}"
                maximum = f"{numeric.max():g}"
                mean = float(numeric.mean())
        elif role == "temporal":
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            if parsed.notna().any():
                minimum = str(parsed.min())[:19]
                maximum = str(parsed.max())[:19]
        elif role == "dimension" and distinct and distinct <= max(50, rows):
            counts = series.dropna().astype(str).value_counts().head(max_top_values)
            top_values = tuple(f"{_safe_cell(v)} ({int(c)})" for v, c in counts.items())

        columns.append(
            ColumnProfile(
                name=str(name),
                dtype=dtype,
                role=role,
                null_rate=round(null_rate, 4),
                distinct=distinct,
                minimum=minimum,
                maximum=maximum,
                mean=mean,
                top_values=top_values,
            )
        )

    return SchemaCard(
        row_count=rows,
        column_count=int(len(df.columns)),
        columns=tuple(columns),
        truncated=len(df.columns) > max_columns,
    )


def card_summary(card: SchemaCard) -> dict:
    """Compact, JSON-safe summary for API responses."""
    return {
        "row_count": card.row_count,
        "column_count": card.column_count,
        "truncated": card.truncated,
        "columns": [
            {
                "name": c.name,
                "dtype": c.dtype,
                "role": c.role,
                "null_rate": c.null_rate,
                "distinct": c.distinct,
            }
            for c in card.columns
        ],
    }


def numeric_columns(card: SchemaCard) -> List[str]:
    return [c.name for c in card.columns if c.role == "measure" and math.isfinite(c.null_rate)]


def temporal_columns(card: SchemaCard) -> List[str]:
    return [c.name for c in card.columns if c.role == "temporal"]


def render_columns(columns: Iterable[str]) -> str:
    return ", ".join(f'"{c}"' for c in columns)
