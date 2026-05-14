# PROMEOS V4 · Checklist Sprint M2-1 Foundation infra

> Version : v1.0 · 2026-05-14
> Sprint : M2-1 Foundation infra (Mois 2 J+1 à J+3)
> Source : L9 §2 Sprint M2-1 + L7 §3 enums + ADR-027 §9 CI workflow
> Audience : opérateur Sprint M2-1 (Amine ou backup operator)
> Durée estimée : ~2 jours/h (16h ouvrées)

---

## 0. Préambule

**Avant de commencer Sprint M2-1**, vérifier que :

- [ ] Mois 1 docs only est mergé sur `main` ou conservé sur `claude/refonte-sol2` (à votre convenance)
- [ ] Branche de travail créée : `git checkout -b m2-sprint-1-foundation-infra`
- [ ] Dernier commit Mois 1 récupéré localement : `git log --oneline | head -1` montre `docs(action-center-l9): Month 2 backend pilot manual + Month 1 final synthesis`
- [ ] **Pas de modification du code Mois 1** : les 8 livrables (doctrine + L1 + 5 ADR + L7 + L8 + L9) sont intouchables sauf nouvel avenant doctrinal
- [ ] Pratiques cardinales L9 §9.1 lues : MCPs obligatoires · Phase 0 si >100 LoC · commits atomiques · DoD binaire · STOP GATE

**Objectif Sprint M2-1** : préparer le terrain (CI + dépendances + structure répertoires + 4 premiers source-guards anti-régression) pour les sprints suivants. Pas encore de code métier — juste infrastructure technique.

---

## 1. Day 1 — Setup CI + dépendances (J+1)

### 1.1 Setup CI complète (cardinal · ~3h)

Créer ou compléter `.github/workflows/ci.yml` :

```yaml
name: CI Backend
on:
  push:
    branches: [m2-sprint-*, main]
  pull_request:
    branches: [main]

jobs:
  bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install bandit
      - name: Bandit SAST
        run: bandit -r backend/ -lll -ii -f json -o bandit-report.json

  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: |
            p/security-audit
            p/owasp-top-ten

  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install pip-audit
      - name: Audit dependencies
        run: pip-audit --strict --desc -r requirements.txt

  source-guards:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install pytest -r requirements.txt
      - name: Run source-guards
        run: pytest tests/source_guards/ -v --tb=short
```

**Checklist** :

- [ ] Fichier `.github/workflows/ci.yml` créé/édité avec les 5 jobs
- [ ] Premier push déclenche les jobs (vérifier sur GitHub Actions)
- [ ] Bandit job : passing (peut-être 0 finding au début, c'est OK)
- [ ] Semgrep job : passing
- [ ] gitleaks job : passing (aucun secret détecté)
- [ ] pip-audit job : passing (0 CVE high)
- [ ] source-guards job : passing (vide pour l'instant, c'est OK · Sprint M2-1 ajoute les 4 premiers)

**Garde-fou** : ces 5 jobs doivent **bloquer les PR** sur `main` (configurer dans Settings → Branches → Branch protection rules).

### 1.2 `.gitignore` final (cardinal · ~30 min)

Éditer `.gitignore` à la racine du repo :

```gitignore
# ─── Python ───
__pycache__/
*.py[cod]
*.so
.Python
venv/
.venv/
env/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# ─── Node.js / Frontend ───
node_modules/
dist/
build/
.next/
.cache/
*.log

# ─── IDE ───
.vscode/
.idea/
*.swp
.DS_Store

# ─── PROMEOS V4 cardinal (IS10 + IE1 + I9) ───
# Backups hors Git (ADR-026 I9 + ADR-027 IS10)
/backups/
*.backup
*.sql
**/legacy_json/
promeos.db
promeos.db-journal
promeos_staging.db

# Evidences storage hors Git (ADR-029 IE1)
/data/promeos/evidences/

# Receipts sanitizés autorisés (ADR-026 §3.2)
!docs/migrations/L3_cutover_receipts/RECEIPT_*.md
!docs/migrations/L8_suppression_receipts/RECEIPT_*.md

# ─── Secrets ───
.env
.env.local
.env.*.local
*.pem
*.key
secrets/

# ─── Logs ops ───
*.log
logs/
```

**Checklist** :

- [ ] `.gitignore` créé/édité
- [ ] `git status` ne montre AUCUN fichier `*.backup`, `*.sql`, `evidences/`
- [ ] Test : créer un fichier `touch test.backup` → `git status` ne le voit pas
- [ ] Commit du `.gitignore` : `git add .gitignore && git commit -m "chore(m2-1): gitignore strict for backups + evidences + secrets (IS10 + IE1)"`

### 1.3 Dépendances Python (cardinal · ~1h)

Éditer `requirements.txt` (ou pyproject.toml selon votre stack) :

```
# Core
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.30
alembic==1.13.0
pydantic==2.7.0
pydantic-settings==2.3.0

# Sécurité (ADR-027)
python-jose[cryptography]==3.3.0  # JWT
passlib[bcrypt]==1.7.4              # password hashing

# Evidence + audit trail (ADR-029)
python-magic==0.4.27                 # IE9 magic bytes MIME
structlog==24.1.0                    # IS7-IS9 logs sanitisés

# Scheduling (Q17 + ADR-028 + ADR-029)
apscheduler==3.10.4                  # IL8 + IE5 purge mensuelle

# Tests
pytest==8.2.0
pytest-asyncio==0.23.0
pytest-cov==5.0.0
httpx==0.27.0                        # tests FastAPI

# Optionnel (utile mais pas cardinal)
slowapi==0.1.9                       # rate limiting (M8 ADR-027)
```

**Checklist** :

- [ ] `requirements.txt` édité
- [ ] `pip install -r requirements.txt` réussit (venv recommandé)
- [ ] `pip-audit` local : 0 CVE high
- [ ] `python -c "import magic; print(magic.__version__)"` réussit (test libmagic)
- [ ] **Important** : `libmagic1` installé au niveau OS (`apt-get install libmagic1` sur Ubuntu) — sinon `python-magic` casse
- [ ] Commit : `git add requirements.txt && git commit -m "chore(m2-1): pin dependencies for V4 backend (FastAPI, Pydantic v2, python-magic, structlog, apscheduler)"`

### 1.4 Variables d'environnement (~1h)

Créer `.env.example` (commitable) :

```bash
# ─── Environment ───
ENV=development
DEBUG=True

# ─── Database ───
DATABASE_URL=sqlite:///./promeos.db
# Migration future PostgreSQL :
# DATABASE_URL=postgresql://user:password@localhost:5432/promeos_v4

# ─── JWT (ADR-027 §3.3) ───
JWT_SECRET_KEY=changeme_secret_min_32_chars_random
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60       # 1h
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30         # 30j
JWT_ADMIN_FRESH_TOKEN_MAX_AGE_SECONDS=300  # 5min (IS5 + IL3)

# ─── Evidence storage (ADR-029 IE1) ───
EVIDENCE_STORAGE_BACKEND=filesystem
EVIDENCE_FS_ROOT=/data/promeos/evidences
EVIDENCE_MAX_SIZE_BYTES=10485760         # 10 MB (Q45-B)

# ─── Retention purge (ADR-029 IE5) ───
RETENTION_PURGE_ENABLED=False            # OFF Mois 2-3 (triple garde-fou)
RETENTION_PURGE_DRY_RUN_FIRST=True       # Default dry-run

# ─── Logging (ADR-027 IS7-IS9) ───
LOG_LEVEL=INFO
LOG_FORMAT=json                          # structlog JSON output

# ─── CORS ───
CORS_ALLOW_ORIGINS=http://localhost:3000

# ─── Feature flags Mois 2-3 ───
FEATURE_FLAG_V4_ENABLED=False            # Cutover Mois 4 J0 activation
```

**Checklist** :

- [ ] `.env.example` créé et commité
- [ ] `.env` local créé (ne pas committer ! Vérifier `.gitignore`)
- [ ] Test : `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.environ['JWT_SECRET_KEY'])"` réussit
- [ ] Commit : `git add .env.example && git commit -m "chore(m2-1): document required environment variables (.env.example)"`

---

## 2. Day 2 — Structure répertoires + 4 source-guards (J+2)

### 2.1 Structure répertoires backend (cardinal · ~1h)

Créer la structure cible Mois 2 :

```
backend/
├── __init__.py
├── main.py                         # FastAPI app entry point (Sprint M2-3)
├── config/
│   ├── __init__.py
│   ├── settings.py                  # Pydantic Settings depuis .env
│   └── constants.py                 # Constantes business (ADEME, CO2, etc.)
├── models/                          # SQLAlchemy (Sprint M2-2)
│   ├── __init__.py
│   └── enums/
│       └── __init__.py              # 9 enums Python (L7 §3)
├── schemas/                         # Pydantic (Sprint M2-2)
│   ├── __init__.py
│   └── event_payloads/              # 16 schemas v1 (Sprint M2-6)
│       └── __init__.py
├── api/
│   ├── __init__.py
│   └── action_center/               # 12 endpoints (Sprint M2-4)
│       └── __init__.py
├── services/
│   ├── __init__.py
│   ├── lifecycle/                   # State machine (Sprint M2-5)
│   │   └── __init__.py
│   ├── evidence/                    # Storage + validation (Sprint M2-6)
│   │   └── __init__.py
│   └── event_log/                   # Writer (Sprint M2-6)
│       └── __init__.py
├── repositories/                    # Pattern repository org-scopé (Sprint M2-3+)
│   └── __init__.py
├── middleware/                      # OrgScopingMiddleware (Sprint M2-3)
│   └── __init__.py
├── decorators/                      # @org_scoped (Sprint M2-3)
│   └── __init__.py
├── auth/                            # JWT + cookies (Sprint M2-3)
│   └── __init__.py
├── logging/                         # structlog config (Sprint M2-3)
│   └── __init__.py
├── maintenance/                     # Purge mensuelle (Sprint M2-6)
│   └── __init__.py
└── db.py                            # SQLAlchemy session factory

tests/
├── __init__.py
├── conftest.py                      # Fixtures pytest
├── unit/
│   ├── __init__.py
│   └── lifecycle/                   # Sprint M2-5
│       └── __init__.py
├── integration/
│   └── __init__.py
├── contract/                        # Sprint M2-8
│   └── __init__.py
├── source_guards/                   # 50 SG (sprints M2-1 à M2-8)
│   └── __init__.py
└── perf/                            # Benchmarks (Sprint M2-8)
    └── __init__.py
```

**Checklist** :

- [ ] Structure créée via `mkdir -p` + `touch __init__.py`
- [ ] `tree backend tests` ressemble au schéma ci-dessus
- [ ] Commit : `git add backend/ tests/ && git commit -m "chore(m2-1): scaffold backend + tests directory structure (per L7 §2 + L9 §2)"`

### 2.2 Setup structlog + configuration logging (~1h)

Créer `backend/logging/__init__.py` :

```python
"""
Structured logging config (ADR-027 IS7-IS9 · ADR-029 §10).

Invariants :
- IS7 : logs sans body, query string sensible, ni token
- IS8 : IP anonymisée /24 IPv4 /48 IPv6
- IS9 : correlation_id obligatoire
"""
import structlog
import ipaddress
from typing import Any

def configure_logging(log_level: str = "INFO"):
    """Configure structlog avec sanitization par défaut."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )


def anonymize_ip(ip: str) -> str:
    """
    IS8 : anonymisation IP RGPD CNIL.
    IPv4 : /24 mask · IPv6 : /48 mask
    """
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv4Address):
            return str(ipaddress.IPv4Network(f"{ip}/24", strict=False).network_address)
        else:
            return str(ipaddress.IPv6Network(f"{ip}/48", strict=False).network_address)
    except ValueError:
        return "unknown"
```

**Checklist** :

- [ ] `backend/logging/__init__.py` créé
- [ ] Test rapide : `python -c "from backend.logging import configure_logging, anonymize_ip; configure_logging(); print(anonymize_ip('192.168.1.42'))"` → `192.168.1.0`
- [ ] Commit : `git add backend/logging/ && git commit -m "chore(m2-1): structlog config + anonymize_ip helper (IS7-IS9)"`

### 2.3 4 premiers source-guards anti-régression (cardinal · ~3h)

Créer `tests/source_guards/test_legacy_anti_regression.py` :

```python
"""
4 source-guards Sprint M2-1.

Objectif : empêcher toute régression vers le code legacy supprimé Mois 5.
Active dès Sprint M2-1, même avant que le code backend V4 soit écrit.
"""
import re
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).parent.parent.parent / "backend"
FRONTEND_ROOT = Path(__file__).parent.parent.parent / "frontend" / "src"


def _grep_files(root: Path, pattern: str, extensions: tuple = (".py",)) -> list[Path]:
    """Helper grep récursif."""
    if not root.exists():
        return []
    matches = []
    for ext in extensions:
        for f in root.rglob(f"*{ext}"):
            try:
                content = f.read_text()
                if re.search(pattern, content):
                    matches.append(f)
            except (UnicodeDecodeError, PermissionError):
                continue
    return matches


def test_no_action_legacy_imports():
    """SG-1 : aucun import de models legacy (anti-régression Mois 5)."""
    forbidden_patterns = [
        r"from backend\.models\.action_legacy import",
        r"from backend\.models\.anomaly_legacy import",
        r"import backend\.models\.action_legacy",
    ]
    for pattern in forbidden_patterns:
        matches = _grep_files(BACKEND_ROOT, pattern)
        assert not matches, f"Legacy import found: {pattern} in {matches}"


def test_no_anomaly_legacy_imports():
    """SG-2 : aucun import direct AnomalyEvent / ActionPlanItem / BillAnomaly."""
    forbidden_patterns = [
        r"from\s+\S+\s+import\s+AnomalyEvent",
        r"from\s+\S+\s+import\s+ActionPlanItem",
        r"from\s+\S+\s+import\s+BillAnomaly",
    ]
    for pattern in forbidden_patterns:
        matches = _grep_files(BACKEND_ROOT, pattern)
        assert not matches, f"Legacy class import: {pattern} in {matches}"


def test_gitignore_excludes_backups():
    """SG-3 : .gitignore exclut /backups/, *.backup, *.sql (IS10 + I9)."""
    gitignore_path = Path(__file__).parent.parent.parent / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist at repo root"
    content = gitignore_path.read_text()
    required_patterns = ["/backups/", "*.backup", "*.sql"]
    for pattern in required_patterns:
        assert pattern in content, f"Missing in .gitignore: {pattern}"


def test_gitignore_excludes_evidences():
    """SG-4 : .gitignore exclut /data/promeos/evidences/ (IE1)."""
    gitignore_path = Path(__file__).parent.parent.parent / ".gitignore"
    content = gitignore_path.read_text()
    assert "/data/promeos/evidences/" in content, (
        "Missing in .gitignore: /data/promeos/evidences/"
    )
```

**Checklist** :

- [ ] Fichier créé
- [ ] `pytest tests/source_guards/test_legacy_anti_regression.py -v` : **4/4 PASSED**
- [ ] Si **1 échec** → c'est probablement `.gitignore` incomplet (corriger §1.2)
- [ ] Push branch · vérifier que CI déclenche le job `source-guards` et qu'il passe
- [ ] Commit : `git add tests/source_guards/ && git commit -m "test(m2-1): 4 source-guards anti-régression legacy (SG-1 à SG-4)"`

---

## 3. Day 3 — Pydantic Settings + commit final Sprint (J+3)

### 3.1 Pydantic Settings (~2h)

Créer `backend/config/settings.py` :

```python
"""
Pydantic Settings depuis .env (cohérent ADR-025 + ADR-027 + ADR-029).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./promeos.db"

    # JWT (ADR-027)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ADMIN_FRESH_TOKEN_MAX_AGE_SECONDS: int = 300

    # Evidence storage (ADR-029 IE1)
    EVIDENCE_STORAGE_BACKEND: Literal["filesystem", "s3"] = "filesystem"
    EVIDENCE_FS_ROOT: str = "/data/promeos/evidences"
    EVIDENCE_MAX_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB (Q45-B)

    # Retention purge (ADR-029 IE5)
    RETENTION_PURGE_ENABLED: bool = False
    RETENTION_PURGE_DRY_RUN_FIRST: bool = True

    # Logging (ADR-027 IS7-IS9)
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = ["http://localhost:3000"]

    # Feature flags Mois 2-3
    FEATURE_FLAG_V4_ENABLED: bool = False


settings = Settings()  # singleton
```

**Checklist** :

- [ ] Fichier créé
- [ ] Test : `python -c "from backend.config.settings import settings; print(settings.EVIDENCE_MAX_SIZE_BYTES)"` → `10485760`
- [ ] Si erreur "JWT_SECRET_KEY missing" → vérifier que `.env` local existe avec cette variable
- [ ] Commit : `git add backend/config/ && git commit -m "chore(m2-1): Pydantic Settings from .env (cohérent ADR-025/027/029)"`

### 3.2 Vérifications finales Sprint M2-1 (cardinal · ~2h)

```bash
# 1. Tous les source-guards passent
pytest tests/source_guards/ -v
# Doit être : 4/4 PASSED

# 2. CI workflow déclenche correctement
git push origin m2-sprint-1-foundation-infra
# Vérifier sur GitHub Actions : 5 jobs verts (bandit + semgrep + gitleaks + pip-audit + source-guards)

# 3. Pas de secrets exposés
gitleaks detect --no-git
# Doit être : 0 leaks

# 4. Dépendances saines
pip-audit --strict
# Doit être : 0 CVE high

# 5. Bandit local
bandit -r backend/ -lll -ii
# Doit être : 0 high severity findings

# 6. Structure répertoires
tree backend tests -L 3
# Vérifier que tous les __init__.py sont présents

# 7. Aucune régression legacy possible
grep -r "from backend.models.action_legacy" backend/  # vide
grep -r "AnomalyEvent\|ActionPlanItem\|BillAnomaly" backend/  # vide

# 8. Variables env documentées
cat .env.example  # Toutes les variables présentes
```

---

## 4. DoD binaire Sprint M2-1 (tous obligatoires)

Avant de **merger** la branche `m2-sprint-1-foundation-infra` :

- [ ] **CI 4 outils** Bandit + Semgrep + gitleaks + pip-audit : 4/4 jobs verts
- [ ] **CI source-guards** : 4/4 SG passing (SG-1 à SG-4)
- [ ] **`.gitignore`** strict : `/backups/`, `*.backup`, `*.sql`, `/data/promeos/evidences/`, `.env`
- [ ] **`requirements.txt`** pinned : FastAPI, Pydantic v2, python-magic, structlog, apscheduler
- [ ] **`libmagic1`** installé au niveau OS
- [ ] **`.env.example`** committé avec toutes les variables documentées
- [ ] **`.env`** local créé (non-committé) avec valeurs réelles
- [ ] **Structure répertoires** backend/tests créée
- [ ] **`backend/logging/`** : `configure_logging()` + `anonymize_ip()` opérationnels
- [ ] **`backend/config/settings.py`** : Pydantic Settings depuis .env
- [ ] **Aucune régression legacy** possible (grep checks vides)
- [ ] **Branch protection** GitHub : 5 jobs CI bloquant sur main
- [ ] **Commits atomiques** : au moins 6 commits propres (gitignore + deps + env + structure + logging + source-guards)
- [ ] **PR description** : reference L9 §2 Sprint M2-1 + DoD checklist cochée

---

## 5. Communication fin Sprint M2-1

### 5.1 Message Slack/équipe

```
✅ Sprint M2-1 Foundation infra terminé · Mois 2 lancé

Date début : <DATE J+1>
Date fin : <DATE J+3>
Durée réelle : <N> jours/h
Operator : Amine

Livré :
  ✓ CI complète (Bandit + Semgrep + gitleaks + pip-audit + source-guards)
  ✓ .gitignore strict (IS10 + IE1 + I9)
  ✓ Dépendances pinnées (FastAPI, Pydantic v2, python-magic, structlog, apscheduler)
  ✓ Variables env documentées
  ✓ Structure backend + tests
  ✓ 4 source-guards anti-régression actifs (SG-1 à SG-4)
  ✓ structlog + anonymize_ip helper
  ✓ Pydantic Settings

Prochaine étape : Sprint M2-2 Schéma DB V4 + Alembic migration (J+4 à J+6)
```

### 5.2 Tag git

```bash
git tag -a m2-sprint-1-done -m "Sprint M2-1 Foundation infra · DoD 13/13 ✓"
git push origin m2-sprint-1-done
```

---

## 6. Préparation Sprint M2-2

Avant de démarrer Sprint M2-2 :

- [ ] Sprint M2-1 mergé sur `main` (ou conservé sur branche selon Git flow)
- [ ] CI 100% verte sur `main`
- [ ] Annonce équipe envoyée
- [ ] Tag `m2-sprint-1-done` poussé
- [ ] Relire L9 §2 Sprint M2-2 + ADR-025 §2 (schéma DB V4) + L7 §2 (tables détaillées)
- [ ] Créer nouvelle branche : `git checkout -b m2-sprint-2-schema-db`

---

## 7. Risques Sprint M2-1 à surveiller

Cf. **`M1-RISKS-CONSOLIDATED.md`** :

- R0-4 (commit accidentel backup) — surveillance via gitleaks CI
- R2-3 (pip-audit CVE) — surveillance continue
- R1-5 (dépassement délai sprint) — buffer 1 jour si nécessaire

---

## 8. Hors-scope Sprint M2-1 (PAS faire)

❌ Créer des modèles SQLAlchemy (Sprint M2-2)
❌ Créer des migrations Alembic (Sprint M2-2)
❌ Implémenter OrgScopingMiddleware (Sprint M2-3)
❌ Créer des endpoints (Sprint M2-4)
❌ Implémenter state machine (Sprint M2-5)
❌ Implémenter evidence storage (Sprint M2-6)
❌ Seed HELIOS data (Sprint M2-7)
❌ Modifier les ADR ou la doctrine (figés)
❌ Lancer la suppression legacy (Mois 5 · L8)

---

**Fin checklist Sprint M2-1.** Une fois mergé, démarrer Sprint M2-2 selon L9 §2.
