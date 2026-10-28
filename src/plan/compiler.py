"""Compile a typed plan into one read-only SQL statement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from semantic.catalog import BoundMetric, quote_identifier
from semantic.query import MetricFilter, MetricQueryError, filter_sql

from .ir import AnalysisPlan, PlanError

_GRAIN_TRUNC = {
    "day": "day",
    "week": "week",
    "month": "month",
    "quarter": "quarter",
    "year": "year",
}


@dataclass(frozen=True)
class CompiledPlan:
    sql: str
    intent: str
    metric: str
    group_by: tuple
    plan_hash: str
    notes: tuple = ()


def compile_plan(
    plan: AnalysisPlan,
    metrics: Dict[str, BoundMetric],
    columns: Sequence[str],
) -> CompiledPlan:
    """
    Deterministically compile an :class:`AnalysisPlan`.

    Raises :class:`PlanError` with an actionable message when the plan refers
    to an unknown metric or column, so the planner can repair it instead of the
    executor producing NULLs.
    """
    known = [str(c) for c in columns]
    metric_name = plan.metrics[0]
    metric: BoundMetric | None = metrics.get(metric_name)
    if metric is None:
        available = ", ".join(sorted(metrics)) or "(none for this dataset)"
        raise PlanError(f"Metric '{metric_name}' is not defined for this dataset. Available: {available}")

    for column in plan.group_by:
        if column not in known:
            raise PlanError(f"Unknown group_by column: {column}")
    if plan.time_column and plan.time_column not in known:
        raise PlanError(f"Unknown time column: {plan.time_column}")

    conflict = set(plan.group_by) | ({plan.time_column} if plan.time_column else set())
    if metric.name in conflict:
        raise PlanError("The metric name collides with a grouping column; rename the grouping column.")

    select: List[str] = []
    group_exprs: List[str] = []
    order_expr = quote_identifier(metric.name)
    direction = "ASC" if plan.order == "asc" else "DESC"

    if plan.intent == "trend":
        trunc = _GRAIN_TRUNC[plan.grain or "month"]
        period = (
            f"date_trunc('{trunc}', TRY_CAST({quote_identifier(plan.time_column or '')} AS TIMESTAMP))"
        )
        select.append(f"{period} AS {quote_identifier('period')}")
        group_exprs.append(period)
        order_expr = quote_identifier("period")
        direction = "ASC"

    for column in plan.group_by:
        select.append(quote_identifier(column))
        group_exprs.append(quote_identifier(column))

    select.append(f"{metric.sql} AS {quote_identifier(metric.name)}")

    try:
        where = filter_sql(
            [MetricFilter(f.column, f.op, f.value) for f in plan.filters], known
        )
    except MetricQueryError as exc:
        raise PlanError(str(exc)) from exc

    # Identifiers are validated against the dataset schema and quoted; literals are
    # escaped by filter_sql. The SQL then passes the sandbox allow-list before it runs.
    sql = "SELECT " + ", ".join(select) + " FROM dataset"  # noqa: S608
    if where:
        sql += " WHERE " + where
    if group_exprs:
        sql += " GROUP BY " + ", ".join(group_exprs)
    sql += f" ORDER BY {order_expr} {direction}"
    sql += f" LIMIT {plan.limit}"

    notes = (f"metric {metric.name} v{metric.version}",)
    return CompiledPlan(
        sql=sql,
        intent=plan.intent,
        metric=metric.name,
        group_by=tuple(plan.group_by),
        plan_hash=plan.plan_hash(),
        notes=notes,
    )
