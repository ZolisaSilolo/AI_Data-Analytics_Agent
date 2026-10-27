# 🦁 OmniAnalyst: Autonomous Deterministic Data Analyst Platform

[![AWS](https://img.shields.io/badge/AWS-Serverless%20(Scale--to--Zero)-orange)](https://aws.amazon.com)
[![Amplify](https://img.shields.io/badge/Frontend-AWS%20Amplify%20(React)-purple)](https://aws.amazon.com/amplify/)
[![Bedrock](https://img.shields.io/badge/AI-Amazon%20Bedrock%20AgentCore-blue)](https://aws.amazon.com/bedrock/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Engine](https://img.shields.io/badge/Engine-DuckDB%20%2B%20Polars-green)](https://duckdb.org)
[![Automation](https://img.shields.io/badge/Capability-Playwright%20Browser-purple)](https://playwright.dev)

> **OmniAnalyst** is an enterprise-grade, deterministic, multi-disciplinary autonomous Data Analyst platform. Built on AWS Serverless (scaling to zero with $0 idle cost), it replaces probabilistic LLM guesswork with compiled code execution (DuckDB, Polars, Scipy), automated invariant verification gates, native Amazon Bedrock AgentCore integration, a modern **React SPA deployable on AWS Amplify**, and a **Chrome/Edge Manifest V3 Companion Extension**.

---

## ⚡ Core Architecture: Extreme Determinism

```
[React SPA on AWS Amplify / Chrome Extension]
                        │
                        ▼ POST /analyze
      [AWS Serverless HTTP API Gateway ($0 Idle)]
                        │
                        ▼
      [Amazon Bedrock AgentCore (Claude 3.5 Sonnet / Nova Pro)]
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
- **Modern React Frontend for AWS Amplify**:
  - Built with **React 18 + Vite** in [`frontend/`](frontend/).
  - Connects to your backend API Gateway.
  - Includes multi-discipline toolkits, live Plotly visualizations, transparent execution audit logs, and web portal scraping.
  - Pre-configured with [`amplify.yml`](amplify.yml) for 1-click AWS Amplify continuous deployment.
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

### 1. Run Tests (Backend)
```bash
python -m pytest tests -v
```

### 2. Local Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### 3. Deploy Backend to AWS (SAM Scale-to-Zero)
```bash
sam build
sam deploy --guided
```

### 4. Deploy Frontend to AWS Amplify Hosting
1. Push your repository to GitHub.
2. In the **AWS Amplify Console**, select **Host web app**.
3. Connect your GitHub repository (`AI_Data-Analytics_Agent`).
4. Amplify will automatically detect the [`amplify.yml`](amplify.yml) build specification:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - cd frontend
           - npm install
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: frontend/dist
       files:
         - '**/*'
     cache:
       paths:
         - frontend/node_modules/**/*
   ```
5. Click **Save and Deploy**. Your React app is live on a global CloudFront CDN with SSL and continuous deployment!

---

## 🧩 Installing the Browser Extension (Manifest V3)

1. Open Chrome or Edge and navigate to `chrome://extensions/` (or `edge://extensions/`).
2. Toggle on **Developer mode** in the top right corner.
3. Click **Load unpacked** and select the [`extension/`](extension/) directory from this repository.
4. Click the extension icon in your browser toolbar to open the **OmniAnalyst Sidepanel**.
5. Set your deployed API Gateway endpoint in the sidepanel config and start analyzing active tabs!

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
