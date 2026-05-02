# Conventions de développement HELIOS / Promeos

Référence stable. L'état du repo prime sur ce document si conflit.

## Stack actif

- Backend : FastAPI, Python 3.11, SQLAlchemy, SQLite (PostgreSQL-ready)
- Frontend : React 18, Vite, Tailwind v4, Recharts (JS pur, .jsx)
- Tests : pytest (~6 027 tests), Vitest
- Migrations : `backend/database/migrations.py` custom (pas Alembic)
- Outillage : Claude Code + MCP Context7/code-review/simplify (obligatoires)

## Cibles futures (non actives)

- Postgres / Supabase : préparé via SQLAlchemy, migration quand prod multi-tenant
- Alembic : à évaluer si complexité dépasse le custom actuel
- TypeScript : non prévu court terme

## Paths canoniques

- `backend/doctrine/constants.py` — constantes inviolables
- `backend/config/tarifs_reglementaires.yaml` — SoT tarifs
- `backend/regops/` — conformité (DT, BACS, APER, audit SMÉ)
- `backend/services/billing_*` — Bill Intelligence / shadow billing
- `backend/services/consumption_unified_service.py` — SoT consommation
- `backend/tests/test_*_source_guards.py` — tests SG anti-régression (pattern flat)
- `tests/doctrine/` — tests doctrine pre-commit hook

## Modèle Claude Code par défaut

- Opus 4.7 + `/effort xhigh` : régulatoire, architecture, `backend/doctrine/`, `backend/regops/`, `backend/services/billing_*`
- Sonnet 4.6 : tests, UI Recharts, refactos sans risque métier
- Haiku 4.5 : classifications côté API HELIOS (pas dev Claude Code)

## Conventions absolues

- Audit AVANT fix (doctrine 13 principes)
- Commits atomiques format `fix(module-pN): Phase X.Y — description`
- Constantes régulatoires : flux exclusif via `backend/doctrine/constants.py`
- MCP obligatoires : Context7 + code-review + simplify
- Langue : produit FR (UI, doctrine), technique EN (code, commits)
- Nomenclature : "Marché de gros" pas "Post-ARENH" ; "NEBCO" pas "NEBEF"

## Règle SG_NAV_FE_01 — extension à étudier

- ✅ bloque constantes physiques hardcoded (0.052, 0.227, etc.)
- ⚠️ ne bloque pas labels d'unité ("€", "kWh", "kWh/m²") encore en dur dans certains composants
- TODO : décider si labels passent par `frontend/src/constants/units.js` centralisé

## Fichiers protégés (validation explicite avant édition)

- `backend/database/migrations.py`
- `backend/doctrine/constants.py`
- `backend/config/tarifs_reglementaires.yaml`
- `backend/services/consumption_unified_service.py`
- `backend/tests/test_*_source_guards.py`
- `tests/doctrine/`

## Filtres pytest utiles

- `pytest backend/tests/ -k source_guards -x -q` — tous les SG
- `pytest tests/doctrine/ -x -q` — doctrine
- `pytest -x -q` — non-régression complète (~6 027 tests, doit être vert avant phase suivante)
- Tous les filtres assument **cwd = racine du repo** (depuis `backend/`, retirer le préfixe `backend/`).
