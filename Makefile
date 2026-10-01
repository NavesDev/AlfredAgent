.DEFAULT_GOAL := help
SERVER := server
WEB := apps/web

.PHONY: help setup dev dev-server dev-web test lint fmt gen-api build

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install server and web dependencies
	cd $(SERVER) && uv sync
	cd $(WEB) && pnpm install

dev: ## Run server + Vite together
	$(MAKE) -j2 dev-server dev-web

dev-server: ## Run server only (voice + API)
	cd $(SERVER) && uv run python main.py

dev-web: ## Run Vite dev server only
	cd $(WEB) && pnpm dev

test: ## Run all tests
	cd $(SERVER) && uv run pytest
	cd $(WEB) && pnpm test --run

lint: ## Lint and type-check
	cd $(SERVER) && uv run ruff check . && uv run mypy .
	cd $(WEB) && pnpm lint

fmt: ## Format code
	cd $(SERVER) && uv run ruff format .
	cd $(WEB) && pnpm format

gen-api: ## Regenerate apps/web/src/api/schema.ts from FastAPI OpenAPI
	cd $(WEB) && pnpm gen:api

build: ## Build web for FastAPI to serve
	cd $(WEB) && pnpm build
