---
name: promeos-securite-production
description: >
  Expert sécurité et mise en production PROMEOS.
  RBAC, org-scoping, JWT, Docker, CI/CD,
  PostgreSQL, observabilité, checklist prod.
version: 1.0.0
tags: [securite, rbac, jwt, docker, cicd, postgres, production]
---

# Sécurité & Production — Expert PROMEOS

## 1. Authentification & Autorisation

### JWT + RBAC

```python
# Rôles PROMEOS (11 rôles métier)
# Source : backend/models/enums.py → UserRole
class UserRole(str, Enum):
    DG_OWNER = "dg_owner"              # Directeur Général / propriétaire
    DSI_ADMIN = "dsi_admin"            # Admin DSI / technique
    DAF = "daf"                        # Directeur Administratif et Financier
    ACHETEUR = "acheteur"              # Acheteur énergie
    RESP_CONFORMITE = "resp_conformite" # Responsable conformité
    ENERGY_MANAGER = "energy_manager"  # Energy Manager
    RESP_IMMOBILIER = "resp_immobilier" # Responsable immobilier
    RESP_SITE = "resp_site"            # Responsable site
    PRESTATAIRE = "prestataire"        # Prestataire externe
    AUDITEUR = "auditeur"             # Auditeur
    PMO_ACC = "pmo_acc"               # PMO / accompagnement

# Structure JWT
{
    "sub": "user_id",
    "org_id": "org_uuid",
    "roles": ["energy_manager"],
    "scopes": ["site:read", "billing:read"],
    "exp": timestamp,
    "iat": timestamp
}
```

### Org-Scoping (95-100 endpoints à sécuriser — P0 prod)

```python
# Pattern obligatoire sur TOUS les endpoints
from backend.middleware.auth import get_current_user, require_org_scope

@router.get("/api/sites")
async def list_sites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # TOUJOURS filtrer par org_id de l'utilisateur
    return db.query(Site)\
        .filter(Site.org_id == current_user.org_id)\
        .all()

# ⛔ PATTERN DANGEREUX — jamais faire :
# return db.query(Site).all()  # Expose toutes les orgs !
```

### Source Guards (vérifié par pytest)
```bash
# Test automatique : zéro endpoint sans org-scoping
python -m pytest tests/security/test_org_scoping.py -v
```

## 2. Configuration Sécurité

### Variables d'environnement obligatoires
```bash
# .env.production (JAMAIS committer)
PROMEOS_JWT_SECRET=<32 chars random>  # Crash si absent
DATABASE_URL=postgresql://...          # Postgres en prod
PROMEOS_CORS_ORIGINS=https://app.promeos.fr
DEMO_MODE=false                        # Désactiver en prod
AI_API_KEY=sk-ant-...                  # Clé Anthropic
ENEDIS_CLIENT_ID=...
ENEDIS_CLIENT_SECRET=...
```

### Checklist sécurité avant déploiement
```
[ ] PROMEOS_JWT_SECRET != "dev-secret-change-me"
[ ] DEMO_MODE=false en production
[ ] CORS_ORIGINS liste blanche (pas *)
[ ] Tous les endpoints org-scopés (grep test)
[ ] Rate limiting activé (slowapi 100 req/min)
[ ] HTTPS uniquement (pas HTTP)
[ ] Secrets hors du repo (no .env commité)
[ ] Logs sans données sensibles (PRM masqué)
[ ] Audit log activé (qui/quoi/quand)
```

## 3. Infrastructure Production

### Docker (À CRÉER — pas encore dans le repo)

> **NOTE** : Aucun fichier `docker-compose.yml` n'existe actuellement
> dans le repo. La configuration ci-dessous est la **cible de production**.

```yaml
# docker-compose.prod.yml (À CRÉER)
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - PROMEOS_JWT_SECRET=${PROMEOS_JWT_SECRET}
    ports:
      - "8001:8001"
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=promeos
      - POSTGRES_USER=promeos
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### CI/CD GitHub Actions (EXISTANT)

Le fichier `.github/workflows/quality-gate.yml` existe et couvre :
linting → pytest → vitest → playwright → build.

```yaml
# .github/workflows/quality-gate.yml (existant)
name: Quality Gate PROMEOS
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: {python-version: '3.11'}
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest tests/ -v --tb=short
      - run: cd backend && ruff check routes/ models/ services/

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: '24'}
      - run: cd frontend && npm ci
      - run: cd frontend && npx vitest run
      - run: cd frontend && npm run build
```

## 4. Base de Données Production

### État actuel : SQLite (dev) + PostgreSQL-ready (prod)

Le backend supporte les deux via `DATABASE_URL` :
- **Dev** : SQLite à `backend/data/promeos.db` (défaut)
- **Prod** : PostgreSQL via variable d'environnement

```python
# backend/database/connection.py — support dual DB
# Si DATABASE_URL commence par "postgresql://" → pool PG
# Sinon → SQLite locale
```

### Migration SQLite → PostgreSQL (Alembic)

```python
# alembic/env.py
from backend.config import settings

def run_migrations_online():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
```

```bash
# Commandes de migration
alembic revision --autogenerate -m "initial_migration"
alembic upgrade head

# Vérification idempotence
alembic downgrade -1 && alembic upgrade head
```

### Index critiques
```python
# migrations/add_critical_indexes.py
Index('ix_site_org_id', Site.org_id)
Index('ix_consumption_site_date', ConsumptionReading.site_id,
      ConsumptionReading.timestamp)
Index('ix_invoice_org_date', Invoice.org_id, Invoice.invoice_date)
Index('ix_regassessment_site', RegAssessment.site_id)
# Objectif : queries < 50ms sur 1M+ lignes
```

## 5. Observabilité

### Structured Logging (454 print() → logging)
```python
# Pattern correct partout
import logging
logger = logging.getLogger(__name__)

# ⛔ JAMAIS :
# print(f"Processing site {site_id}")

# ✅ TOUJOURS :
logger.info("Processing site", extra={
    "site_id": site_id,
    "org_id": org_id,
    "correlation_id": request.state.correlation_id
})

logger.error("Enedis SGE call failed", extra={
    "error": str(e),
    "prm": prm,
    "correlation_id": correlation_id
})
```

### Health Checks
```python
# GET /health → 200 si OK, 503 si dégradé
# GET /ready → 200 si DB OK + dépendances OK
@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))  # Test DB
    return {"status": "ready", "db": "ok"}
```

### Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.get("/api/consumption")
@limiter.limit("100/minute")
async def get_consumption(request: Request):
    ...
```

## 6. Checklist Go-Live

```
SÉCURITÉ
[ ] JWT secret fort (32+ chars) configuré
[ ] Tous endpoints org-scopés (source guard test)
[ ] CORS liste blanche configurée
[ ] Rate limiting activé
[ ] HTTPS configuré (certificat SSL)
[ ] .env hors git (.gitignore vérifié)

INFRASTRUCTURE
[ ] Docker Compose créé et testé (docker compose up)
[ ] CI/CD GitHub Actions vert
[ ] PostgreSQL migré (alembic upgrade head)
[ ] Index critiques créés (queries < 50ms)
[ ] Backup automatique DB configuré

OBSERVABILITÉ
[ ] 0 print() restant (ruff check confirme)
[ ] Logs JSON structurés avec correlation_id
[ ] /health et /ready opérationnels
[ ] Alertes monitoring configurées

QUALITÉ
[ ] Tests frontend passent (npx vitest run)
[ ] Tests backend passent (python -m pytest tests/ -v)
[ ] Source guards pass (0 calcul frontend)
[ ] Build frontend clean (0 erreur TS)
[ ] 0 DeprecationWarning datetime.utcnow()
```
