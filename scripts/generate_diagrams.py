"""
OmniAnalyst Architecture Diagram Generator
Generates publication-quality diagrams in both SVG and PNG formats for all stakeholder personas.
"""

import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated-diagrams")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Theme Palette (Dark-slate Enterprise Theme matching React UI)
COLORS = {
    'bg': '#0b0f19',
    'surface': '#111827',
    'card': '#1e293b',
    'card_inner': '#0f172a',
    'border': '#334155',
    'border_subtle': '#1e293b',
    'text_primary': '#f8fafc',
    'text_secondary': '#94a3b8',
    'text_muted': '#64748b',
    'cyan': '#38bdf8',
    'indigo': '#818cf8',
    'purple': '#c084fc',
    'emerald': '#34d399',
    'amber': '#f59e0b',
    'rose': '#f43f5e',
    'accent_dark': '#0f172a'
}


def draw_header(ax, title, subtitle, badges=None):
    """Draws enterprise header bar with badges."""
    # Header card
    header_box = FancyBboxPatch((0.02, 0.90), 0.96, 0.08,
                               boxstyle="round,pad=0.015,rounding_size=0.015",
                               fc=COLORS['card'], ec=COLORS['border'], lw=1.5, zorder=2)
    ax.add_patch(header_box)
    
    # Title & Subtitle
    ax.text(0.04, 0.95, title, fontsize=15, fontweight='bold', color=COLORS['text_primary'], va='center', zorder=3)
    ax.text(0.04, 0.92, subtitle, fontsize=9.5, color=COLORS['cyan'], va='center', zorder=3)
    
    # Badges on right
    if badges:
        bx = 0.96
        for text, border_col, bg_col, text_col in reversed(badges):
            b_width = len(text) * 0.0075 + 0.03
            bx -= b_width
            badge_patch = FancyBboxPatch((bx, 0.925), b_width - 0.01, 0.032,
                                        boxstyle="round,pad=0.005,rounding_size=0.01",
                                        fc=bg_col, ec=border_col, lw=1.2, zorder=4)
            ax.add_patch(badge_patch)
            ax.text(bx + (b_width - 0.01)/2, 0.941, text, fontsize=7.5, fontweight='bold',
                    color=text_col, ha='center', va='center', zorder=5)
            bx -= 0.005


def create_overview_diagram():
    """Generates the Executive & Non-Technical Architecture Diagram."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
    fig.patch.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['bg'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    draw_header(
        ax,
        "OmniAnalyst — Executive Architecture Overview",
        "How Business Hypotheses Transform into Deterministic, Hallucination-Free Insights",
        badges=[
            ("Zero Hallucination", COLORS['rose'], "#4c0519", "#fda4af"),
            ("$0 Idle Cost", COLORS['emerald'], "#064e3b", "#6ee7b7"),
            ("Graviton ARM64", COLORS['indigo'], "#1e1b4b", "#a5b4fc")
        ]
    )
    
    cols = [
        {
            "num": "1", "title": "INGESTION & CLIENTS", "color": COLORS['cyan'],
            "sub": "Cross-Platform Access",
            "items": [
                ("React 18 SPA (AWS Amplify)", "Global CDN, Dark-slate UI, Plotly charts"),
                ("Chrome/Edge Extension (MV3)", "Instant 1-click AG-Grid & DOM table scrape"),
                ("Presigned S3 Upload", "Size-capped server-generated object keys"),
                ("Amazon S3 Data Lakehouse", "Parquet/CSV raw business data storage")
            ]
        },
        {
            "num": "2", "title": "REASONING & DECIDER", "color": COLORS['purple'],
            "sub": "Autonomous Planning",
            "items": [
                ("Amazon Bedrock Converse", "Kimi K3 (global profile, interim)"),
                ("Typed Discipline Tools", "Ten audited tools, no arbitrary code"),
                ("Automated Hypotheses", "Breaks business questions into analytical steps"),
                ("SQL Code Compilation", "Synthesizes precise DuckDB queries")
            ]
        },
        {
            "num": "3", "title": "DETERMINISTIC SANDBOX", "color": COLORS['emerald'],
            "sub": "Zero-Hallucination Execution",
            "items": [
                ("DuckDB In-Process Engine", "Vectorized C++ OLAP executing in microseconds"),
                ("SQL Allow-list Gate", "sqlglot AST blocks DDL, files, URLs"),
                ("Automated Invariant Gates", "Enforces mass conservation & [0,1] bounds"),
                ("PyArrow Zero-Copy Stream", "Direct RAM streaming from S3 / Parquet")
            ]
        },
        {
            "num": "4", "title": "MULTI-DISCIPLINE ENGINES", "color": COLORS['amber'],
            "sub": "Verified Business Insights",
            "items": [
                ("Financial & RevOps", "ARR/MRR waterfalls, runway Monte Carlo"),
                ("Product Analytics", "Funnel drop-off & cohort retention matrices"),
                ("Operations & Queuing", "Little's Law, lead-time variance, bottlenecks"),
                ("Growth & Attribution", "Multi-touch attribution, CAC/LTV cohorts"),
                ("Clinical & Biostatistics", "2x2 Contingency, Odds Ratios, Fisher's test")
            ]
        }
    ]
    
    col_width = 0.225
    gap = 0.018
    start_x = 0.02
    
    for i, col in enumerate(cols):
        cx = start_x + i * (col_width + gap)
        
        # Outer column card
        card = FancyBboxPatch((cx, 0.06), col_width, 0.81,
                              boxstyle="round,pad=0.012,rounding_size=0.012",
                              fc=COLORS['surface'], ec=COLORS['border'], lw=1.2, zorder=2)
        ax.add_patch(card)
        
        # Column Header Badge
        header_patch = FancyBboxPatch((cx, 0.81), col_width, 0.06,
                                     boxstyle="round,pad=0.008,rounding_size=0.01",
                                     fc=COLORS['card'], ec=col['color'], lw=1.5, zorder=3)
        ax.add_patch(header_patch)
        
        ax.text(cx + 0.015, 0.845, f"{col['num']}. {col['title']}", fontsize=10.5, fontweight='bold',
                color=col['color'], va='center', zorder=4)
        ax.text(cx + 0.015, 0.825, col['sub'], fontsize=7.5, color=COLORS['text_muted'], va='center', zorder=4)
        
        # Cards inside column
        item_y = 0.74
        item_height = 0.145 if len(col['items']) == 4 else 0.118
        for title, desc in col['items']:
            box_bottom = item_y - item_height + 0.02
            ibox = FancyBboxPatch((cx + 0.01, box_bottom), col_width - 0.02, item_height - 0.02,
                                  boxstyle="round,pad=0.008,rounding_size=0.008",
                                  fc=COLORS['card'], ec=COLORS['border'], lw=1.0, zorder=3)
            ax.add_patch(ibox)

            # Left accent stripe
            stripe = FancyBboxPatch((cx + 0.012, box_bottom + 0.005), 0.004, item_height - 0.03,
                                   boxstyle="round,pad=0.001,rounding_size=0.002",
                                   fc=col['color'], ec='none', zorder=4)
            ax.add_patch(stripe)

            # Vertically centre the two text lines inside the card
            centre = (item_y + box_bottom) / 2
            ax.text(cx + 0.022, centre + 0.018, title, fontsize=9, fontweight='bold',
                    color=COLORS['text_primary'], va='center', zorder=4)
            ax.text(cx + 0.022, centre - 0.004, desc, fontsize=7.2,
                    color=COLORS['text_secondary'], va='top', zorder=4, wrap=True)

            item_y -= item_height + 0.012

        # Connecting Arrow to next column
        if i < len(cols) - 1:
            ax.annotate("", xy=(cx + col_width + gap * 0.9, 0.46), xytext=(cx + col_width + 0.002, 0.46),
                        arrowprops=dict(arrowstyle="-|>", color=col['color'], lw=2.5, mutation_scale=15),
                        zorder=10)

    # Bottom Business Guarantee Ribbon
    ribbon = FancyBboxPatch((0.02, 0.015), 0.96, 0.035,
                            boxstyle="round,pad=0.005,rounding_size=0.008",
                            fc=COLORS['card'], ec=COLORS['border'], lw=1.0, zorder=2)
    ax.add_patch(ribbon)
    ax.text(0.5, 0.032,
            "Value Promise: Non-technical users input natural language hypotheses; the deterministic pipeline compiles and verifies all calculations in DuckDB.",
            fontsize=8.5, color=COLORS['cyan'], ha='center', va='center', zorder=3)

    plt.tight_layout()
    png_path = os.path.join(OUTPUT_DIR, "architecture_overview.png")
    svg_path = os.path.join(OUTPUT_DIR, "architecture_overview.svg")
    fig.savefig(png_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    fig.savefig(svg_path, format='svg', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"Generated: {png_path} and {svg_path}")


def create_infrastructure_diagram():
    """Generates the Cloud-Native AWS Technical Infrastructure Diagram."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
    fig.patch.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['bg'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    draw_header(
        ax,
        "OmniAnalyst — Technical Cloud-Native AWS Infrastructure",
        "Scale-to-Zero Serverless Graviton Architecture, Amazon Bedrock Converse API & In-Process OLAP",
        badges=[
            ("AWS SAM Serverless", COLORS['amber'], "#78350f", "#fde68a"),
            ("ARM64 Graviton3", COLORS['indigo'], "#1e1b4b", "#a5b4fc"),
            ("Amazon Bedrock", COLORS['purple'], "#4c1d95", "#e9d5ff")
        ]
    )
    
    # 3 Horizontal Swimlanes:
    # 1. Edge & Client Presentation (Top)
    # 2. Serverless Orchestration & Intelligence (Middle)
    # 3. Deterministic OLAP Sandbox & Lakehouse (Bottom)

    lanes = [
        {
            "y": 0.645, "height": 0.215, "title": "CLIENT & INGRESS PLANE", "color": COLORS['cyan'],
            "nodes": [
                ("AWS Amplify Hosting", "React 18 + Vite SPA\nGlobal CloudFront CDN\nSSL & Continuous Deploy", 0.04, 0.24),
                ("Chrome/Edge Extension", "Manifest V3 Sidepanel API\nOn-demand table extraction\nPolls /jobs/{id}", 0.31, 0.26),
                ("Amazon API Gateway", "HTTP API v2 (10s integration)\nCORS + Idempotency Keys\nRoutes to Lambda or SQS", 0.60, 0.34)
            ]
        },
        {
            "y": 0.375, "height": 0.215, "title": "SERVERLESS ROUTING & AI REASONING PLANE", "color": COLORS['purple'],
            "nodes": [
                ("Lambda: API (10s)", "Validate, authorize, enqueue\nPresigned S3 POST\nReturns 202 + job_id", 0.04, 0.22),
                ("SQS Queue + DLQ", "Batch size 1\nVisibility 360s\n3 receives then DLQ", 0.28, 0.20),
                ("Lambda: Worker (300s)", "Loads dataset from S3\nRuns Bedrock tool loop\nWrites artifact to S3", 0.50, 0.20),
                ("Amazon Bedrock", "Converse API\nKimi K3 (interim)\nFailover opt-in", 0.72, 0.24)
            ]
        },
        {
            "y": 0.09, "height": 0.24, "title": "DETERMINISTIC SANDBOX & DATA LAKEHOUSE PLANE", "color": COLORS['emerald'],
            "nodes": [
                ("DuckDB In-Process Engine", "Locked configuration\nNo external access\nRead-only SQL only", 0.04, 0.22),
                ("SQL Guard + Invariants", "sqlglot read-only allow-list\nBounds & reconciliation\n5000-row result cap", 0.28, 0.24),
                ("Amazon S3 Lakehouse", "uploads/ + artifacts/\nSSE + TLS-only policy\n30d / 14d lifecycle", 0.54, 0.20),
                ("Amazon DynamoDB", "Job status + TTL 90d\nTenant-partitioned keys\nPoint-in-time recovery", 0.76, 0.20)
            ]
        }
    ]

    for lane in lanes:
        # Lane boundary box
        lbox = FancyBboxPatch((0.02, lane['y']), 0.96, lane['height'],
                              boxstyle="round,pad=0.01,rounding_size=0.012",
                              fc=COLORS['surface'], ec=COLORS['border'], lw=1.2, zorder=2)
        ax.add_patch(lbox)

        # Lane label badge sized to its text so it never overflows the lane
        llabel_width = min(0.52, len(lane['title']) * 0.0095 + 0.06)
        llabel = FancyBboxPatch((0.03, lane['y'] + lane['height'] - 0.035), llabel_width, 0.028,
                               boxstyle="round,pad=0.004,rounding_size=0.006",
                               fc=COLORS['card'], ec=lane['color'], lw=1.2, zorder=3)
        ax.add_patch(llabel)
        ax.text(0.04, lane['y'] + lane['height'] - 0.021, lane['title'],
                fontsize=8.5, fontweight='bold', color=lane['color'], va='center', zorder=4)

        # Draw nodes
        for title, body, nx, nw in lane['nodes']:
            nbox = FancyBboxPatch((nx, lane['y'] + 0.02), nw, lane['height'] - 0.07,
                                  boxstyle="round,pad=0.008,rounding_size=0.008",
                                  fc=COLORS['card'], ec=COLORS['border'], lw=1.0, zorder=3)
            ax.add_patch(nbox)

            # Node header bar
            nhead = FancyBboxPatch((nx, lane['y'] + lane['height'] - 0.088), nw, 0.032,
                                   boxstyle="round,pad=0.004,rounding_size=0.006",
                                   fc=COLORS['card_inner'], ec=lane['color'], lw=1.0, zorder=4)
            ax.add_patch(nhead)
            ax.text(nx + nw/2, lane['y'] + lane['height'] - 0.072, title,
                    fontsize=8.5, fontweight='bold', color=COLORS['text_primary'], ha='center', va='center', zorder=5)

            # Body text is centred in the space left below the header bar.
            body_centre = (lane['y'] + 0.02 + lane['y'] + lane['height'] - 0.088) / 2
            ax.text(nx + nw/2, body_centre, body,
                    fontsize=7.2, color=COLORS['text_secondary'], ha='center', va='center', zorder=5, linespacing=1.4)

    # Plane-order connectors drawn in the gaps between swimlanes so no arrow
    # crosses a node box.
    for upper_top, lower_bottom in ((0.645, 0.593), (0.375, 0.333)):
        ax.annotate("", xy=(0.5, lower_bottom), xytext=(0.5, upper_top - 0.003),
                    arrowprops=dict(arrowstyle="-|>", color=COLORS['border'], lw=2.0,
                                    mutation_scale=14), zorder=10)

    # Bottom Protocol Specs Ribbon
    ribbon = FancyBboxPatch((0.02, 0.015), 0.96, 0.035,
                            boxstyle="round,pad=0.005,rounding_size=0.008",
                            fc=COLORS['card'], ec=COLORS['border'], lw=1.0, zorder=2)
    ax.add_patch(ribbon)
    ax.text(0.5, 0.032,
            "Technical Protocol: TLS 1.3 In-Flight | SSE-256 S3 At-Rest | ARM64 Graviton3 Execution | "
            "sqlglot Allow-list Sandboxing | Plotly Declarative JSON Specs",
            fontsize=8.2, color=COLORS['indigo'], ha='center', va='center', zorder=3)

    plt.tight_layout()
    png_path = os.path.join(OUTPUT_DIR, "detailed_infrastructure.png")
    svg_path = os.path.join(OUTPUT_DIR, "detailed_infrastructure.svg")
    fig.savefig(png_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    fig.savefig(svg_path, format='svg', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"Generated: {png_path} and {svg_path}")


def create_data_flow_diagram():
    """Generates the Data Flow & Deterministic Execution Pipeline Diagram."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
    fig.patch.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['bg'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    draw_header(
        ax,
        "OmniAnalyst — Deterministic Data Flow",
        "Step-by-Step Lifecycle from Raw Ingestion to Verified Multi-Disciplinary Plotly Visualizations",
        badges=[
            ("Deterministic Gates", COLORS['rose'], "#4c0519", "#fda4af"),
            ("PyArrow In-Memory", COLORS['cyan'], "#083344", "#7dd3fc"),
            ("Vectorized DuckDB", COLORS['emerald'], "#064e3b", "#6ee7b7")
        ]
    )

    steps = [
        ("Step 1: Ingestion", "Presigned S3 upload\nParquet / CSV / DOM table\nPyArrow buffer load", COLORS['cyan']),
        ("Step 2: AI Planning", "Bedrock Converse API\nHypothesis decomposition\nCompiles analytical SQL", COLORS['purple']),
        ("Step 3: SQL Allow-list", "sqlglot AST validation\nRead-only SELECT only\nNo files, URLs or DDL", COLORS['rose']),
        ("Step 4: DuckDB Execution", "Locked in-memory engine\nAggregations, joins & cohorts\n5000-row result cap", COLORS['emerald']),
        ("Step 5: Invariant Gates", "Reconciliation checks\nBounds [0,1], non-negative\nSample-size warnings", COLORS['amber']),
        ("Step 6: Visualization", "Plotly declarative JSON\nTabular SQL result\nRendered on React 18 SPA", COLORS['indigo'])
    ]

    swidth = 0.14
    sgap = 0.02
    ystart = 0.56
    sheight = 0.28

    for i, (title, body, col) in enumerate(steps):
        sx = 0.025 + i * (swidth + sgap)
        
        # Step box
        sbox = FancyBboxPatch((sx, ystart), swidth, sheight,
                              boxstyle="round,pad=0.01,rounding_size=0.01",
                              fc=COLORS['card'], ec=col, lw=1.5, zorder=3)
        ax.add_patch(sbox)
        
        # Step header banner
        banner = FancyBboxPatch((sx, ystart + sheight - 0.045), swidth, 0.04,
                               boxstyle="round,pad=0.005,rounding_size=0.008",
                               fc=COLORS['surface'], ec=col, lw=1.0, zorder=4)
        ax.add_patch(banner)
        ax.text(sx + swidth/2, ystart + sheight - 0.025, title,
                fontsize=8.5, fontweight='bold', color=col, ha='center', va='center', zorder=5)
        
        ax.text(sx + swidth/2, ystart + (sheight - 0.05)/2, body,
                fontsize=7.5, color=COLORS['text_secondary'], ha='center', va='center', zorder=5, linespacing=1.5)

        # Arrow to next step
        if i < len(steps) - 1:
            ax.annotate("", xy=(sx + swidth + sgap * 0.9, ystart + sheight/2),
                        xytext=(sx + swidth + 0.002, ystart + sheight/2),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=2.2, mutation_scale=14), zorder=10)

    # Lower Section: Multi-Discipline Engines & Statistical Guarantees
    bcard = FancyBboxPatch((0.025, 0.06), 0.95, 0.44,
                           boxstyle="round,pad=0.01,rounding_size=0.012",
                           fc=COLORS['surface'], ec=COLORS['border'], lw=1.2, zorder=2)
    ax.add_patch(bcard)

    ax.text(0.04, 0.465, "MULTI-DISCIPLINARY STATISTICAL ENGINES & ARITHMETIC GATES",
            fontsize=10.5, fontweight='bold', color=COLORS['cyan'], va='center', zorder=4)

    engines = [
        ("Financial Engine", "ARR / MRR Waterfall\nRunway Monte Carlo\nConservation of Currency ($)"),
        ("Product Engine", "Funnel Drop-off\nCohort Retention Matrices\nStep Transition Ratios"),
        ("Operations Engine", "Little's Law (WIP = TH x CT)\nLead-time Percentiles\nSLA Breach Risk"),
        ("Growth Engine", "First / Last / Linear\nLTV, LTV:CAC Ratio\nCAC Payback Months"),
        ("Clinical Engine", "2x2 Contingency Tables\nFisher's Exact Test\nOdds Ratios & 95% Wald CI")
    ]

    ewidth = 0.175
    egap = 0.015
    for j, (etitle, ebody) in enumerate(engines):
        ex = 0.04 + j * (ewidth + egap)
        ebox = FancyBboxPatch((ex, 0.10), ewidth, 0.32,
                              boxstyle="round,pad=0.008,rounding_size=0.008",
                              fc=COLORS['card'], ec=COLORS['border'], lw=1.0, zorder=3)
        ax.add_patch(ebox)

        # Engine Title
        ehead = FancyBboxPatch((ex, 0.38), ewidth, 0.04,
                               boxstyle="round,pad=0.004,rounding_size=0.006",
                               fc=COLORS['card_inner'], ec=COLORS['indigo'], lw=1.0, zorder=4)
        ax.add_patch(ehead)
        ax.text(ex + ewidth/2, 0.40, etitle, fontsize=8.5, fontweight='bold',
                color=COLORS['text_primary'], ha='center', va='center', zorder=5)

        ax.text(ex + ewidth/2, 0.24, ebody, fontsize=7.2,
                color=COLORS['text_secondary'], ha='center', va='center', zorder=5, linespacing=1.5)

    # Bottom Guarantee Ribbon
    ribbon = FancyBboxPatch((0.025, 0.015), 0.95, 0.035,
                            boxstyle="round,pad=0.005,rounding_size=0.008",
                            fc=COLORS['card'], ec=COLORS['border'], lw=1.0, zorder=2)
    ax.add_patch(ribbon)
    ax.text(0.5, 0.032,
            "Verification Proof: Every number rendered in Plotly charts is accompanied by a transparent DuckDB SQL execution trace and invariant test report.",
            fontsize=8.2, color=COLORS['emerald'], ha='center', va='center', zorder=3)

    plt.tight_layout()
    png_path = os.path.join(OUTPUT_DIR, "data_flow_architecture.png")
    svg_path = os.path.join(OUTPUT_DIR, "data_flow_architecture.svg")
    fig.savefig(png_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    fig.savefig(svg_path, format='svg', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"Generated: {png_path} and {svg_path}")


if __name__ == "__main__":
    create_overview_diagram()
    create_infrastructure_diagram()
    create_data_flow_diagram()
    print("All architecture diagrams successfully generated in PNG and SVG formats!")
