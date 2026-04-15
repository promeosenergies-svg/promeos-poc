# TEST REPORT - PROMEOS POC

**Date**: 2026-02-13
**Commande**: `py -3.14 -m pytest backend/tests/ -v --tb=short`
**Duree**: 131.62s (2min 11s)

---

## Resultat global

| Metrique | Valeur |
|----------|--------|
| **Total tests** | 824 |
| **Passed** | 824 (100%) |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Warnings** | 54942 (deprecation datetime.utcnow) |
| **Fichiers test** | 38 |

---

## Detail par fichier de test

| # | Fichier | Tests | Classes | Pass | Domaine |
|---|---------|-------|---------|------|---------|
| 1 | test_bill_pdf_parser.py | 28 | - | 28 | Bill Intelligence: PDF parsing |
| 2 | test_kb_citations.py | 19 | - | 19 | KB: citations, provenance |
| 3 | test_bill_engine.py | 18 | - | 18 | Bill Intelligence: shadow billing engine |
| 4 | test_iam.py | 18 | 10+ | 18 | IAM: auth, JWT, roles, scopes, permissions |
| 5 | test_watchlist_schema.py | 17 | - | 17 | Watchers: schema validation |
| 6 | test_regops_rules.py | 16 | - | 16 | RegOps: 4 packs reglementaires |
| 7 | test_fetch_dry_run.py | 20 | - | 20 | Referential: fetch sources |
| 8 | test_bill_timeline.py | 14 | - | 14 | Bill Intelligence: timeline analysis |
| 9 | test_bill_domain.py | 13 | - | 13 | Bill Intelligence: domain logic |
| 10 | test_manifest_build.py | 11 | - | 11 | Referential: manifest build |
| 11 | test_alert_engine.py | 11 | - | 11 | Monitoring: alert engine |
| 12 | test_compliance_engine.py | 10 | - | 10 | Compliance: engine core |
| 13 | test_compliance_v1.py | 10 | - | 10 | Compliance: V1 rules |
| 14 | test_sprint6_diag_v11.py | 10 | - | 10 | Diagnostic: V11 detectors |
| 15 | test_patrimoine.py | 10 | 7 | 10 | Patrimoine: staging, quality, activation |
| 16 | test_intake.py | 9 | 8 | 9 | Smart Intake: questions, apply, demo, API |
| 17 | test_notifications.py | 8 | - | 8 | Notifications: events, preferences |
| 18 | test_ai_agents.py | 7 | - | 7 | AI Agents: stub mode |
| 19 | test_kb_usages.py | 7 | - | 7 | KB: archetypes, rules, analytics |
| 20 | test_connectors.py | 7 | - | 7 | Connectors: registry, RTE, PVGIS |
| 21 | test_actions.py | 7 | - | 7 | Actions Hub: sync, workflow |
| 22 | test_data_quality.py | 7 | - | 7 | Monitoring: data quality |
| 23 | test_consumption_diag.py | 6 | 2 | 6 | Diagnostic: consommation |
| 24 | test_kpi_engine.py | 6 | - | 6 | Monitoring: KPI engine |
| 25 | test_power_calculations.py | 6 | - | 6 | Monitoring: power calculations |
| 26 | test_watchers.py | 6 | - | 6 | Watchers: RSS parsing |
| 27 | test_job_outbox.py | 6 | - | 6 | Jobs: outbox, worker, cascade |
| 28 | test_segmentation.py | 6 | - | 6 | Segmentation: questionnaire, profil |
| 29 | test_purchase.py | 5 | 2 | 5 | Achat Energie: scenarios, seed |
| 30 | test_monitoring_integration.py | 5 | - | 5 | Monitoring: integration |
| 31 | test_smoke.py | 5 | - | 5 | Smoke: endpoints up (need live DB) |
| 32 | test_demo_import.py | 4 | - | 4 | Demo: import flow |
| 33 | test_onboarding.py | 3 | 2 | 3 | Onboarding: org, sites |
| 34 | test_billing.py | 3 | - | 3 | Billing: contracts |
| 35 | test_sprint2.py | 3 | - | 3 | Sprint 2: legacy |
| 36 | test_reports.py | 3 | - | 3 | Reports: audit JSON/PDF |
| 37 | test_integration_pipeline.py | 1 | 1 | 1 | Integration: full pipeline |
| 38 | test_site_compliance_api.py | 1 | - | 1 | Sites: compliance API |

**Total**: 38 fichiers, 824 tests, 100% pass

---

## Couverture par brique

| Brique | Tests | % du total | Fichiers test |
|--------|-------|------------|---------------|
| Bill Intelligence | 73 | 8.9% | test_bill_*.py (4), test_billing.py |
| IAM / Auth | 61 | 7.4% | test_iam.py |
| Patrimoine DIAMANT | 29 | 3.5% | test_patrimoine.py |
| Diagnostic Conso | 28 | 3.4% | test_consumption_diag.py, test_sprint6_diag_v11.py |
| Knowledge Base | 26 | 3.2% | test_kb_citations.py, test_kb_usages.py |
| Smart Intake DIAMANT | 25 | 3.0% | test_intake.py |
| Monitoring / Energy | 24 | 2.9% | test_alert_engine.py, test_kpi_engine.py, test_power_*.py, test_data_quality.py, test_monitoring_*.py |
| Compliance | 20 | 2.4% | test_compliance_engine.py, test_compliance_v1.py |
| Achat Energie | 18 | 2.2% | test_purchase.py |
| RegOps | 16 | 1.9% | test_regops_rules.py |
| Referential | 31 | 3.8% | test_fetch_dry_run.py, test_manifest_build.py |
| Watchers | 23 | 2.8% | test_watchers.py, test_watchlist_schema.py |
| Notifications | 8 | 1.0% | test_notifications.py |
| Actions Hub | 7 | 0.8% | test_actions.py |
| AI Agents | 7 | 0.8% | test_ai_agents.py |
| Connectors | 7 | 0.8% | test_connectors.py |
| Segmentation | 6 | 0.7% | test_segmentation.py |
| Jobs | 6 | 0.7% | test_job_outbox.py |
| Onboarding | 5 | 0.6% | test_onboarding.py, test_sprint2.py |
| Cockpit | 0 | 0% | - |
| Alertes | 0 | 0% | - |
| Demo Mode | 0 | 0% | - |

---

## Briques sans tests (a ajouter)

| Brique | Fichier source | Tests manquants suggerees |
|--------|---------------|--------------------------|
| Cockpit | routes/cockpit.py, dashboard_2min.py | 5 tests: aggregation KPIs, filtres org, dashboard 2min |
| Alertes | routes/alertes.py | 3 tests: list, get, resolve |
| Demo Mode | routes/demo.py | 3 tests: enable, disable, seed |
| Compteurs | routes/compteurs.py | 3 tests: create, list, get |
| Guidance | routes/guidance.py | 2 tests: action-plan, readiness |

---

## Warnings deprecation (54942)

Toutes les warnings viennent de `datetime.utcnow()` deprece en Python 3.12+.

| Fichier source | Occurrences | Fix |
|----------------|-------------|-----|
| services/iam_service.py | L104, L110, L167, L227, L339 | `datetime.now(UTC)` |
| services/intake_service.py | L88, L227, L347 | `datetime.now(UTC)` |
| services/notification_service.py | L383, L459 | `datetime.now(UTC)` |
| services/purchase_service.py | L28 | `datetime.now(UTC)` |
| services/purchase_seed.py | L85, L111 | `datetime.now(UTC)` |
| services/audit_report_service.py | L68 | `datetime.now(UTC)` |
| services/analytics_engine.py | L90, L453, L497 | `datetime.now(UTC)` |
| services/consumption_diagnostic.py | L318 | `datetime.now(UTC)` |
| services/patrimoine_service.py | L516 | `datetime.now(UTC)` |
| routes/auth.py | L102 | `datetime.now(UTC)` |
| jobs/worker.py | L27 | `datetime.now(UTC)` |
| scripts/referential/build_manifest.py | L25 | `datetime.now(UTC)` |

**Effort total**: 15 min (remplacement global `datetime.utcnow()` -> `datetime.now(datetime.UTC)`)

---

## Commande de reproduction

```bash
cd promeos-poc
py -3.14 -m pytest backend/tests/ -v --tb=short
# Resultat attendu: 824 passed, 54942 warnings in ~132s
```
