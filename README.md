# 🦁 OmniAnalyst: Autonomous Deterministic Data Analyst Platform

[![AWS](https://img.shields.io/badge/AWS-Serverless%20(Scale--to--Zero)-orange)](https://aws.amazon.com)
[![Bedrock](https://img.shields.io/badge/AI-Amazon%20Bedrock%20AgentCore-blue)](https://aws.amazon.com/bedrock/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Engine](https://img.shields.io/badge/Engine-DuckDB%20%2B%20Polars-green)](https://duckdb.org)
[![Automation](https://img.shields.io/badge/Capability-Playwright%20Browser-purple)](https://playwright.dev)

> **OmniAnalyst** is an enterprise-grade, deterministic, multi-disciplinary autonomous Data Analyst platform. Built on AWS Serverless (scaling to zero with $0 idle cost), it replaces probabilistic LLM guesswork with compiled code execution (DuckDB, Polars, Scipy), automated invariant verification gates, and native Amazon Bedrock AgentCore integration.

---

## ⚡ Core Architecture: Extreme Determinism

```
[User / Browser Extension / Streamlit]
                  │
                  ▼ POST /analyze
[AWS Serverless HTTP API Gateway ($0 Idle)]
                  │
                  ▼
[Amazon Bedrock AgentCore (Claude 3.5 Sonnet / Amazon Nova Pro)]
                  │
                  ├── Formulates Hypotheses & Compiles Analytical Code
                  │
                  ▼ Tool Invocation Loop
┌─────────────────────────────────────────────────────────────┐
│             Deterministic Sandboxed Execution Engine        │
│  - DuckDB / Polars (Vectorised in-memory execution)         │
│  - AST Security Linter (Blocks unsafe OS/socket imports)    │
│  - Automated Invariant Gates (Sample size, [0,1] bounds,    │
│    reconciliations, Benjamini-Hochberg FDR)                 │
└─────────────────────────────────────────────────────────────┘
                  │
                  ├── Outputs Verified Numerical Facts Only
                  ▼
[Executive Synthesis + Declarative Plotly & Vega-Lite Specs]
```

---

## 🌟 Modernized Capabilities

- **100% Deterministic (Zero LLM-Hallucinated Math)**: The model acts as a code compiler and planner. All statistics, cohort retention tables, regressions, and aggregations are compiled and executed by DuckDB and Polars.
- **Native Amazon Bedrock AgentCore**: Replaced external vendor endpoints with Bedrock Converse API (`anthropic.claude-3-5-sonnet-20241022-v2:0` and `amazon.nova-pro-v1:0`), with automatic failover and guardrails.
- **Scale-to-Zero ($0 Idle Cost)**:
  - **API Gateway HTTP API**: Pay-per-request, scale-to-zero.
  - **AWS Lambda (ARM64 Graviton)**: Ephemeral compute, scale-to-zero.
  - **Amazon DynamoDB**: `PAY_PER_REQUEST` billing mode, scale-to-zero.
  - **Amazon S3 Lakehouse**: Encrypted with SSE-256 and automatic lifecycle expiration for ephemeral charts.
- **Multi-Discipline Analytical Engines**:
  - **Product Analytics**: Funnels, interval-precise cohort retention matrices, Kaplan-Meier drop-off curves.
  - **Financial & RevOps**: SaaS ARR/MRR waterfalls, NRR/GRR reconciliation, Monte Carlo runway simulations.
  - **Operations & Supply Chain**: Little's Law ($WIP = \lambda W$), lead-time distribution fitting, SLA risk bounds.
  - **Marketing & Growth**: First/Last/Linear and Markov Chain attribution models, CAC/LTV unit economics.
  - **Clinical & Biotech**: 2x2 contingency tables, Odds Ratios with 95% Wald CIs, Fisher's Exact test.
- **Playwright Headless Browser Tool**: Extract tables from live web URLs, scrape dashboards (Tableau, PowerBI, Metabase, QuickSight), and capture high-resolution snapshots.
- **Browser Extension (Manifest V3)**: Chrome/Edge sidepanel companion allowing analysts to extract active webpage tables and trigger instant Bedrock analyses.

---

## 🚀 Quick Start

### 1. Setup Local Environment
```bash
git clone https://github.com/ZolisaSilolo/AI_Data-Analytics_Agent.git
cd AI_Data_Analyst_Agent

python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Tests
```bash
python -m pytest tests -v
```

### 3. Launch Streamlit Platform
```bash
streamlit run src/streamlit_app.py
```

### 4. Deploy to AWS (Scale-to-Zero)
```bash
sam build
sam deploy --guided
```

---

## 🧩 Installing the Browser Extension (Manifest V3)

1. Open Chrome or Edge and navigate to `chrome://extensions/` (or `edge://extensions/`).
2. Toggle on **Developer mode** in the top right corner.
3. Click **Load unpacked** and select the [`extension/`](extension/) directory from this repository.
4. Click the extension icon in your browser toolbar to open the **OmniAnalyst Sidepanel**.
5. Set your deployed API Gateway endpoint in the sidepanel config and start analyzing active tabs!

---

## 🔒 Security & Well-Architected Hardening

- **AST Code Inspection**: Validates all synthesized Python scripts via Python's Abstract Syntax Tree to block malicious system calls, file tampering, and shell execution.
- **Least-Privilege IAM**: Granular policies restricting Bedrock invocation and S3 read/writes.
- **TLS 1.2+ Enforcement**: S3 bucket policies explicitly deny non-SSL traffic (`aws:SecureTransport: false`).
- **AWS Lambda Powertools**: Structured JSON logging, correlation IDs, and CloudWatch metrics.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
