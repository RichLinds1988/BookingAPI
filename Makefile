.PHONY: help install run test lint format fix pre-push

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	pip install -r requirements.txt -r requirements-dev.txt

run: ## Start the API server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src

test: ## Run the test suite
	pytest

lint: ## Check code style with ruff
	ruff check .

format: ## Format code with ruff
	ruff format .

fix: ## Auto-fix lint errors and format
	ruff check --fix .
	ruff format .

pre-push: lint test ## Run lint and tests before pushing
