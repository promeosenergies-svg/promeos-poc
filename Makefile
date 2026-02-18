# PROMEOS Quality Gate — Makefile
# Usage: make lint | make test | make ci | make e2e | make dev

SHELL := bash
.DEFAULT_GOAL := help
BACKEND := backend
FRONTEND := frontend
VENV := $(BACKEND)/venv/Scripts

# ── Lint ──────────────────────────────────────────────────────────────────────

.PHONY: lint lint-front lint-back
lint: lint-front lint-back ## Lint front + back

lint-front:
	npm run lint --prefix $(FRONTEND)

lint-back:
	$(VENV)/ruff check $(BACKEND) --config $(BACKEND)/pyproject.toml

# ── Format ────────────────────────────────────────────────────────────────────

.PHONY: format format-check
format: ## Auto-format front + back
	npm run format --prefix $(FRONTEND)
	$(VENV)/ruff format $(BACKEND) --config $(BACKEND)/pyproject.toml

format-check: ## Check formatting (CI)
	npm run format:check --prefix $(FRONTEND)
	$(VENV)/ruff format --check $(BACKEND) --config $(BACKEND)/pyproject.toml

# ── Typecheck ─────────────────────────────────────────────────────────────────

.PHONY: typecheck
typecheck: ## Mypy on backend (gradual)
	$(VENV)/python -m mypy $(BACKEND) --config-file $(BACKEND)/pyproject.toml

# ── Tests ─────────────────────────────────────────────────────────────────────

.PHONY: test test-front test-back
test: test-front test-back ## Run all unit tests

test-front:
	npm test --prefix $(FRONTEND)

test-back:
	cd $(BACKEND) && $(CURDIR)/$(VENV)/python -m pytest tests/ -x -q

# ── Build ─────────────────────────────────────────────────────────────────────

.PHONY: build
build: ## Vite production build
	npm run build --prefix $(FRONTEND)

# ── E2E ───────────────────────────────────────────────────────────────────────

.PHONY: e2e
e2e: ## Playwright smoke tests (requires running servers)
	cd e2e && npx playwright test

# ── CI gate (local) ──────────────────────────────────────────────────────────

.PHONY: ci
ci: lint format-check typecheck test build ## Full CI gate (local)
	@echo "✅ Quality gate passed"

# ── Dev ───────────────────────────────────────────────────────────────────────

.PHONY: dev
dev: ## Start backend + frontend (concurrent)
	npx concurrently -n BE,FE -c blue,green \
		"cd $(BACKEND) && venv/Scripts/python main.py" \
		"wait-on http://127.0.0.1:8000/api/health && npm run dev --prefix $(FRONTEND)"

# ── Install ───────────────────────────────────────────────────────────────────

.PHONY: install
install: ## Install all dependencies
	npm ci
	cd $(FRONTEND) && npm ci
	cd $(BACKEND) && venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
