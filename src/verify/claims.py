"""Deterministic verification of numbers in the narrative.

The last mile of an analysis is prose. This module checks every analytically
meaningful number in that prose against numbers a tool actually produced. It
does not rewrite the text and it does not call a model; it returns evidence so
the caller can flag or block an unsupported claim.
"""

from __future__ import annotations

import bisect
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

DEFAULT_TOLERANCE = 0.005  # 0.5% relative
_YEAR_MIN, _YEAR_MAX = 1900, 2100
_CONTEXT_CHARS = 48

# Number, optional thousands separators, optional decimals, optional magnitude
# suffix or percent sign. A leading word character is excluded so identifiers
# such as "K3" or "v1" are not treated as claims.
_NUMBER_RE = re.compile(
    r"(?<![\w.])"
    r"(?P<sign>[-+])?"
    r"(?P<body>\d{1,3}(?:,\d{3})+|\d+)"
    r"(?P<frac>\.\d+)?"
    r"\s*(?P<suffix>%|percent|pp|[kKmMbB](?:n|illion)?)?",
)
_MAGNITUDE = {"k": 1e3, "m": 1e6, "b": 1e9}


@dataclass(frozen=True)
class NumericClaim:
    raw: str
    value: float
    is_percent: bool
    start: int
    end: int
    decimals: int

    @property
    def severity(self) -> str:
        if self.is_percent:
            return "critical"
        if abs(self.value) >= 1000:
            return "critical"
        if self.decimals and abs(self.value) >= 10:
            return "critical"
        return "info"


def _parse_number(match: re.Match) -> Optional[NumericClaim]:
    body = match.group("body").replace(",", "")
    frac = match.group("frac") or ""
    suffix = (match.group("suffix") or "").lower()
    try:
        value = float(body + frac)
    except ValueError:
        return None
    if match.group("sign") == "-":
        value = -value
    if suffix in _MAGNITUDE:
        value *= _MAGNITUDE[suffix]
    is_percent = suffix in ("%", "percent", "pp")
    decimals = len(frac) - 1 if frac else 0
    return NumericClaim(
        raw=match.group(0).strip(),
        value=value,
        is_percent=is_percent,
        start=match.start(),
        end=match.end(),
        decimals=max(decimals, 0),
    )


def extract_numbers(text: str) -> List[NumericClaim]:
    if not isinstance(text, str) or not text:
        return []
    claims: List[NumericClaim] = []
    for match in _NUMBER_RE.finditer(text):
        claim = _parse_number(match)
        if claim is not None:
            claims.append(claim)
    return claims


def _is_supported(claim: NumericClaim, facts: Sequence[float], tolerance: float) -> bool:
    candidates = [claim.value / 100.0] if claim.is_percent else [claim.value]
    for candidate in candidates:
        target = abs(candidate)
        matched = _find(facts, candidate, tolerance)
        if matched:
            return True
        # Rounding in prose is legitimate; accept the same value at the
        # claim's stated precision.
        rounded = round(candidate, claim.decimals)
        if abs(rounded - candidate) > 1e-12 and _find(facts, rounded, tolerance):
            return True
        if claim.decimals == 0 and abs(candidate - round(candidate)) < 1e-9:
            if _find(facts, float(round(candidate)), tolerance):
                return True
        if target and _find(facts, -candidate, tolerance):
            return True
    return False


def _find(sorted_facts: Sequence[float], value: float, tolerance: float) -> bool:
    magnitude = abs(value)
    window = max(1e-9, tolerance * magnitude, 0.5 if magnitude < 100 else 1e-9)
    index = bisect.bisect_left(sorted_facts, value - window)
    while index < len(sorted_facts) and sorted_facts[index] <= value + window:
        fact = sorted_facts[index]
        if abs(fact - value) <= max(window, tolerance * max(abs(fact), 1e-12)):
            return True
        index += 1
    return False


def _context(text: str, start: int, end: int) -> str:
    left = max(0, start - _CONTEXT_CHARS)
    right = min(len(text), end + _CONTEXT_CHARS)
    snippet = text[left:right].replace("\n", " ").strip()
    return ("…" if left else "") + snippet + ("…" if right < len(text) else "")


def collect_facts(payload: Any, limit: int = 5000) -> List[float]:
    """Collect numeric leaves from tool output (deterministic, depth-first)."""
    facts: List[float] = []

    def visit(node: Any) -> None:
        if len(facts) >= limit:
            return
        if isinstance(node, bool) or node is None:
            return
        if isinstance(node, (int, float)):
            value = float(node)
            if math.isfinite(value):
                facts.append(value)
            return
        if isinstance(node, dict):
            for key in node:
                visit(node[key])
            return
        if isinstance(node, (list, tuple)):
            for item in node[:limit]:
                visit(item)

    visit(payload)
    return facts


def verify_claims(
    narrative: str,
    facts: Iterable[float],
    tolerance: float = DEFAULT_TOLERANCE,
) -> Dict[str, Any]:
    """
    Compare every number in ``narrative`` with ``facts``.

    Returns ``status=PASS`` only when every critical claim is supported. When
    there are no numbers at all the status is ``NO_CLAIMS`` (not a pass: a
    narrative without numbers is usually a summary of a failure).
    """
    claims = extract_numbers(narrative)
    clean_facts = sorted(
        float(f) for f in facts if isinstance(f, (int, float)) and math.isfinite(float(f))
    )

    supported = 0
    unsupported: List[Dict[str, Any]] = []
    ignored = 0

    for claim in claims:
        if (
            claim.decimals == 0
            and not claim.is_percent
            and _YEAR_MIN <= claim.value <= _YEAR_MAX
            and not _find(clean_facts, claim.value, tolerance)
        ):
            ignored += 1
            continue
        if _is_supported(claim, clean_facts, tolerance):
            supported += 1
            continue
        unsupported.append(
            {
                "value": claim.value,
                "raw": claim.raw,
                "severity": claim.severity,
                "context": _context(narrative, claim.start, claim.end),
            }
        )

    critical = [u for u in unsupported if u["severity"] == "critical"]
    if not claims:
        status = "NO_CLAIMS"
    elif critical:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "status": status,
        "checked": len(claims) - ignored,
        "supported": supported,
        "unsupported": unsupported[:25],
        "unsupported_count": len(unsupported),
        "ignored_years": ignored,
        "facts_considered": len(clean_facts),
        "tolerance": tolerance,
    }
