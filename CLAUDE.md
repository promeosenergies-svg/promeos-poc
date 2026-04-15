# CLAUDE.md — Contexte PROMEOS pour Claude Code

Ce fichier est charge automatiquement a chaque session Claude Code.

## Skill PROMEOS obligatoire

Lis `SKILL.md` a la racine AVANT toute action sur ce repo.
Toutes les regles non-negociables y sont encodees.
Skills detailles dans `.claude/skills/` (11 skills domaine).

## Workframe & boundaries

Read and enforce the rules in `docs/dev/workframe-contract.md` before
creating or moving files. Personal material never enters this repo —
it lives in `../workspace/personal/<person>/` outside the git boundary.
The merge process, commit message discipline, and wait-for-eyes zones
are defined there. Do not create `docs/drafts/` or `docs/notes/` folders
for informal sharing — use GitHub Draft PRs instead.

## Stack technique

- Backend : Python 3.11 / FastAPI / SQLAlchemy / SQLite (PostgreSQL-ready)
- Frontend : React 18 / Vite / Tailwind CSS v4 / Recharts / Lucide React
- Tests : pytest (BE) / Vitest (FE) / Playwright (E2E)
- Repo : github.com/promeosenergies-svg/promeos-poc
- Port backend : **8001** (pas 8000 ni 8080)
- Port frontend : **5173** (proxy -> localhost:8001)

## Regle d'or — ZERO calcul metier frontend

Le frontend est affichage uniquement. Voir SKILL.md section "Regle absolue".

## Workflow obligatoire

1. Phase 0 read-only : grep/find/cat uniquement — bilan avant toute modif
2. Zero modif sans bilan Phase 0 valide
3. Tests avant ET apres chaque phase
4. Commit atomique par phase avec message normalise

## Fichiers critiques (audit avant modification)

- backend/regops/scoring.py — source de verite scoring conformite
- backend/services/consumption_unified_service.py — source de verite conso
- backend/config/emission_factors.py — constantes CO2 canoniques
- backend/config/tarifs_reglementaires.yaml — tarifs versionnes
- backend/utils/naf_resolver.py — resolution NAF (ne pas dupliquer)
- backend/services/demo_seed/orchestrator.py — seed orchestration
- backend/services/compliance_score_service.py — scoring conformite

## Commandes de reference

```bash
# Backend
cd backend && python main.py                        # -> http://localhost:8001
cd backend && python -m pytest tests/ -v --tb=short # tests backend

# Frontend
cd frontend && npm run dev                           # -> http://localhost:5173
cd frontend && npx vitest run                        # tests frontend

# Source guards (regles architecture)
cd backend && python -m pytest tests/source_guards/ -v

# Seed demo
cd backend && python -m services.demo_seed --pack helios --size S --reset

# Full stack
npm run dev:full                                     # depuis la racine

# Skills
npx skills list                                      # tous les skills installes
```

## Workflow obligatoire pre-merge

1. `/code-review:code-review` — bugs, secu, qualite
2. `/simplify` — refactoring, clarte
3. Tests FE >= 3 783, BE >= 843, zero regression
4. Playwright audit screenshots si modification UI

## Architecture hierarchique

Organisation -> EntiteJuridique -> Portefeuille -> Site -> Batiment -> Compteur -> DeliveryPoint

## Skills installes

### Skills domaine (.claude/skills/) :
- promeos-regulatory — conformite DT/BACS/APER/AUDIT
- promeos-billing — shadow billing, TURPE, accises
- promeos-enedis — connecteur SGE, SF1/SF2/SF3
- promeos-architecture — patterns backend/frontend
- promeos-seed — orchestration demo data
- promeos-energy-fundamentals — physique energie
- promeos-energy-market — marche elec/gaz France
- energy-contracts-b2b — contrats B2B fourniture
- energy-flexibility-dr — flexibilite et DR
- energy-autoconsommation — autoconsommation collective
- energy-france-veille — veille reglementaire

### Skills vendor (.agents/skills/) :
- fastapi-templates — patterns FastAPI
- python-testing-patterns — patterns pytest
- vercel-react-best-practices — React patterns
- webapp-testing — testing web apps

### Skill core (racine) :
- promeos-core (SKILL.md) — regles metier PROMEOS
