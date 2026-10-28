"""Real Bedrock + real DuckDB smoke test (no mocks). Not part of the unit suite."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("BEDROCK_PRIMARY_MODEL", "global.moonshotai.kimi-k3")
os.environ.setdefault("AWS_REGION", "us-east-1")

from services.analysis import run_analysis  # noqa: E402

page_context = {
    "url": "https://example.test/sales",
    "pageTitle": "Regional sales",
    "tableCount": 1,
    "tables": [
        {
            "tableIndex": 1,
            "headers": ["region", "month", "revenue", "cost"],
            "rowCount": 6,
            "sampleRows": [
                ["EMEA", "2026-01", "1000", "400"],
                ["EMEA", "2026-02", "1500", "500"],
                ["APAC", "2026-01", "900", "300"],
                ["APAC", "2026-02", "1200", "450"],
                ["AMER", "2026-01", "2000", "900"],
                ["AMER", "2026-02", "2500", "1000"],
            ],
        }
    ],
}

result = run_analysis(
    {
        "query": "Which region has the highest total revenue? Return a table of region, total_revenue.",
        "page_context": page_context,
        "discipline": "general",
        "generate_chart": False,
    }
)

summary = {
    "status": result.get("status"),
    "analysis": result.get("analysis"),
    "model_used": result.get("model_used"),
    "usage": result.get("usage"),
    "rounds": result.get("rounds"),
    "tool_calls": [
        {"tool": t.get("tool"), "status": t.get("status")} for t in result.get("tool_executions", [])
    ],
    "row_count": (result.get("dataset") or {}).get("row_count"),
}
print(json.dumps(summary, indent=2, default=str))
