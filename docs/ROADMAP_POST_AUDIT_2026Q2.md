# PROMEOS Roadmap Post-Audit Master — Q2-Q3 2026

> Mis a jour le 2026-04-07 par Product Manager

---

## Scorecard Post-Sprints B-F

| Axe | Avant | Apres | Delta | Statut |
|-----|-------|-------|-------|--------|
| Securite | 20/100 | 20/100 | 0 | **P0 CRITIQUE** — Sprint A a faire |
| API Qualite | 40/100 | 55/100 | +15 | En validation |
| Tests | 15/100 | 25/100 | +10 | Cible 60% |
| UX | 75/100 | 85/100 | +10 | En cours |
| EMS | 63/100 | 80/100 | +17 | Tier 1 livre |
| Connecteurs | 50/100 | 70/100 | +20 | Validation en cours |
| Seed | 66/100 | 85/100 | +19 | Idempotent + calibre |

**Score global** : ~60/100 (avant : ~47/100) — +13 points en 5 sprints.

---

## Bilan Sprints B-F (25 taches livrees)

- **P0 fixes critiques** : POC labels, seed idempotence, prix ref 0.068
- **P1 ameliorations** : RegOps scoring granulaire, CEE cumac auto, export OPERAT elec/gaz, cockpit consolidation useEffect
- **UX hardening** : ErrorState sur 4 pages, empty states, loading states, PageShell
- **Integration Achat** : Fusion 5 tabs, deep-links, assistant integre

---

## Priorites Roadmap

### Phase 1 — Securite Sprint A (S15-S16) — P0 BLOQUANT

Aucune mise en production possible avant completion.

- 43+ endpoints sans org-scoping (power.py, contracts_v2, flex, usages, ems)
- Pattern : `resolve_org_id(request, auth, db)` + filtre `Site.org_id`
- 20+ tests cross-org isolation
- CORS whitelist + JWT secret rotation (sans default)

### Phase 2 — Stabilisation + Tests 60% (S17-S18)

- Couverture tests : 25% → 60%
  - Unitaires : purchase, EMS, billing
  - E2E Playwright pages principales
  - Cross-org isolation (Sprint A)
- CI verte Docker + GitHub Actions
- QA 0-fail baseline sur sprints B-F
- Seed idempotent toutes briques

### Phase 3 — Connecteurs Production (S19-S20)

- Enedis SGE C4/C2 (SOAP, cadence 10min)
- DataConnect OAuth2 PKCE (C5, cadence 30min)
- GRDF ADICT REST
- Lifecycle consentements + revocation
- Monitoring + retry + gap detection

### Phase 4 — EMS Tier 2 + Achat V2 (S21-S24)

- EMS drill-down : portfolio > site > batiment > compteur
- Signature energetique E=a*DJU+b, CUSUM ISO50001
- Anomalie ML : LOF + IsolationForest + SHAP explainability
- Achat V2 : Mode Express, Bar chart couts, Marketplace offres

### Phase 5 — Pilote Client (S25+, Q3-Q4)

- Demo scenario complet premier ETI pilote
- Connecteur marketplace energie (offres fournisseurs reelles)
- Extension Gaz module Achat
- Rapport PDF automatise multi-module
- Performance : < 2s toutes pages

---

## KPIs Cibles

| KPI | Actuel | Cible Q2 | Cible Q3 |
|-----|--------|----------|----------|
| Score securite | 20/100 | 90/100 | 95/100 |
| Couverture tests | 25% | 60% | 75% |
| Score UX | 85/100 | 90/100 | 92/100 |
| Score EMS | 80/100 | 85/100 | 92/100 |
| Score Connecteurs | 70/100 | 85/100 | 90/100 |
| Endpoints prod-ready | ~60% | 90% | 100% |
| Temps chargement pages | ~3s | <2s | <1.5s |

---

## Risques

| Risque | Prob. | Impact | Mitigation |
|--------|-------|--------|------------|
| Sprint A securite > 2 sprints | Moyenne | Pipeline bloque | Decomposer par module (power.py d'abord) |
| Connecteurs Enedis/GRDF instables | Haute | Donnees reelles bloquees | Circuit breaker + retry + monitoring |
| Performance degradee donnees reelles | Moyenne | UX deterioree | Load test k6 des Sprint 10, Redis |
| Pilote client reporte | Faible | Impact business | Demo interne mensuelle |
