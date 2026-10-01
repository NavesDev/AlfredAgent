.DEFAULT_GOAL := help
SERVER := server
WEB := apps/web
# Web targets are no-ops until apps/web exists (phase 6).
WEB_RUN = $(if $(wildcard $(WEB)/package.json),cd $(WEB) &&,@true)

.PHONY: help setup dev dev-server dev-web test lint fmt gen-api build

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install server and web dependencies
	cd $(SERVER) && uv sync
	$(WEB_RUN) pnpm install

dev: ## Run server + Vite together
	$(MAKE) -j2 dev-server dev-web

dev-server: ## Run server only (voice + API)
	cd $(SERVER) && uv run python main.py

dev-web: ## Run Vite dev server only
	$(WEB_RUN) pnpm dev

test: ## Run all tests
	cd $(SERVER) && uv run pytest
	$(WEB_RUN) pnpm test --run

lint: ## Lint and type-check
	cd $(SERVER) && uv run ruff check . && uv run mypy .
	$(WEB_RUN) pnpm lint

fmt: ## Format code
	cd $(SERVER) && uv run ruff format .
	$(WEB_RUN) pnpm format

gen-api: ## Regenerate apps/web/src/api/schema.ts from FastAPI OpenAPI
	$(WEB_RUN) pnpm gen:api

build: ## Build web for FastAPI to serve
	$(WEB_RUN) pnpm build
