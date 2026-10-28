"""
Versioned metric catalogue — the logical-determinism layer (L1).

A metric is defined once, in version control, and compiled to SQL by this
module. The model may *choose* a metric and its grouping, but it never chooses
the formula. When a required column is missing the metric becomes unavailable
rather than being silently re-derived by the model.

Definitions live in ``catalog.json`` next to this module:

* ``sql`` metrics substitute ``{canonical_column}`` placeholders.
* ``formula`` metrics reference other metric names (resolved recursively).

Both are validated at load time, so a malformed catalogue fails at import
instead of producing a wrong number at runtime.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).with_name("catalog.json")
_ALLOWED_UNITS = {"currency", "count", "ratio", "duration_hours", "score"}
_METRIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class CatalogError(ValueError):
    """Raised when a metric definition is malformed or unsatisfiable."""


def _norm(name: Any) -> str:
    """Fold a column name to a comparison key (case/punctuation insensitive)."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def quote_identifier(name: str) -> str:
    """Quote a column identifier for DuckDB without allowing injection."""
    return '"' + str(name).replace('"', '""') + '"'


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    version: int
    unit: str
    description: str
    requires: Tuple[str, ...] = ()
    sql: Optional[str] = None
    formula: Optional[str] = None
    aliases: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "MetricDefinition":
        name = str(raw.get("name") or "")
        if not _METRIC_NAME_RE.match(name):
            raise CatalogError(f"Invalid metric name: {name!r}")
        unit = str(raw.get("unit") or "")
        if unit not in _ALLOWED_UNITS:
            raise CatalogError(f"Metric {name!r} has unsupported unit {unit!r}")

        sql = raw.get("sql")
        formula = raw.get("formula")
        if bool(sql) == bool(formula):
            raise CatalogError(f"Metric {name!r} needs exactly one of 'sql' or 'formula'")

        aliases_raw = raw.get("aliases") or {}
        aliases = {
            _norm(canonical): tuple(_norm(a) for a in (values or []))
            for canonical, values in aliases_raw.items()
        }
        return cls(
            name=name,
            version=int(raw.get("version", 1)),
            unit=unit,
            description=str(raw.get("description") or "").strip(),
            requires=tuple(_norm(c) for c in (raw.get("requires") or [])),
            sql=str(sql) if sql else None,
            formula=str(formula) if formula else None,
            aliases=aliases,
        )

    @property
    def display_sql(self) -> str:
        return str(self.sql or self.formula or "")


@dataclass(frozen=True)
class BoundMetric:
    """A metric resolved against the actual columns of one dataset."""

    name: str
    version: int
    unit: str
    description: str
    sql: str
    columns: Tuple[str, ...]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.name}@{self.version} = {self.sql}"


class MetricCatalog:
    """A validated, versioned set of metric definitions."""

    def __init__(self, version: int, metrics: Iterable[MetricDefinition]) -> None:
        self.version = version
        self.metrics: Dict[str, MetricDefinition] = {m.name: m for m in metrics}
        self._validate()

    def _validate(self) -> None:
        for metric in self.metrics.values():
            if metric.formula:
                for ref in re.findall(r"[a-z][a-z0-9_]{1,63}", metric.formula):
                    if ref not in self.metrics:
                        raise CatalogError(
                            f"Metric {metric.name!r} references unknown metric {ref!r}"
                        )

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "MetricCatalog":
        metrics = raw.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            raise CatalogError("Metric catalogue must contain a non-empty 'metrics' list")
        return cls(
            version=int(raw.get("version", 1)),
            metrics=[MetricDefinition.from_dict(m) for m in metrics],
        )

    def bind(self, columns: Iterable[Any]) -> Dict[str, BoundMetric]:
        """
        Resolve every metric against ``columns``.

        Unavailable metrics are omitted (the caller reports them) instead of
        being guessed. Ambiguity is an omission too: two candidate columns for
        one metric is a data-quality signal, not a coin flip.
        """
        actual = [str(c) for c in columns]
        index: Dict[str, List[str]] = {}
        for column in actual:
            index.setdefault(_norm(column), []).append(column)

        resolved_columns: Dict[str, Optional[str]] = {}
        bound: Dict[str, BoundMetric] = {}
        pending = dict(self.metrics)

        for _ in range(len(pending) + 1):
            progressed = False
            for name in list(pending):
                metric = pending[name]
                if metric.formula:
                    deps = re.findall(r"[a-z][a-z0-9_]{1,63}", metric.formula)
                    if any(dep not in bound for dep in deps):
                        continue
                    sql = metric.formula
                    for dep in sorted(deps, key=len, reverse=True):
                        sql = re.sub(
                            rf"\b{re.escape(dep)}\b", f"({bound[dep].sql})", sql
                        )
                    used: List[str] = []
                    for dep in deps:
                        used.extend(bound[dep].columns)
                    bound[name] = BoundMetric(
                        name=metric.name,
                        version=metric.version,
                        unit=metric.unit,
                        description=metric.description,
                        sql=sql,
                        columns=tuple(dict.fromkeys(used)),
                    )
                    del pending[name]
                    progressed = True
                    continue

                mapping: Dict[str, str] = {}
                failed = None
                for canonical in metric.requires:
                    if canonical in resolved_columns:
                        mapping[canonical] = resolved_columns[canonical] or ""
                        if not resolved_columns[canonical]:
                            failed = canonical
                            break
                        continue
                    candidates = index.get(canonical, [])
                    if not candidates:
                        for alias in metric.aliases.get(canonical, ()):
                            candidates.extend(index.get(alias, []))
                    candidates = list(dict.fromkeys(candidates))
                    if len(candidates) == 1:
                        resolved_columns[canonical] = candidates[0]
                        mapping[canonical] = candidates[0]
                    elif len(candidates) > 1:
                        logger.info(
                            "Metric %s unavailable: column %s is ambiguous (%s)",
                            name, canonical, ", ".join(candidates),
                        )
                        failed = canonical
                        break
                    else:
                        failed = canonical
                        break
                if failed:
                    continue

                sql = str(metric.sql or "")
                for canonical, column in mapping.items():
                    sql = sql.replace("{" + canonical + "}", quote_identifier(column))
                bound[name] = BoundMetric(
                    name=metric.name,
                    version=metric.version,
                    unit=metric.unit,
                    description=metric.description,
                    sql=sql,
                    columns=tuple(dict.fromkeys(mapping.values())),
                )
                del pending[name]
                progressed = True
            if not progressed:
                break

        if pending:
            logger.info(
                "Metrics unavailable for this dataset: %s", ", ".join(sorted(pending))
            )
        return bound

    def render_prompt(self, bound: Dict[str, BoundMetric], max_chars: int = 1800) -> str:
        """
        Render the *bound* catalogue for the system prompt.

        Deterministic and token-bounded: sorted by name, trimmed at
        ``max_chars`` so a wide catalogue cannot crowd out the schema card.
        """
        lines = [
            f"METRIC CATALOG v{self.version} — call query_metric for these; "
            "never re-derive their formulas:"
        ]
        for name in sorted(bound):
            metric = bound[name]
            line = f"- {metric.name} v{metric.version} [{metric.unit}]: {metric.sql}"
            if len("\n".join(lines + [line])) > max_chars:
                lines.append("- (catalogue truncated; request one metric at a time)")
                break
            lines.append(line)
        return "\n".join(lines)


def load_catalog(path: Optional[Path] = None) -> MetricCatalog:
    """Load and validate the catalogue. Cached per process by the caller."""
    target = path or CATALOG_PATH
    with open(target, encoding="utf-8") as handle:
        return MetricCatalog.from_dict(json.load(handle))
