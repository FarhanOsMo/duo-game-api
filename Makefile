# Convenience targets. GNU make is optional: every target is a plain command
# listed in the README (with PowerShell equivalents) for machines without make.

PYTHON ?= python
COMPOSE ?= docker compose
GIT_SHA ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
export GIT_SHA

.PHONY: help install run test lint format typecheck validate manifest check audit \
        up up-staging up-prod down logs smoke traffic loadtest pdf

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install runtime and dev dependencies
	$(PYTHON) -m pip install -r requirements-dev.txt

run: ## Run the API locally without Docker (auto-reload)
	$(PYTHON) -m uvicorn app.main:app --reload

test: ## Run tests with the coverage gate
	$(PYTHON) -m pytest --cov --cov-report=term

lint: ## Lint and check formatting
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format: ## Apply formatting and safe lint fixes
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

typecheck: ## Static type check (strict)
	$(PYTHON) -m mypy app scripts tests

validate: ## Validate the game data
	$(PYTHON) scripts/validate_data.py

manifest: ## Regenerate data/manifest.json
	$(PYTHON) scripts/build_manifest.py

audit: ## Check dependencies for known vulnerabilities
	$(PYTHON) -m pip_audit -r requirements.txt -r requirements-dev.txt

check: lint typecheck validate test ## Everything CI runs before building the image
	$(PYTHON) scripts/build_manifest.py --check

up: ## Start the dev stack (api, prometheus, grafana)
	$(COMPOSE) up -d --build

up-staging: ## Start the stack with staging configuration
	$(COMPOSE) -f docker-compose.yml -f compose.staging.yml up -d --build

up-prod: ## Start a released image with prod-like configuration (set API_IMAGE)
	$(COMPOSE) -f docker-compose.yml -f compose.prod.yml up -d --no-build

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Follow API logs
	$(COMPOSE) logs -f api

smoke: ## Smoke test the running stack
	$(PYTHON) scripts/smoke_test.py

traffic: ## Send 60s of realistic traffic for the dashboard
	$(PYTHON) scripts/generate_traffic.py --duration 60

loadtest: ## Run the Locust load test against the running stack
	$(PYTHON) -m locust -f loadtest/locustfile.py --headless --host http://localhost:8000 \
		--users 50 --spawn-rate 10 --run-time 60s --csv loadtest/results/run --only-summary

pdf: ## Build Mohamed_Farhan_Portfolio.pdf
	$(PYTHON) scripts/build_pdf.py
