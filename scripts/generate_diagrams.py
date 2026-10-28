"""
OmniAnalyst Architecture Diagram Generator.

Regenerates every stakeholder diagram in three guaranteed-render formats:

* PNG (matplotlib raster) — for slides and documents.
* SVG (matplotlib vector, text as paths) — identical in every viewer.
* Mermaid (.md) — renders natively on GitHub and in modern editors.

It also writes ``generated-diagrams/index.html``, a zero-dependency viewer so a
local double-click shows every artifact. Content is kept in sync with the
codebase: 11 typed tools, semantic catalogue, schema card, claim verification,
90-day artifact retention.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated-diagrams"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    "bg": "#0b0f19",
    "surface": "#111827",
    "card": "#1e293b",
    "card_inner": "#0f172a",
    "border": "#334155",
    "border_subtle": "#1e293b",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "cyan": "#38bdf8",
    "indigo": "#818cf8",
    "purple": "#c084fc",
    "emerald": "#34d399",
    "amber": "#f59e0b",
    "rose": "#f43f5e",
}


def new_figure():
    fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def save(fig, stem):
    png_path = os.path.join(OUTPUT_DIR, f"{stem}.png")
    svg_path = os.path.join(OUTPUT_DIR, f"{stem}.svg")
    fig.savefig(png_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
    fig.savefig(svg_path, format="svg", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Generated: {png_path} and {svg_path}")


def draw_header(ax, title, subtitle, badges=None):
    header_box = FancyBboxPatch(
        (0.02, 0.90), 0.96, 0.08,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        fc=COLORS["card"], ec=COLORS["border"], lw=1.5, zorder=2,
    )
    ax.add_patch(header_box)
    ax.text(0.04, 0.95, title, fontsize=15, fontweight="bold",
            color=COLORS["text_primary"], va="center", zorder=3)
    ax.text(0.04, 0.92, subtitle, fontsize=9.5, color=COLORS["cyan"], va="center", zorder=3)

    if badges:
        bx = 0.96
        for text, border_col, bg_col, text_col in reversed(badges):
            b_width = len(text) * 0.0075 + 0.03
            bx -= b_width
            badge_patch = FancyBboxPatch(
                (bx, 0.925), b_width - 0.01, 0.032,
                boxstyle="round,pad=0.005,rounding_size=0.01",
                fc=bg_col, ec=border_col, lw=1.2, zorder=4,
            )
            ax.add_patch(badge_patch)
            ax.text(bx + (b_width - 0.01) / 2, 0.941, text, fontsize=7.5, fontweight="bold",
                    color=text_col, ha="center", va="center", zorder=5)
            bx -= 0.005


def draw_ribbon(ax, text, color):
    ribbon = FancyBboxPatch(
        (0.02, 0.015), 0.96, 0.035,
        boxstyle="round,pad=0.005,rounding_size=0.008",
        fc=COLORS["card"], ec=COLORS["border"], lw=1.0, zorder=2,
    )
    ax.add_patch(ribbon)
    ax.text(0.5, 0.032, text, fontsize=8.5, color=color, ha="center", va="center", zorder=3)


def create_overview_diagram():
    """Executive architecture overview (4 stages)."""
    fig, ax = new_figure()
    draw_header(
        ax,
        "OmniAnalyst — Executive Architecture Overview",
        "How Business Questions Become Deterministic, Evidence-Checked Answers",
        badges=[
            ("Evidence-Checked", COLORS["rose"], "#4c0519", "#fda4af"),
            ("$0 Idle Cost", COLORS["emerald"], "#064e3b", "#6ee7b7"),
            ("Graviton ARM64", COLORS["indigo"], "#1e1b4b", "#a5b4fc"),
        ],
    )

    cols = [
        {
            "num": "1", "title": "INGESTION & CLIENTS", "color": COLORS["cyan"],
            "sub": "Cross-Platform Access",
            "items": [
                ("React 18 SPA (AWS Amplify)", "Global CDN, dark-slate UI, Plotly charts"),
                ("Chrome/Edge Extension (MV3)", "One-click AG-Grid & DOM table extraction"),
                ("Presigned S3 Upload", "Size-capped, server-generated object keys"),
                ("Documents (PDF / images)", "Text layer first, lightweight OCR when scanned"),
            ],
        },
        {
            "num": "2", "title": "PLANNING & SEMANTICS", "color": COLORS["purple"],
            "sub": "Bounded Reasoning",
            "items": [
                ("Amazon Bedrock Converse", "Open-weight model profile (interim)"),
                ("Schema Card", "Column names, types, roles before planning"),
                ("Metric Catalogue", "Versioned formulas; query_metric tool"),
                ("Typed Plan (Analyst IR)", "Hashed, validated, replayable intent"),
            ],
        },
        {
            "num": "3", "title": "DETERMINISTIC SANDBOX", "color": COLORS["emerald"],
            "sub": "Engine-Computed Numbers",
            "items": [
                ("DuckDB In-Process Engine", "Vectorised OLAP, locked configuration"),
                ("SQL Allow-list Gate", "sqlglot AST blocks DDL, files, URLs"),
                ("Invariant Gates", "Bounds, reconciliation, null-rate checks"),
                ("Seeded Method Library", "Deterministic statistics, stated assumptions"),
            ],
        },
        {
            "num": "4", "title": "VERIFICATION & OUTPUT", "color": COLORS["amber"],
            "sub": "Evidence-Checked Delivery",
            "items": [
                ("Claim Verification", "Every narrative number ↔ tool output"),
                ("Execution Trace", "Exact SQL, tool calls, invariants per job"),
                ("Multi-Discipline Engines", "Finance, product, ops, growth, clinical"),
                ("Plotly Spec from Results", "Charts only from computed tables"),
            ],
        },
    ]

    col_width, gap, start_x = 0.225, 0.018, 0.02
    for i, col in enumerate(cols):
        cx = start_x + i * (col_width + gap)

        card = FancyBboxPatch(
            (cx, 0.06), col_width, 0.81,
            boxstyle="round,pad=0.012,rounding_size=0.012",
            fc=COLORS["surface"], ec=COLORS["border"], lw=1.2, zorder=2,
        )
        ax.add_patch(card)

        header_patch = FancyBboxPatch(
            (cx, 0.81), col_width, 0.06,
            boxstyle="round,pad=0.008,rounding_size=0.01",
            fc=COLORS["card"], ec=col["color"], lw=1.5, zorder=3,
        )
        ax.add_patch(header_patch)
        ax.text(cx + 0.015, 0.845, f"{col['num']}. {col['title']}", fontsize=10.5,
                fontweight="bold", color=col["color"], va="center", zorder=4)
        ax.text(cx + 0.015, 0.825, col["sub"], fontsize=7.5,
                color=COLORS["text_muted"], va="center", zorder=4)

        item_y = 0.74
        item_height = 0.145
        for title, desc in col["items"]:
            box_bottom = item_y - item_height + 0.02
            ibox = FancyBboxPatch(
                (cx + 0.01, box_bottom), col_width - 0.02, item_height - 0.02,
                boxstyle="round,pad=0.008,rounding_size=0.008",
                fc=COLORS["card"], ec=COLORS["border"], lw=1.0, zorder=3,
            )
            ax.add_patch(ibox)
            stripe = FancyBboxPatch(
                (cx + 0.012, box_bottom + 0.005), 0.004, item_height - 0.03,
                boxstyle="round,pad=0.001,rounding_size=0.002",
                fc=col["color"], ec="none", zorder=4,
            )
            ax.add_patch(stripe)
            centre = (item_y + box_bottom) / 2
            ax.text(cx + 0.022, centre + 0.018, title, fontsize=9, fontweight="bold",
                    color=COLORS["text_primary"], va="center", zorder=4)
            ax.text(cx + 0.022, centre - 0.004, desc, fontsize=7.2,
                    color=COLORS["text_secondary"], va="top", zorder=4, wrap=True)
            item_y -= item_height + 0.012

        if i < len(cols) - 1:
            ax.annotate(
                "", xy=(cx + col_width + gap * 0.9, 0.46), xytext=(cx + col_width + 0.002, 0.46),
                arrowprops=dict(arrowstyle="-|>", color=col["color"], lw=2.5, mutation_scale=15),
                zorder=10,
            )

    draw_ribbon(
        ax,
        "Value Promise: the model plans; engines compute; the verifier checks every number against the evidence.",
        COLORS["cyan"],
    )
    save(fig, "architecture_overview")


def create_infrastructure_diagram():
    """AWS infrastructure swimlanes."""
    fig, ax = new_figure()
    draw_header(
        ax,
        "OmniAnalyst — AWS Technical Infrastructure",
        "Scale-to-Zero Serverless Graviton, Bedrock Converse & In-Process OLAP",
        badges=[
            ("AWS SAM Serverless", COLORS["amber"], "#78350f", "#fde68a"),
            ("ARM64 Graviton", COLORS["indigo"], "#1e1b4b", "#a5b4fc"),
            ("Amazon Bedrock", COLORS["purple"], "#4c1d95", "#e9d5ff"),
        ],
    )

    lanes = [
        {
            "y": 0.645, "height": 0.215, "title": "CLIENT & INGRESS PLANE", "color": COLORS["cyan"],
            "nodes": [
                ("AWS Amplify Hosting", "React 18 + Vite SPA\nGlobal CDN\nSSL & continuous deploy", 0.04, 0.24),
                ("Chrome/Edge Extension", "Manifest V3 side panel\nOn-demand table extraction\nPolls /jobs/{id}", 0.31, 0.26),
                ("Amazon API Gateway", "HTTP API v2 (10s integration)\nCORS + idempotency keys\nRoutes to Lambda or SQS", 0.60, 0.34),
            ],
        },
        {
            "y": 0.375, "height": 0.215, "title": "SERVERLESS ROUTING & AI REASONING PLANE", "color": COLORS["purple"],
            "nodes": [
                ("Lambda: API (10s)", "Validate, authorize, enqueue\nPresigned S3 POST\nReturns 202 + job_id", 0.04, 0.22),
                ("SQS Queue + DLQ", "Batch size 1\nVisibility 360s\n3 receives then DLQ", 0.28, 0.20),
                ("Lambda: Worker (300s)", "Schema card + metric catalogue\nBedrock tool loop (11 tools)\nWrites artifact to S3", 0.50, 0.20),
                ("Amazon Bedrock", "Converse API\nOpen-weight profile (interim)\nFailover opt-in", 0.72, 0.24),
            ],
        },
        {
            "y": 0.09, "height": 0.24, "title": "DETERMINISTIC SANDBOX & DATA LAKEHOUSE PLANE", "color": COLORS["emerald"],
            "nodes": [
                ("DuckDB In-Process Engine", "Locked configuration\nNo external access\nRead-only SQL only", 0.04, 0.22),
                ("Guards, Invariants & Verifier", "sqlglot read-only allow-list\nInvariant gates per result\nClaim ↔ evidence check", 0.28, 0.24),
                ("Amazon S3 Lakehouse", "uploads/ 30d + artifacts/ 90d\nSSE + TLS-only policy\nVersioned, private", 0.54, 0.20),
                ("Amazon DynamoDB", "Job status + TTL 90d\nTenant-partitioned keys\nPoint-in-time recovery", 0.76, 0.20),
            ],
        },
    ]

    for lane in lanes:
        lbox = FancyBboxPatch(
            (0.02, lane["y"]), 0.96, lane["height"],
            boxstyle="round,pad=0.01,rounding_size=0.012",
            fc=COLORS["surface"], ec=COLORS["border"], lw=1.2, zorder=2,
        )
        ax.add_patch(lbox)

        llabel_width = min(0.52, len(lane["title"]) * 0.0095 + 0.06)
        llabel = FancyBboxPatch(
            (0.03, lane["y"] + lane["height"] - 0.035), llabel_width, 0.028,
            boxstyle="round,pad=0.004,rounding_size=0.006",
            fc=COLORS["card"], ec=lane["color"], lw=1.2, zorder=3,
        )
        ax.add_patch(llabel)
        ax.text(0.04, lane["y"] + lane["height"] - 0.021, lane["title"],
                fontsize=8.5, fontweight="bold", color=lane["color"], va="center", zorder=4)

        for title, body, nx, nw in lane["nodes"]:
            nbox = FancyBboxPatch(
                (nx, lane["y"] + 0.02), nw, lane["height"] - 0.07,
                boxstyle="round,pad=0.008,rounding_size=0.008",
                fc=COLORS["card"], ec=COLORS["border"], lw=1.0, zorder=3,
            )
            ax.add_patch(nbox)
            nhead = FancyBboxPatch(
                (nx, lane["y"] + lane["height"] - 0.088), nw, 0.032,
                boxstyle="round,pad=0.004,rounding_size=0.006",
                fc=COLORS["card_inner"], ec=lane["color"], lw=1.0, zorder=4,
            )
            ax.add_patch(nhead)
            ax.text(nx + nw / 2, lane["y"] + lane["height"] - 0.072, title,
                    fontsize=8.5, fontweight="bold", color=COLORS["text_primary"],
                    ha="center", va="center", zorder=5)
            body_centre = (lane["y"] + 0.02 + lane["y"] + lane["height"] - 0.088) / 2
            ax.text(nx + nw / 2, body_centre, body,
                    fontsize=7.2, color=COLORS["text_secondary"], ha="center", va="center",
                    zorder=5, linespacing=1.4)

    for upper_top, lower_bottom in ((0.645, 0.593), (0.375, 0.333)):
        ax.annotate(
            "", xy=(0.5, lower_bottom), xytext=(0.5, upper_top - 0.003),
            arrowprops=dict(arrowstyle="-|>", color=COLORS["border"], lw=2.0, mutation_scale=14),
            zorder=10,
        )

    draw_ribbon(
        ax,
        "Technical Protocol: TLS 1.3 in flight | SSE-256 at rest | ARM64 Graviton execution | "
        "sqlglot allow-list sandboxing | Plotly declarative JSON specs",
        COLORS["indigo"],
    )
    save(fig, "detailed_infrastructure")


def create_data_flow_diagram():
    """Request lifecycle: ingestion to verified output."""
    fig, ax = new_figure()
    draw_header(
        ax,
        "OmniAnalyst — Deterministic Data Flow",
        "From Raw Ingestion to an Evidence-Checked, Charted Answer",
        badges=[
            ("Deterministic Gates", COLORS["rose"], "#4c0519", "#fda4af"),
            ("Typed Metric SQL", COLORS["cyan"], "#083344", "#7dd3fc"),
            ("Verified Narrative", COLORS["emerald"], "#064e3b", "#6ee7b7"),
        ],
    )

    steps = [
        ("Step 1: Ingestion", "Presigned S3 upload\nParquet / CSV / documents\nOCR when scanned", COLORS["cyan"]),
        ("Step 2: Grounding", "Schema card profile\nMetric catalogue bind\nRoles, ranges, nulls", COLORS["indigo"]),
        ("Step 3: Planning", "Bedrock Converse loop\nquery_metric or SQL tool\nGuarded, single statement", COLORS["purple"]),
        ("Step 4: Execution", "Locked DuckDB engine\nAggregates, funnels, tests\n5000-row result cap", COLORS["emerald"]),
        ("Step 5: Verification", "Invariant gates per result\nClaim ↔ evidence check\nWarnings travel with job", COLORS["rose"]),
        ("Step 6: Output", "Narrative + Plotly spec\nTrace + verification badge\nArtifact in S3, TTL 90d", COLORS["amber"]),
    ]

    swidth, sgap, ystart, sheight = 0.14, 0.02, 0.56, 0.28
    for i, (title, body, col) in enumerate(steps):
        sx = 0.025 + i * (swidth + sgap)
        sbox = FancyBboxPatch(
            (sx, ystart), swidth, sheight,
            boxstyle="round,pad=0.01,rounding_size=0.01",
            fc=COLORS["card"], ec=col, lw=1.5, zorder=3,
        )
        ax.add_patch(sbox)
        banner = FancyBboxPatch(
            (sx, ystart + sheight - 0.045), swidth, 0.04,
            boxstyle="round,pad=0.005,rounding_size=0.008",
            fc=COLORS["surface"], ec=col, lw=1.0, zorder=4,
        )
        ax.add_patch(banner)
        ax.text(sx + swidth / 2, ystart + sheight - 0.025, title,
                fontsize=8.5, fontweight="bold", color=col, ha="center", va="center", zorder=5)
        ax.text(sx + swidth / 2, ystart + (sheight - 0.05) / 2, body,
                fontsize=7.5, color=COLORS["text_secondary"], ha="center", va="center",
                zorder=5, linespacing=1.5)
        if i < len(steps) - 1:
            ax.annotate(
                "", xy=(sx + swidth + sgap * 0.9, ystart + sheight / 2),
                xytext=(sx + swidth + 0.002, ystart + sheight / 2),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=2.2, mutation_scale=14), zorder=10,
            )

    bcard = FancyBboxPatch(
        (0.025, 0.06), 0.95, 0.44,
        boxstyle="round,pad=0.01,rounding_size=0.012",
        fc=COLORS["surface"], ec=COLORS["border"], lw=1.2, zorder=2,
    )
    ax.add_patch(bcard)
    ax.text(0.04, 0.465, "MULTI-DISCIPLINE STATISTICAL ENGINES & ARITHMETIC GATES",
            fontsize=10.5, fontweight="bold", color=COLORS["cyan"], va="center", zorder=4)

    engines = [
        ("Financial Engine", "ARR waterfall + NRR/GRR\nSeeded runway Monte Carlo\nIdentity reconciliation"),
        ("Product Engine", "Sequential funnels\nCohort retention matrices\nCompleteness flags"),
        ("Operations Engine", "Little's Law (WIP = TH x CT)\nEmpirical lead-time percentiles\nOptional SLA breach"),
        ("Growth Engine", "First/Last/Linear/Position\n(multi-touch when possible)\nLTV, LTV:CAC, payback"),
        ("Clinical Engine", "2x2 contingency tables\nFisher's exact, Haldane OR\nRR + log-normal CI"),
    ]

    ewidth, egap = 0.175, 0.015
    for j, (etitle, ebody) in enumerate(engines):
        ex = 0.04 + j * (ewidth + egap)
        ebox = FancyBboxPatch(
            (ex, 0.10), ewidth, 0.32,
            boxstyle="round,pad=0.008,rounding_size=0.008",
            fc=COLORS["card"], ec=COLORS["border"], lw=1.0, zorder=3,
        )
        ax.add_patch(ebox)
        ehead = FancyBboxPatch(
            (ex, 0.38), ewidth, 0.04,
            boxstyle="round,pad=0.004,rounding_size=0.006",
            fc=COLORS["card_inner"], ec=COLORS["indigo"], lw=1.0, zorder=4,
        )
        ax.add_patch(ehead)
        ax.text(ex + ewidth / 2, 0.40, etitle, fontsize=8.5, fontweight="bold",
                color=COLORS["text_primary"], ha="center", va="center", zorder=5)
        ax.text(ex + ewidth / 2, 0.24, ebody, fontsize=7.2,
                color=COLORS["text_secondary"], ha="center", va="center", zorder=5, linespacing=1.5)

    draw_ribbon(
        ax,
        "Verification Proof: every number rendered is backed by a DuckDB execution trace, an invariant report and a claim check.",
        COLORS["emerald"],
    )
    save(fig, "data_flow_architecture")


def create_determinism_diagram():
    """The planner/executor separation (Analyst IR contract)."""
    fig, ax = new_figure()
    draw_header(
        ax,
        "OmniAnalyst — The Determinism Contract",
        "A Stochastic Planner Cannot Move a Number: Typed Plans, Compiled SQL, Verified Prose",
        badges=[
            ("Planner ≠ Executor", COLORS["rose"], "#4c0519", "#fda4af"),
            ("plan_hash Replay", COLORS["indigo"], "#1e1b4b", "#a5b4fc"),
            ("Fail Closed", COLORS["amber"], "#78350f", "#fde68a"),
        ],
    )

    stages = [
        ("Question", "Natural language\nfrom any client", COLORS["cyan"]),
        ("Planner", "Bedrock model\nReads schema card\nChooses intent + metric", COLORS["purple"]),
        ("Typed Plan", "AnalysisPlan v1\nClosed schema\nSHA-256 plan_hash", COLORS["indigo"]),
        ("Compiler", "Semantic catalogue\nVersioned formulas\nQuoted identifiers", COLORS["amber"]),
        ("Executor", "DuckDB / method library\nSeeded, locked down\nFacts + invariants", COLORS["emerald"]),
        ("Verifier", "Claims ↔ facts\nIdentity checks\nPASS / REVIEW", COLORS["rose"]),
        ("Narrator", "Facts only\nNo new numbers\nEvidence badge", COLORS["cyan"]),
    ]

    swidth, sgap, ystart, sheight = 0.118, 0.015, 0.56, 0.24
    for i, (title, body, col) in enumerate(stages):
        sx = 0.02 + i * (swidth + sgap)
        sbox = FancyBboxPatch(
            (sx, ystart), swidth, sheight,
            boxstyle="round,pad=0.01,rounding_size=0.01",
            fc=COLORS["card"], ec=col, lw=1.5, zorder=3,
        )
        ax.add_patch(sbox)
        ax.text(sx + swidth / 2, ystart + sheight - 0.028, title,
                fontsize=9, fontweight="bold", color=col, ha="center", va="center", zorder=5)
        ax.text(sx + swidth / 2, ystart + (sheight - 0.06) / 2, body,
                fontsize=7.2, color=COLORS["text_secondary"], ha="center", va="center",
                zorder=5, linespacing=1.45)
        if i < len(stages) - 1:
            ax.annotate(
                "", xy=(sx + swidth + sgap * 0.9, ystart + sheight / 2),
                xytext=(sx + swidth + 0.002, ystart + sheight / 2),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=2.0, mutation_scale=13), zorder=10,
            )

    supports = [
        ("Schema Card", "dtype, role, nulls,\ndistinct, ranges", COLORS["cyan"], 0.06),
        ("Metric Catalogue", "30 versioned metrics\naliases → columns", COLORS["purple"], 0.28),
        ("Replay Tuple", "dataset_sha · plan_hash\n· engine_version · seed", COLORS["indigo"], 0.50),
        ("Golden Set", "exact expected numbers\ngate in CI", COLORS["amber"], 0.72),
    ]
    for title, body, col, sx in supports:
        sbox = FancyBboxPatch(
            (sx, 0.30), 0.20, 0.16,
            boxstyle="round,pad=0.008,rounding_size=0.008",
            fc=COLORS["surface"], ec=col, lw=1.2, zorder=3,
        )
        ax.add_patch(sbox)
        ax.text(sx + 0.10, 0.425, title, fontsize=9, fontweight="bold",
                color=col, ha="center", va="center", zorder=5)
        ax.text(sx + 0.10, 0.365, body, fontsize=7.4,
                color=COLORS["text_secondary"], ha="center", va="center", zorder=5, linespacing=1.5)

    ax.annotate("", xy=(0.16, 0.56), xytext=(0.16, 0.465),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["cyan"], lw=1.6, mutation_scale=12), zorder=10)
    ax.annotate("", xy=(0.38, 0.56), xytext=(0.38, 0.465),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["purple"], lw=1.6, mutation_scale=12), zorder=10)
    # Golden Set is a CI asset, not a runtime input: no arrow into the pipeline.

    ax.text(0.04, 0.20, "RULES THE CONTRACT ENFORCES",
            fontsize=10.5, fontweight="bold", color=COLORS["rose"], va="center", zorder=4)
    rules = [
        "1. The planner never computes: every number comes from the executor.",
        "2. The plan is a typed, hashed object — unknown keys are rejected.",
        "3. Catalogued metrics compile to one formula, versioned in git.",
        "4. The narrator sees facts, not data; unsupported numbers are flagged.",
        "5. Same dataset + same plan hash + same engine = same result.",
    ]
    for index, rule in enumerate(rules):
        ax.text(0.04, 0.175 - index * 0.027, rule, fontsize=8.6,
                color=COLORS["text_secondary"], va="center", zorder=4)

    draw_ribbon(
        ax,
        "Determinism is a contract, not a model setting: plan → compile → execute → verify → narrate.",
        COLORS["rose"],
    )
    save(fig, "determinism_contract")


def write_mermaid():
    """Mermaid sources: they render on GitHub and in modern editors."""
    overview = """# OmniAnalyst — Architecture Overview (Mermaid)

```mermaid
flowchart LR
    subgraph A[1. Ingestion & Clients]
        A1[React 18 SPA on Amplify]
        A2[MV3 Browser Extension]
        A3[Presigned S3 Upload]
        A4[Documents: PDF text layer / OCR]
    end
    subgraph B[2. Planning & Semantics]
        B1[Bedrock Converse]
        B2[Schema Card]
        B3[Metric Catalogue + query_metric]
        B4[Typed Plan: Analyst IR]
    end
    subgraph C[3. Deterministic Sandbox]
        C1[Locked DuckDB]
        C2[sqlglot Allow-list]
        C3[Invariant Gates]
        C4[Seeded Method Library]
    end
    subgraph D[4. Verification & Output]
        D1[Claim Verification]
        D2[Execution Trace]
        D3[Multi-Discipline Engines]
        D4[Plotly Spec from Results]
    end
    A --> B --> C --> D
```
"""
    infra = """# OmniAnalyst — AWS Infrastructure (Mermaid)

```mermaid
flowchart TB
    subgraph CLIENT[Client & Ingress Plane]
        SPA[Amplify SPA]
        EXT[MV3 Extension]
        APIGW[API Gateway HTTP API]
    end
    subgraph ROUTING[Serverless Routing & AI Reasoning Plane]
        API[Lambda API 10s]
        SQSQ[SQS + DLQ 360s visibility, 3 receives]
        WRK[Lambda Worker 300s: schema card, metric catalogue, tool loop]
        BRK[Amazon Bedrock Converse]
    end
    subgraph SANDBOX[Deterministic Sandbox & Lakehouse Plane]
        DDB[DuckDB locked engine]
        GRD[SQL Guard + Invariants + Claim Verifier]
        S3[S3 uploads 30d / artifacts 90d]
        DYN[DynamoDB jobs, TTL 90d]
    end
    SPA --> APIGW
    EXT --> APIGW
    APIGW --> API --> SQSQ --> WRK
    WRK --> BRK
    WRK --> DDB --> GRD
    WRK --> S3
    WRK --> DYN
    API --> DYN
```
"""
    dataflow = """# OmniAnalyst — Request Lifecycle (Mermaid)

```mermaid
sequenceDiagram
    participant U as User
    participant G as API Gateway
    participant L as Lambda API
    participant Q as SQS
    participant W as Worker Lambda
    participant B as Bedrock
    participant E as DuckDB + Methods
    participant V as Verifier
    participant S as S3 / DynamoDB

    U->>G: POST /analyze (idempotency key)
    G->>L: validate + limits
    L->>Q: enqueue job (202 + job_id)
    Q->>W: deliver (batch 1)
    W->>S: load dataset (S3 or page context)
    W->>W: build schema card, bind metric catalogue
    loop Tool rounds (max 5)
        W->>B: Converse (system + card + catalogue)
        B-->>W: tool call (query_metric / SQL / discipline)
        W->>E: execute guarded, deterministic
        E-->>W: facts + invariants
    end
    W->>V: claims vs facts
    V-->>W: verification (PASS / REVIEW)
    W->>S: artifact + job status COMPLETED
    U->>G: GET /jobs/{id}
    G-->>U: narrative, chart, trace, verification
```
"""
    determinism = """# OmniAnalyst — The Determinism Contract (Mermaid)

```mermaid
flowchart LR
    Q[Question] --> P[Planner: Bedrock model]
    SC[Schema Card] -.-> P
    P --> IR[Typed Plan: AnalysisPlan v1 + plan_hash]
    MC[Metric Catalogue] -.-> CP
    IR --> CP[Compiler: guarded SQL]
    CP --> EX[Executor: DuckDB / methods]
    EX --> VR[Verifier: claims vs facts]
    VR --> NR[Narrator: facts only]
    NR --> R[Report + badge]
    GS[Golden Set] -.-> CI[CI gate]
    RT[Replay Tuple] -.-> EX
```

## The five rules

1. The planner never computes: every number comes from the executor.
2. The plan is a typed, hashed object; unknown keys are rejected.
3. Catalogued metrics compile to one versioned formula.
4. The narrator sees facts, not data; unsupported numbers are flagged.
5. Same dataset + same plan hash + same engine = same result.
"""
    files = {
        "mermaid-overview.md": overview,
        "mermaid-infrastructure.md": infra,
        "mermaid-dataflow.md": dataflow,
        "mermaid-determinism.md": determinism,
    }
    for name, content in files.items():
        path = os.path.join(OUTPUT_DIR, name)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        print(f"Generated: {path}")


def write_index_html():
    """A zero-dependency viewer so local double-click renders everything."""
    rows = []
    for stem, title in [
        ("architecture_overview", "Executive Architecture Overview"),
        ("detailed_infrastructure", "AWS Infrastructure"),
        ("data_flow_architecture", "Deterministic Data Flow"),
        ("determinism_contract", "The Determinism Contract"),
    ]:
        rows.append(
            f"""  <section>
    <h2>{title}</h2>
    <p class="links">
      <a href="{stem}.png">PNG</a> · <a href="{stem}.svg">SVG</a>
    </p>
    <img src="{stem}.svg" alt="{title}" />
  </section>"""
        )
    mermaid_links = " · ".join(
        f'<a href="{name}">{name}</a>'
        for name in [
            "mermaid-overview.md",
            "mermaid-infrastructure.md",
            "mermaid-dataflow.md",
            "mermaid-determinism.md",
        ]
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>OmniAnalyst — Generated Diagrams</title>
<style>
  body {{ background: #0b0f19; color: #f8fafc; font-family: "Segoe UI", Arial, sans-serif; margin: 0; padding: 24px; }}
  h1 {{ font-size: 22px; }}
  h2 {{ font-size: 16px; color: #38bdf8; margin-bottom: 6px; }}
  section {{ margin-bottom: 32px; }}
  img {{ max-width: 100%; border: 1px solid #334155; border-radius: 8px; background: #111827; }}
  .links a, .m a {{ color: #818cf8; font-size: 12px; }}
</style>
</head>
<body>
<h1>OmniAnalyst — Generated Diagrams</h1>
<p class="m">Mermaid sources (render on GitHub / editors with Mermaid): {mermaid_links}</p>
{"".join(rows)}
</body>
</html>
"""
    path = os.path.join(OUTPUT_DIR, "index.html")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
    print(f"Generated: {path}")


if __name__ == "__main__":
    create_overview_diagram()
    create_infrastructure_diagram()
    create_data_flow_diagram()
    create_determinism_diagram()
    write_mermaid()
    write_index_html()
    print("All diagrams regenerated: PNG + SVG + Mermaid + index.html viewer.")
