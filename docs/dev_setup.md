# PROMEOS — Dev Environment Setup

## Prerequisites

- **Python 3.14+** (Windows Store or python.org)
- **Node.js 18+** (for frontend)
- **Git**

## Quick Start (PowerShell)

```powershell
# 1. Clone and enter repo
cd promeos-poc

# 2. Bootstrap (creates .venv, installs deps)
.\scripts\bootstrap.ps1

# 3. Activate venv
.\.venv\Scripts\Activate.ps1

# 4. Start backend
cd backend
uvicorn main:app --reload --port 8001

# 5. Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Manual Setup

### 1. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r backend/requirements.txt
```

> If activation fails with ExecutionPolicy error:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 2. Verify

```powershell
python -c "import sys; print(sys.executable, sys.prefix != sys.base_prefix)"
# Expected: C:\...\promeos-poc\.venv\Scripts\python.exe True
```

### 3. Run tests

```powershell
cd backend
python -m pytest tests/ -v --tb=short
```

### 4. Frontend

```powershell
cd frontend
npm install
npm run dev         # dev server
npx vite build      # production build
```

## Environment Audit (2026-03-03)

| Item | Value |
|------|-------|
| Python | 3.14.3 |
| pip | 26.0.1 |
| venv location | `.venv/` (repo root) |
| Backend deps | `backend/requirements.txt` (min floors) |
| Locked deps | `backend/requirements.lock.txt` (exact pins) |
| VS Code interpreter | `.venv\Scripts\python.exe` |
| Backend port | 8001 |
| Database | SQLite (dev), PostgreSQL (prod) |

## File Structure

```
promeos-poc/
  .venv/                  # Python virtual environment (gitignored)
  .vscode/settings.json   # VS Code config (interpreter locked to .venv)
  backend/
    requirements.txt      # Min version floors
    requirements.lock.txt # Exact pinned versions
    main.py               # FastAPI entrypoint
    tests/                # pytest
  frontend/
    src/                  # React + Vite
  scripts/
    bootstrap.ps1         # One-command setup
  docs/
    dev_setup.md          # This file
```
