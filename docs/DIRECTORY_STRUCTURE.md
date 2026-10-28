# Directory Structure Guide

## Repository Organization

```
AI_Data-Analytics_Agent/
├── src/                    # Main application source code
│   ├── aws/               # AWS service integrations
│   ├── agent/            # Bedrock agent interactions
│   ├── api/              # API layer and validation
│   ├── config/           # Configuration management
│   ├── core/             # Core business logic
│   ├── dataprof/         # Data profiling utilities
│   ├── disciplines/      # Domain-specific analysis modules
│   ├── engine/           # Execution engines (sandbox, SQL guard)
│   ├── ingest/           # Data ingestion and processing
│   ├── plan/             # Analysis planning and IR generation
│   ├── rag/              # RAG pipeline and vector storage
│   ├── semantic/         # Semantic search and catalog
│   ├── services/         # Business services
│   ├── storage/          # Data persistence layer
│   ├── utils/            # Common utilities
│   └── verify/           # Claim verification
├── frontend/             # React/TypeScript application
│   ├── src/
│   └── public/
├── extension/            # Browser extension
│   ├── sidepanel/
│   └── vendor/
├── generated-diagrams/   # Auto-generated architecture diagrams
├── docs/                 # Documentation
├── scripts/             # Utility scripts
├── tests/               # Unit and integration tests
├── requirements*.txt    # Python dependencies
└── *.yaml               # Infrastructure definitions
```

## Key Directories Explained

### src/aws/
- `__init__.py`: AWS client factory and service integrations
- Handles all AWS SDK interactions with proper configuration

### src/config/
- `__init__.py`: Centralized configuration management
- Environment variable handling with defaults
- Configuration validation

### src/storage/
- `__init__.py`: Storage module exports
- `s3_storage.py`: S3 bucket operations
- `repository.py`: Generic repository pattern
- `README.md`: Storage module documentation

### src/utils/
- `__init__.py`: Common utility functions
- ID generation, timestamp formatting, safe dictionary access

### src/engine/sandbox/
- Execution sandbox for secure code execution
- Isolated environment for DuckDB operations

## File Naming Conventions

- **Python files**: `snake_case.py`
- **Configuration files**: `lowercase-with-dashes.ext`
- **Test files**: `test_snake_case.py`
- **Utility files**: refer to their purpose (e.g., `generate_id`, `format_timestamp`)

## Import Patterns

```python
# Internal imports (within src/)
from src.utils import generate_id
from src.config import config
from src.aws import AWSClientFactory

# External imports
import boto3
from aws_lambda_powertools import Logger
```

## Security Notes

- Credentials are never committed to Git
- `.gitignore` blocks all sensitive files
- Environment-specific configs go in `.env` files (not tracked)

## Git Workflow

1. Run `git status` to see changes
2. Use `git add` to stage specific files or directories
3. Commit with descriptive messages:
   - `chore`: repository maintenance
   - `feat`: new features
   - `fix`: bug fixes
   - `refactor`: code restructuring
   - `docs`: documentation updates