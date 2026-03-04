# PROMEOS POC — Quality Gates

> Version: V113.1 | Date: 2026-03-04 | Status: Active

## Gate 1 — Backend Build & Import

**Critere**: Tous les modules Python importent sans erreur.

```bash
cd backend
python -c "from main import app; print(f'{len(app.routes)} routes loaded')"
```

**Seuil**: 0 ImportError, >= 400 routes.

---

## Gate 2 — Backend Tests

**Critere**: Tous les tests passent, 0 failure.

```bash
cd backend
python -m pytest tests/test_v113_data_quality_causes.py tests/test_v113_operat_golden.py -v
python -m pytest tests/ -x -q --tb=short
```

**Seuil**: 0 failures. Timeout max 5 min.

---

## Gate 3 — Backend Lint (Ruff)

**Critere**: Ruff lint passe sans erreur sur les fichiers V113+.

```bash
cd backend
python -m ruff check routes/ models/ services/ --select E,F,W,B
```

**Seuil**: 0 errors (warnings toleres en POC).

---

## Gate 4 — Frontend Build

**Critere**: Vite build sans erreur.

```bash
cd frontend
npm run build
```

**Seuil**: Exit code 0, bundle genere dans dist/.

---

## Gate 5 — Frontend Tests

**Critere**: Vitest run sans failure.

```bash
cd frontend
npx vitest run
```

**Seuil**: 4300+ tests passent, 0 failures.

---

## Gate 6 — Frontend Lint

**Critere**: ESLint passe sans erreur.

```bash
cd frontend
npx eslint src --ext js,jsx --max-warnings=0
```

**Seuil**: 0 errors, 0 warnings.

---

## Gate 7 — Data/KPI Coherence

**Critere**: Les KPIs affiches dans les tuiles = KPIs dans les graphes/tables.

**Verification manuelle**:
1. Cockpit: coverage % = Data Quality service `overall_coverage_pct`
2. Copilot: savings EUR = somme des `estimated_savings_eur` (proposed + converted)
3. OPERAT: Total kWh = `Conso_elec_kWh + Conso_gaz_kWh + Conso_reseau_kWh`
4. Actions: count = API `total` field

**Seuil**: Aucune divergence.

---

## Gate 8 — Filtres & Navigation

**Critere**: Filtres ScopeContext s'appliquent partout, pas de dead links.

**Verification**:
```bash
# Backend: tous les endpoints avec org_id/site_id
cd backend
grep -r "org_id" routes/ --include="*.py" | wc -l
```

**Seuil**: Chaque page avec filtre site/org produit des resultats coherents avec le scope.

---

## Gate 9 — UX States

**Critere**: Chaque page a: loading skeleton, empty state, error state.

**Verification**: Parcours manuel des 12 pages principales (voir qa_smoketests.md).

**Seuil**: 0 page sans loading state. 0 page avec erreur silencieuse.

---

## Gate 10 — Demo Seed

**Critere**: Le seed HELIOS genere des donnees coherentes.

```bash
cd backend
python -m services.demo_seed --pack helios --size S --reset
```

**Seuil**: Exit code 0, >= 5 sites, readings + invoices + actions generees.

---

## Recapitulatif

| Gate | Commande | Seuil |
|------|----------|-------|
| G1 Backend Import | `python -c "from main import app"` | 0 ImportError |
| G2 Backend Tests | `pytest tests/ -x -q` | 0 failures |
| G3 Backend Lint | `ruff check routes/ models/ services/` | 0 errors |
| G4 Frontend Build | `npm run build` | exit 0 |
| G5 Frontend Tests | `npx vitest run` | 0 failures |
| G6 Frontend Lint | `npx eslint src --ext js,jsx` | 0 errors |
| G7 KPI Coherence | Manuel | 0 divergence |
| G8 Filtres | Manuel + grep | Scope coherent |
| G9 UX States | Manuel (12 pages) | 0 page sans states |
| G10 Demo Seed | `python -m services.demo_seed` | exit 0 |
