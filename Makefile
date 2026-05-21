.PHONY: help install run test lint format fix pre-push

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	py -m pip install -r requirements.txt -r requirements-dev.txt

run: ## Start the API server
	cd src && py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run database migrations
	py -m alembic -c migrations/alembic.ini upgrade head

test: ## Run the test suite
	py -m pytest

lint: ## Check code style with ruff
	py -m ruff check .

format: ## Format code with ruff
	py -m ruff format .

fix: ## Auto-fix lint errors and format
	py -m ruff check --fix .
	py -m ruff format .

pre-push: lint test ## Run lint and tests before pushing
