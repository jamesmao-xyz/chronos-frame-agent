# ==============================================================================
# Chronos Frame Agent - Developer Makefile
# ==============================================================================

.PHONY: help install setup dev lint lint-fix format test check run docker-build clean pre-commit

.DEFAULT_GOAL := help

UV := uv
PYTHON := python3

help: ## Show this help message and exit
	@echo ""
	@echo "Chronos Frame Agent - Developer Workflow Commands"
	@echo "=================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""

install: ## Install production and development dependencies using uv
	@echo "Installing project dependencies..."
	$(UV) sync --extra lint --extra eval

setup: install ## Full developer setup: install dependencies and activate pre-commit hooks
	@echo "Installing and activating git pre-commit hooks..."
	$(UV) run pre-commit install
	@echo "✓ Setup complete! Pre-commit hooks are now active for all git commits."

pre-commit: ## Run pre-commit hooks across all files
	@echo "Running pre-commit hooks..."
	$(UV) run pre-commit run --all-files

lint: ## Run linting and code quality checks (ruff check, ruff format check, codespell)
	@echo "Running code quality checks..."
	$(UV) run --extra lint ruff check .
	$(UV) run --extra lint ruff format . --check
	$(UV) run --extra lint codespell

lint-fix: ## Automatically fix lint and formatting errors
	@echo "Auto-fixing formatting and lint issues..."
	$(UV) run --extra lint ruff check --fix .
	$(UV) run --extra lint ruff format .

format: lint-fix ## Alias for lint-fix

test: ## Run unit and integration tests with pytest
	@echo "Running test suite..."
	$(UV) run pytest tests/ -v

run: ## Start the smart frame runner and SSE web server locally
	@echo "Starting Chronos Frame Agent locally..."
	$(UV) run python run_loop.py

docker-build: ## Build the production Docker container image
	@echo "Building production Docker container..."
	docker build -t chronos-frame-agent:latest .

clean: ## Remove temporary caches, build artifacts, and test files
	@echo "Cleaning up temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov dist build *.egg-info .ty
	@echo "✓ Clean complete."
