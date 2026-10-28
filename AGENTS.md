# AGENTS.md - Essential Context for OpenCode Sessions

## Essential Commands

### Development Workflow
- **Run tests**: `pytest tests -v`
- **Lint code**: `ruff check src tests scripts`
- **Type check**: `mypy src`
- **Format code**: `ruff check --fix src tests scripts`

### Verification & Testing
- **Verify Bedrock access**: `python scripts/verify_bedrock_access.py`
- **Run smoke agent test**: `python scripts/smoke_bedrock_agent.py`
- **Run single test**: `pytest tests/test_specific_file.py -v`

### Frontend Development
- **Start dev server**: `cd frontend && npm run dev`
- **Build for production**: `cd frontend && npm run build`

### Backend Deployment
- **Build and deploy**: `sam build && sam deploy --guided`
  - Requires AWS credentials configured
  - First deployment will prompt for configuration

### Diagram Generation
- **Regenerate architecture diagrams**: `python scripts/generate_diagrams.py`
  - Outputs to `generated-diagrams/` directory
  - Creates PNG, SVG, Mermaid sources, and index.html viewer

## Project Structure

### Core Architecture
- **Entry point**: `src/lambda_function.py` (HTTP API handler)
- **Heavy analysis**: `src/worker.py` (SQS worker, 300s budget)
- **Core logic**: `src/core/` (data handling, visualizations)
- **Planning**: `src/plan/` (compiler, IR generation)
- **Agent services**: `src/agent/` (Bedrock interaction)
- **Verification**: `src/verify/` (claim verification)
- **Data ingestion**: `src/ingest/` (data processing)
- **Storage**: `src/storage.py` (S3/DynamoDB interaction)

### Key Directories
- `src/`: Main application code
- `frontend/`: React/TypeScript SPA
- `extension/`: VS Code/Edge browser extension
- `generated-diagrams/`: Architecture diagrams (PNG/SVG/Mermaid)
- `scripts/`: Utility scripts (diagram generation, verification, etc.)
- `tests/`: Unit tests

## Important Notes

### Deterministic Execution
- The system enforces a strict planner/executor separation
- Language model (Bedrock) only plans; never computes results
- All computations happen in locked DuckDB sandbox or statistical libraries
- Every number in output must be traceable to tool execution

### Environment Variables
- `BEDROCK_PRIMARY_MODEL`: Set to model ID (e.g., `global.moonshotai.kimi-k3`)
- `AWS_REGION`: Defaults to `us-east-1`
- See `scripts/verify_bedrock_access.py` for usage examples

### Testing Constraints
- Unit tests use pytest with custom configuration in pyproject.toml
- Test paths: `tests/` (see tool.pytest.ini_options)
- Coverage threshold: 60% minimum
- Ruff linting excludes: frontend, generated-diagrams, .venv

### Linting/Formatting
- Ruff configuration: line-length 120, targets py312
- Specific ignores configured in pyproject.toml:
  - S101, S104, S311, S603, S607, B008 (general)
  - S105, S106 for tests
  - S102 for src/engine/sandbox.py
  - E501 for scripts/generate_diagrams.py and tests/test_agent.py

### Diagram Files
- Architecture diagrams are generated, not hand-maintained
- Located in `generated-diagrams/` directory
- Includes PNG, SVG, and Mermaid sources
- View locally with `generated-diagrams/index.html`

## Getting Started

1. Verify environment setup: `python scripts/verify_bedrock_access.py`
2. Run smoke test: `python scripts/smoke_bedrock_agent.py`
3. Start development: 
   - Backend: `pytest` for testing, `ruff check` for linting
   - Frontend: `cd frontend && npm run dev`
4. Regenerate diagrams when architecture changes: `python scripts/generate_diagrams.py`

## Common Gotchas

- The HTTP API has a 30-second integration limit; heavy analysis runs in worker
- Bedrock model access must be pre-verified before deployment
- Diagram generation requires matplotlib and related dependencies
- Frontend and backend are deployed separately (frontend to Amplify, backend to Lambda)