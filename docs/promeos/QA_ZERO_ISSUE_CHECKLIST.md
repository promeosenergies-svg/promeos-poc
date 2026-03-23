# PROMEOS — QA Zero Issue Checklist

> Checklist exécutée avant chaque release. Tout ✅ requis pour merger.

## 1. Build & Tests

| Check | Commande | Attendu |
|-------|----------|---------|
| Frontend build | `cd frontend && npx vite build` | ✓ built, 0 errors |
| Frontend tests | `cd frontend && npx vitest run` | 5659+ passed, 0 failed |
| Backend tests ciblés | `cd backend && python -m pytest tests/test_cockpit_smoke_demo.py tests/test_demo_e2e_journey.py tests/test_monosite_portfolio_parity.py tests/test_compliance_score_service.py tests/test_billing_invariants_p0.py -q` | 84+ passed, 0 failed |
| Backend full | `cd backend && python -m pytest tests/ -q` | 0 failed |
| E2E Playwright | `cd e2e && npx playwright test` | 17+ passed |

## 2. Audit Cross-Views

| Check | Commande | Attendu |
|-------|----------|---------|
| Audit automatisé | `cd backend && python scripts/audit_cross_views.py` | 60 checks, 0 issues |
| Audit visuel Playwright | `cd e2e && npx playwright test audit-visual.spec.js` | 17 passed |

## 3. Cohérence KPI

| Vérification | Méthode |
|-------------|---------|
| Conso cockpit = conso patrimoine | API `/api/cockpit` vs `/api/patrimoine/sites` |
| Risque cockpit = Σ risque sites | `risque_financier_eur` vs `SUM(sites.risque_eur)` |
| Compliance portfolio = pondéré surface | Vérifier formule `Σ(score×surface)/Σ(surface)` |
| Monosite 1 site = portfolio 1 site | `test_monosite_portfolio_parity.py` |
| Export PDF = valeurs écran | Playwright audit-visual |
| Score achat inline = recompute | Comparer `score_offer()` dans compute vs recompute |

## 4. Parcours Démo

| Écran | Vérifié |
|-------|---------|
| Login → Cockpit | Charge sans erreur, KPIs affichés |
| Cockpit → drill-down site | Drawer s'ouvre, données cohérentes |
| Cockpit → Conformité | Score identique entre les deux vues |
| Cockpit → Priorités | 3 candidats avec impact chiffré |
| Cockpit → Export PDF | PDF généré, valeurs identiques |
| Patrimoine → Registre | 5 sites, risques cohérents |
| Patrimoine → Site360 | Conso/risque/compteurs corrects |
| Site360 → Factures | Contrats affichés, anomalies listées |
| Site360 → Conformité | Obligations BACS/DT/APER visibles |
| Site360 → Réconciliation | État du site + blockers |
| Conformité → ObligationsTab | Findings avec sévérité, deadline |
| Conformité → RegOps | Score + actions recommandées |
| Achat → Radar contrats | Filtres horizon fonctionnels (30/60/90j) |
| Achat → Scénarios | 3 scénarios avec scoring visible |
| Bill Intelligence → Insights | Anomalies listées avec perte estimée |
| Actions → Plan d'actions | 12 actions, impact/ROI cohérents |
| Notifications → Alertes | 10 alertes, sévérité correcte |

## 5. Empty States & Errors

| Cas | Attendu |
|-----|---------|
| Site sans données conso | Message clair + CTA import |
| Scope vide (pas d'org) | Redirection onboarding |
| API 500 | ErrorState avec retry |
| API 404 | Message "introuvable" |
| Filtre sans résultat | EmptyState "Aucun résultat" |
| Sidebar scroll long | Sidebar fixe, contenu scrolle |

## 6. Unités & Labels

| Vérifié |
|---------|
| Toute énergie en kWh/MWh/GWh (jamais sans unité) |
| Tout montant en EUR avec k€/M€ |
| Toute surface en m² |
| Toute puissance en kW/kVA |
| Toute date au format FR (14 fev. 2026) |
| Labels conformité en français |

## 7. Sécurité (hors scope pilote)

| Check | Statut |
|-------|--------|
| Pas de secret en dur dans le code | ⚠ PROMEOS_JWT_SECRET=default en dev |
| Pas de données sensibles dans les logs | ✅ |
| CORS restreint | ⚠ Permissif en dev |
| Rate limiting | ❌ Non implémenté |

## 8. Performance (seuils POC)

| Endpoint | Median | p95 | Seuil |
|----------|--------|-----|-------|
| GET /api/cockpit | < 100ms | < 300ms | 500ms |
| GET /api/cockpit/compliance-history | < 50ms | < 150ms | 300ms |
| GET /api/cockpit/priorities | < 80ms | < 200ms | 300ms |
| GET /api/cockpit/export-report-data | < 100ms | < 250ms | 500ms |
| Génération PDF (front) | < 500ms | < 1s | 2s |

## 9. Commandes de vérification rapide

```bash
# Full check (5 min)
bash scripts/demo-test.sh

# Build seul
cd frontend && npx vite build

# Tests ciblés backend (30s)
cd backend && python -m pytest tests/test_cockpit_smoke_demo.py tests/test_monosite_portfolio_parity.py -q

# Audit cross-views (15s)
cd backend && python scripts/audit_cross_views.py

# E2E (si serveurs tournent)
cd e2e && npx playwright test audit-visual.spec.js
```
