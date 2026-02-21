# Quality Gate — PROMEOS CI/CD

## Overview

The quality gate runs on every PR and push to `main` via GitHub Actions.
It covers frontend (React/Vite), backend (FastAPI/Python), and E2E (Playwright).

## Pipeline Architecture

```
PR / push main
  │
  ├── Job: frontend (parallel)
  │     ├── npm ci
  │     ├── ESLint (--max-warnings=174, ratchet down)
  │     ├── Prettier --check
  │     ├── Vite build
  │     └── Vitest (980+ tests)
  │
  ├── Job: backend (parallel)
  │     ├── pip install requirements + dev
  │     ├── Ruff check (E, F, W, B rules)
  │     ├── Ruff format --check
  │     ├── Mypy (gradual mode)
  │     └── Pytest (770+ tests)
  │
  └── Job: e2e (needs: frontend + backend)
        ├── Start backend + frontend
        ├── Playwright: health, login, dashboard
        └── Upload report on failure
```

## Local Commands

| Command | What it does |
|---------|-------------|
| `make lint` | ESLint + Ruff check |
| `make format` | Prettier --write + Ruff format |
| `make format-check` | Check formatting (CI mode) |
| `make typecheck` | Mypy on backend |
| `make test` | Vitest + Pytest |
| `make build` | Vite production build |
| `make ci` | Full gate: lint + format + typecheck + test + build |
| `make e2e` | Playwright smoke tests (requires running servers) |
| `make dev` | Start backend + frontend concurrently |
| `make install` | Install all deps (npm + pip) |

## Pre-commit Hooks

Husky + lint-staged runs on every `git commit`:
- `.jsx` files: ESLint --fix + Prettier --write
- `.py` files: Ruff check --fix + Ruff format

Setup: `npm install` triggers `husky` via the `prepare` script.

## Ratcheting Strategy

### ESLint warnings
Currently capped at `--max-warnings=174` (all `no-unused-vars` + `react-hooks/exhaustive-deps`).
Reduce this number as warnings are fixed. Target: 0.

### Ruff rules
Currently: `E, F, W, B` (core errors + bugbear).
Next sprints: enable `I` (imports), `UP` (upgrades), `SIM` (simplifications).

### Mypy
Currently: gradual mode with many `disable_error_code` entries.
Reduce the ignore list as type annotations improve. Target: strict mode.

## E2E Tests

3 smoke tests in `e2e/smoke.spec.js`:
1. **Health**: API returns ok
2. **Login**: Demo credentials work and redirect
3. **Dashboard**: Renders content, no crash

Run locally:
```bash
make dev        # Terminal 1
make e2e        # Terminal 2
```

## Files

| File | Purpose |
|------|---------|
| `.github/workflows/quality-gate.yml` | CI pipeline |
| `Makefile` | Local commands |
| `backend/pyproject.toml` | Ruff + Mypy + Pytest config |
| `backend/requirements-dev.txt` | Dev dependencies |
| `frontend/.eslintrc.cjs` | ESLint config (CJS for ESLint 8) |
| `e2e/` | Playwright config + smoke tests |
| `.husky/pre-commit` | Pre-commit hook |
| `.lintstagedrc.json` | Lint-staged config |
