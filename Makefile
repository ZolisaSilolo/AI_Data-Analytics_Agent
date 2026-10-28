.PHONY: test lint verify-models smoke-agent dev-frontend build-frontend deploy-backend

test:
	pytest tests -v

lint:
	ruff check src tests scripts

verify-models:
	python scripts/verify_bedrock_access.py

smoke-agent:
	python scripts/smoke_bedrock_agent.py

dev-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

deploy-backend:
	sam build && sam deploy --guided
