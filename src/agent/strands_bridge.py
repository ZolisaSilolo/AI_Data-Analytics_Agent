"""
AWS Strands Agent SDK Bridge.
Connects with local Strands decider and intervention handlers if present,
enabling calibrated risk evaluation and policy interception before tool calls.
"""

from __future__ import annotations
import logging
import os
import urllib.request
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StrandsPolicyBridge:
    """Intervention and decider bridge compatible with AWS Strands Agent SDK."""

    def __init__(self, decider_url: Optional[str] = None):
        self.decider_url = decider_url or os.environ.get("STRANDS_DECIDER_URL", "http://127.0.0.1:8765")

    def is_decider_available(self) -> bool:
        """Check if local Strands calibrated decider is running."""
        try:
            with urllib.request.urlopen(f"{self.decider_url}/health", timeout=0.3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def evaluate_risk(self, command_or_sql: str) -> Dict[str, Any]:
        """
        Evaluate if proposed execution contains destructive commands
        (e.g., DROP TABLE, TRUNCATE, DELETE, or OS compromise).
        """
        # Static baseline heuristic check
        lowered = command_or_sql.lower()
        blocked_keywords = ["drop table", "truncate", "rm -rf", "format", "delete from"]
        for kw in blocked_keywords:
            if kw in lowered:
                return {
                    "level": "block",
                    "reason": f"Detected destructive statement: '{kw}'"
                }

        # If decider is available, evaluate with calibrated model
        if self.is_decider_available():
            try:
                body = json.dumps({
                    "state": command_or_sql,
                    "questions": {
                        "risk": {
                            "type": "choice",
                            "instructions": "Is this data operation destructive or irreversible?",
                            "criteria": {"safe": "read-only or non-destructive", "destructive": "deletes data"}
                        }
                    }
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.decider_url}/v1/systemone",
                    data=body,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    p_dest = payload.get("answers", {}).get("risk", {}).get("probabilities", {}).get("destructive", 0.0)
                    if p_dest > 0.85:
                        return {"level": "block", "reason": f"Strands decider flagged destructive risk (p={p_dest:.2f})"}
            except Exception as e:
                logger.debug(f"Strands decider call skipped: {e}")

        return {"level": "ok", "reason": "Passed safety heuristics."}
