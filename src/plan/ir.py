"""Typed analysis plan (Analyst IR).

The planner is allowed to be creative; the plan is not. Every plan is a small,
strictly validated object so it can be hashed, replayed, diffed and compiled
without the model being involved again.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

INTENTS = ("aggregate", "trend")
GRAINS = ("day", "week", "month", "quarter", "year")
ORDERINGS = ("asc", "desc")
FILTER_OPS = ("=", "!=", ">", ">=", "<", "<=", "in", "not_in", "is_null", "not_null")

# Accepting unknown keys would let a planner smuggle unchecked semantics into a
# hash, so the schema is closed on purpose.
_PLAN_KEYS = {
    "version",
    "intent",
    "metrics",
    "group_by",
    "filters",
    "time_column",
    "grain",
    "limit",
    "order",
    "method",
    "acceptance",
}
_FILTER_KEYS = {"column", "op", "value"}


class PlanError(ValueError):
    """Raised when a plan is malformed or cannot be compiled."""


@dataclass(frozen=True)
class PlanFilter:
    column: str
    op: str
    value: Any = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PlanFilter":
        if not isinstance(raw, dict):
            raise PlanError("Each filter must be an object.")
        unknown = set(raw) - _FILTER_KEYS
        if unknown:
            raise PlanError(f"Unknown filter keys: {', '.join(sorted(unknown))}")
        column = str(raw.get("column") or "").strip()
        op = str(raw.get("op") or "").strip().lower()
        if not column:
            raise PlanError("Each filter needs a column.")
        if op not in FILTER_OPS:
            raise PlanError(f"Unsupported filter operator: {op}")
        value = raw.get("value")
        if op in ("in", "not_in") and not isinstance(value, (list, tuple)):
            raise PlanError(f"Filter operator {op} needs a list value.")
        if op not in ("in", "not_in", "is_null", "not_null") and value is None:
            raise PlanError(f"Filter operator {op} needs a value.")
        return cls(column=column, op=op, value=value)

    def to_dict(self) -> Dict[str, Any]:
        return {"column": self.column, "op": self.op, "value": self.value}


@dataclass(frozen=True)
class AnalysisPlan:
    intent: str
    metrics: Tuple[str, ...]
    group_by: Tuple[str, ...] = ()
    filters: Tuple[PlanFilter, ...] = ()
    time_column: Optional[str] = None
    grain: Optional[str] = None
    limit: int = 100
    order: str = "desc"
    method: Optional[str] = None
    acceptance: Tuple[str, ...] = ()
    version: int = 1

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "AnalysisPlan":
        if not isinstance(raw, dict):
            raise PlanError("The plan must be an object.")
        unknown = set(raw) - _PLAN_KEYS
        if unknown:
            raise PlanError(f"Unknown plan keys: {', '.join(sorted(unknown))}")

        intent = str(raw.get("intent") or "").strip().lower()
        if intent not in INTENTS:
            raise PlanError(f"intent must be one of: {', '.join(INTENTS)}")

        metrics = raw.get("metrics")
        if isinstance(metrics, str):
            metrics = [metrics]
        if not isinstance(metrics, (list, tuple)) or not metrics:
            raise PlanError("metrics must be a non-empty list.")
        metric_names = tuple(str(m).strip() for m in metrics if str(m).strip())
        if len(metric_names) != 1:
            raise PlanError("Plan version 1 supports exactly one metric per plan.")

        group_by = raw.get("group_by") or []
        if not isinstance(group_by, (list, tuple)):
            raise PlanError("group_by must be a list of column names.")
        group = tuple(str(c).strip() for c in group_by if str(c).strip())
        if len(group) != len(set(group)):
            raise PlanError("group_by contains duplicate columns.")

        filters_raw = raw.get("filters") or []
        if not isinstance(filters_raw, (list, tuple)):
            raise PlanError("filters must be a list.")
        filters = tuple(PlanFilter.from_dict(item) for item in filters_raw)

        grain = raw.get("grain")
        grain = str(grain).lower() if grain else None
        if intent == "trend":
            if not grain or grain not in GRAINS:
                raise PlanError(f"trend plans need grain in: {', '.join(GRAINS)}")
            if not str(raw.get("time_column") or "").strip():
                raise PlanError("trend plans need a time_column.")
        elif grain and grain not in GRAINS:
            raise PlanError(f"Unsupported grain: {grain}")

        order = str(raw.get("order") or "desc").lower()
        if order not in ORDERINGS:
            raise PlanError("order must be 'asc' or 'desc'.")

        try:
            limit = int(raw.get("limit", 100))
        except (TypeError, ValueError) as exc:
            raise PlanError("limit must be an integer.") from exc
        if not 1 <= limit <= 1000:
            raise PlanError("limit must be between 1 and 1000.")

        acceptance = raw.get("acceptance") or []
        if not isinstance(acceptance, (list, tuple)):
            raise PlanError("acceptance must be a list of check names.")

        return cls(
            intent=intent,
            metrics=metric_names,
            group_by=group,
            filters=filters,
            time_column=str(raw.get("time_column")).strip() if raw.get("time_column") else None,
            grain=grain,
            limit=limit,
            order=order,
            method=str(raw.get("method")).strip() if raw.get("method") else None,
            acceptance=tuple(str(a).strip() for a in acceptance if str(a).strip()),
            version=int(raw.get("version", 1)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "intent": self.intent,
            "metrics": list(self.metrics),
            "group_by": list(self.group_by),
            "filters": [f.to_dict() for f in self.filters],
            "time_column": self.time_column,
            "grain": self.grain,
            "limit": self.limit,
            "order": self.order,
            "method": self.method,
            "acceptance": list(self.acceptance),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=str)

    def plan_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def parse_plan(payload: Any) -> AnalysisPlan:
    """Parse a plan from a dict or a JSON string."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PlanError("The plan is not valid JSON.") from exc
    return AnalysisPlan.from_dict(payload)


def plan_schema() -> Dict[str, Any]:
    """JSON Schema handed to planners that support structured output."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["intent", "metrics"],
        "properties": {
            "version": {"type": "integer", "enum": [1]},
            "intent": {"type": "string", "enum": list(INTENTS)},
            "metrics": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": {"type": "string"},
            },
            "group_by": {"type": "array", "items": {"type": "string"}},
            "filters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["column", "op"],
                    "properties": {
                        "column": {"type": "string"},
                        "op": {"type": "string", "enum": list(FILTER_OPS)},
                        "value": {},
                    },
                },
            },
            "time_column": {"type": ["string", "null"]},
            "grain": {"type": ["string", "null"], "enum": list(GRAINS) + [None]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
            "order": {"type": "string", "enum": list(ORDERINGS)},
            "method": {"type": ["string", "null"]},
            "acceptance": {"type": "array", "items": {"type": "string"}},
        },
    }


def plans_equal(left: AnalysisPlan, right: AnalysisPlan) -> bool:
    return left.canonical_json() == right.canonical_json()


def plan_metrics(plan: AnalysisPlan) -> Sequence[str]:
    return plan.metrics


def empty_plan(intent: str = "aggregate", metric: str = "revenue") -> AnalysisPlan:
    return AnalysisPlan(intent=intent, metrics=(metric,))


def plan_to_list(plan: AnalysisPlan) -> List[str]:
    """Human-readable plan, used in traces."""
    parts = [f"{plan.intent} {plan.metrics[0]}"]
    if plan.group_by:
        parts.append("by " + ", ".join(plan.group_by))
    if plan.time_column:
        parts.append(f"over {plan.grain}({plan.time_column})")
    if plan.filters:
        parts.append("where " + " and ".join(f"{f.column} {f.op}" for f in plan.filters))
    return parts
