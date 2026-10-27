.PHONY: test dev-frontend build-frontend deploy-backend

test:
	pytest tests -v

dev-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

deploy-backend:
	sam build && sam deploy --guided
