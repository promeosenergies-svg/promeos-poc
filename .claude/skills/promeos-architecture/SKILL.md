---
name: promeos-architecture
description: "Architecture technique PROMEOS : data model (Org→EntiteJuridique→Portefeuille→Site→Bâtiment→Compteur), FastAPI+SQLAlchemy+SQLite, React 18+Vite+Tailwind v4+Recharts, patterns API, sources de vérité uniques, tests pytest+Vitest+Playwright, navigation, Cockpit, Site360. Utiliser ce skill pour tout choix technique, structure API, endpoints, modèles, composants React, tests, ou règles d'architecture PROMEOS."
---

# PROMEOS Architecture

## Routing

| Contexte | Fichier |
|---|---|
| Quel skill lire pour quelle tâche, combinaisons | `references/cross-skill-routing.md` |
| Tout le reste (data model, SoT, API, navigation) | Ce SKILL.md suffit |

## Proactive triggers — Alerter sans qu'on demande

- Calcul KPI détecté en frontend (JS/JSX) → "VIOLATION : business logic en frontend. Tous les calculs doivent être backend. Déplacer vers un endpoint dédié."
- Endpoint sans org_id filter → "Cet endpoint n'est pas org-scoped. Ajouter Depends(get_current_org) avant production."
- Duplication de logique SoT détectée → "Source de vérité dupliquée. Utiliser le service existant (voir table SoT dans ce skill)."
- datetime.utcnow() utilisé → "datetime.utcnow() est deprecated. Utiliser datetime.now(UTC)."

## Stack

Backend: FastAPI + SQLAlchemy + SQLite (PostgreSQL-ready).
Frontend: React 18 + Vite + Tailwind CSS v4 + Recharts + Lucide.
Tests: pytest (~843), Vitest (~3783), Playwright (E2E).
Export: SheetJS (Excel 3 sheets).

## Data Model

Organisation → EntiteJuridique → Portefeuille → Site → Bâtiment + Compteur + DeliveryPoint.
ContratCadre (entity-level) → AnnexeSite[] (site-level). CHECK: ContractPricing belongs to cadre OR annexe, jamais les deux.

## Sources de Vérité (SoT) — UN SEUL fichier par domaine

| Domaine | Fichier |
|---|---|
| Consommation | `backend/services/consumption_unified_service.py` |
| Scoring conformité | `backend/services/compliance_score_service.py` (A.2) |
| Trajectoire DT | `backend/services/dt_trajectory_service.py` |
| Pricing contrat | `backend/services/contract_pricing_service.py` (resolve_pricing) |
| NAF resolution | `backend/utils/naf_resolver.py` (resolve_naf_code) |
| Facteurs émission | `backend/config/emission_factors.py` |
| Tarifs réglementés | `backend/config/tarifs_reglementaires.yaml` (300 lignes, tarifs versionnés) |
| Intelligence KB | `backend/routes/site_intelligence.py` |
| Anomalies | `backend/services/analytics_engine.py` |
| Seed | `backend/services/demo_seed/orchestrator.py` |

## Règles NON-NÉGOCIABLES

1. **Zéro business logic en frontend** — tout calcul backend, frontend display-only
2. **Org-scoping** obligatoire sur chaque endpoint
3. **Source unique** par domaine — tests source guard pytest
4. **resolve_pricing(annexe)** = SoT prix effectif

## Navigation

Simple: 11 entrées. Expert: 19 (11+8). CommandPalette Ctrl+K.
`/cockpit` Vue COMEX, `/` Vue Exploitation, `/patrimoine`, `/contrats` (sous Patrimoine), `/conformite`, `/factures`, `/site360/{id}` (8 onglets, 0 stubs).

## API Patterns

Erreurs: `{detail, code, hint, correlation_id}`. Validation server-side. Idempotence: `kb-reco:{site_id}:{recommendation_code}`.

## Cycle de développement

Phase 0: audit read-only (pytest + vitest, STOP si fail>0).
Commits: `fix(p0): Phase N — description`.
Validation: Playwright screenshots. DoD: tests pass + screenshots + seed cohérent + pas de régression.

## MCP Plugins obligatoires

Context7 (docs), code-review (qualité), simplify (refactoring).

## Fichiers clés

Backend: config/ (emission_factors, default_prices, tarifs_reglementaires.yaml), services/ (consumption_unified, compliance_score, dt_trajectory, contract_pricing, cost_by_period, tariff_period_classifier, analytics_engine, demo_seed/orchestrator), routes/site_intelligence, regops/scoring, utils/naf_resolver.
Frontend: components/SiteIntelligencePanel, pages/consumption/HPHCPanel, utils/kpiLabels+kpiMessaging, context/ScopeContext.
Docs: bill_intelligence/, reglementaire/, Enedis/ (42 fichiers, 21MB).
