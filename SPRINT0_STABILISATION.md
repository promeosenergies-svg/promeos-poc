# Sprint 0 — Stabilisation du socle PROMEOS

**Date :** 2026-03-16
**Branche :** `ux/cockpit-v3`
**Commit :** `56aa4d6`

---

## 1. Résumé exécutif

Sprint 0 focalisé sur 3 chantiers de stabilisation sans modification métier :
- **Sécurité** : JWT + endpoints sensibles protégés en production
- **Migrations** : Alembic initialisé avec baseline
- **Modularisation** : api.js (1799 lignes) découpé en 11 modules domaine

**Risque** : Faible — aucune modification de logique métier, comportement dev/demo inchangé.

---

## 2. Fichiers modifiés

| Fichier | Changement | Risque |
|---------|-----------|--------|
| `backend/services/iam_service.py` | RuntimeError si JWT default + PROMEOS_ENV=production | Faible |
| `backend/main.py` | dev_tools router non enregistré en production | Faible |
| `backend/routes/demo.py` | /api/demo/seed exige require_admin() | Faible |
| `backend/routes/dev_tools.py` | Bloc 403 si PROMEOS_ENV=production | Faible |
| `backend/alembic.ini` | Config SQLite | Nul |
| `backend/alembic/env.py` | Import models + batch mode | Nul |
| `backend/alembic/versions/*.py` | Migration baseline no-op | Nul |
| `frontend/src/services/api.js` | Compatibility layer (re-export) | Faible |
| `frontend/src/services/api/*.js` | 11 modules domaine | Faible |

---

## 3. Décisions techniques

### JWT Secret
- **Avant** : Warning log si default, aucun blocage
- **Après** : `RuntimeError` si `PROMEOS_ENV=production` + secret par défaut
- **Dev/Demo** : Inchangé, le warning log subsiste

### Endpoints sensibles
| Endpoint | Avant | Après |
|----------|-------|-------|
| `/api/demo/seed` | Aucune auth | `require_admin()` obligatoire |
| `/api/demo/enable` | Aucune auth | Auth admin si PROMEOS_ENV=production |
| `/api/dev/reset_db` | DEMO_MODE check seul | + blocage si PROMEOS_ENV=production |
| Router dev_tools | Toujours enregistré | Non enregistré si PROMEOS_ENV=production |

### Alembic
- `alembic init` + config SQLite batch mode (`render_as_batch=True`)
- Migration initiale = no-op baseline (DB créée via `create_all()`)
- DB stampée : `alembic current` = `2f83c6bebc57 (head)`
- `alembic check` = clean (aucune divergence)
- `database/migrations.py` existant non modifié

### Découpage api.js
| Module | Exports | Domaine |
|--------|---------|---------|
| `api/core.js` | axios, cache, utils | Infrastructure |
| `api/auth.js` | 8 | Authentification |
| `api/patrimoine.js` | ~50 | Sites, compteurs, CRUD, geocoding |
| `api/conformite.js` | ~40 | RegOps, tertiaire, BACS |
| `api/billing.js` | ~30 | Factures, réconciliation |
| `api/purchase.js` | ~20 | Achat énergie, marché |
| `api/actions.js` | ~35 | Actions, anomalies, copilot |
| `api/energy.js` | ~45 | Consommation, EMS, monitoring |
| `api/cockpit.js` | ~25 | Dashboard, alertes, notifications |
| `api/admin.js` | ~30 | Admin, demo, KB, staging |
| `api/index.js` | re-exports | Agrégateur |

Compatibilité : `import { getSites } from '../services/api'` continue de fonctionner.

---

## 4. Tests exécutés

| Suite | Résultat |
|-------|----------|
| Backend (31 tests) | **31 passed** |
| Frontend build (Vite) | **OK (25.9s)** |
| Garde-fous Sprint 0 | **9/9 OK** |
| Lint (ruff + ESLint) | **OK** |

---

## 5. Régressions potentielles

| Risque | Probabilité | Vérification |
|--------|------------|-------------|
| Import api.js cassé quelque part | Très faible | Build Vite OK = tous les imports résolus |
| Endpoint demo bloqué en dev | Nulle | Guard uniquement si PROMEOS_ENV=production |
| Alembic conflit avec migrations.py | Nulle | Coexistence, pas de remplacement |

---

## 6. TODO Sprint 1

| # | Action | Effort | Risque si non fait |
|---|--------|--------|-------------------|
| 1 | Refactorer patrimoine.py (3000+ lignes) | L | Maintenabilité |
| 2 | Refactorer ConformitePage.jsx (2000+ lignes) | L | Maintenabilité |
| 3 | PII : cadrer stockage email/noms | S | Légal |
| 4 | Contrats de données : schémas Pydantic stricts | M | Intégrité |
| 5 | KPI formels : documenter les formules de score | M | Confiance |
| 6 | Connecteur Enedis (structure OAuth) | M | Roadmap |
| 7 | Connecteur Météo-France / Open-Meteo | S | Normalisation |
| 8 | Tests E2E Playwright ciblés | M | Régression |
| 9 | CI/CD pipeline (lint + test + build) | M | Qualité |
| 10 | Rate limiting global (pas juste par endpoint) | S | Sécurité |
