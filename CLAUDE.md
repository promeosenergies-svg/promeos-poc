# CLAUDE.md — Context PROMEOS pour Claude Code

Ce fichier est charge automatiquement par Claude Code a chaque session.

## Skill obligatoire

Charge le skill PROMEOS avant toute action :
-> Voir `SKILL.md` a la racine pour toutes les regles non-negociables.
-> Skills detailles dans `.claude/skills/` (11 skills domaine).

## Stack

- Backend : Python 3.11 / FastAPI / SQLAlchemy / SQLite
- Frontend : React 18 / Vite / Tailwind CSS v4 / Recharts / Lucide
- Tests : pytest (BE) / Vitest (FE) / Playwright (E2E)
- Repo : github.com/promeosenergies-svg/promeos-poc
- Port backend : **8001** (pas 8000 ni 8080)
- Port frontend : **5173** (proxy -> localhost:8001)

## Avant toute modification

1. Phase 0 read-only : `grep`, `find`, lire les fichiers concernes
2. Zero modif sans bilan Phase 0 valide
3. Tests avant ET apres chaque phase
4. Commit atomique par phase

## Fichiers critiques (ne pas toucher sans audit)

- `backend/services/compliance_score_service.py` — source de verite scoring
- `backend/services/consumption_unified_service.py` — source de verite conso
- `backend/config/emission_factors.py` — constantes CO2
- `backend/config/tarifs_reglementaires.yaml` — tarifs versionnes
- `backend/utils/naf_resolver.py` — resolution NAF (ne pas dupliquer)
- `backend/regops/scoring.py` — scoring conformite

## Commandes de reference

```bash
# Backend
cd backend && python main.py                        # -> http://localhost:8001
cd backend && python -m pytest tests/ -v            # tests backend

# Frontend
cd frontend && npm run dev                           # -> http://localhost:5173
cd frontend && npx vitest run                        # tests frontend

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

## Regle d'or

**ZERO calcul metier en frontend.** Tout calcul backend, frontend display-only.
