# V1.C — Cartographie backend FastAPI

**Date**: 2026-04-24 · **Scope**: backend identique sur MAIN et refonte-visuelle-sol (diff marginal confirmé)

## 1. Point d'entrée & architecture

- **Fichier** : `backend/main.py` (523 lignes)
- **App FastAPI** : title="PROMEOS API", version="1.0.0"
- **81 routers inclus** — **607 endpoints @router**
- **Middlewares** :
  - `RequestContextMiddleware` → inject `request_id` (UUID 8 chars) + `X-Response-Time`
  - `CORSMiddleware` → whitelist `PROMEOS_CORS_ORIGINS` (défaut `localhost:5173,localhost:3000`)
  - Error handler global → `APIError` JSON
  - Rate limiter slowapi → `/api/public/*`
  - OAuth2 Bearer (auto_error=False, demo lenient)
- **Health** : `GET /`, `GET /health`, `GET /api/health` (DB + git_sha + engine_versions), `GET /api/meta/version`

## 2. Inventaire endpoints (par module)

### Conformité — 24 endpoints (`routes/compliance.py`)
- `GET /api/compliance/meta` (framework_weights, critical_penalty)
- `POST /api/compliance/recompute` (recalcul global, body: site_ids[])
- `GET /api/compliance/summary` (organisations[], conformity_rate)
- `GET /api/compliance/sites` (liste + score)
- `GET /api/compliance/sites/{site_id}/score` (score A.2 unifié)
- `GET /api/compliance/findings?status&regulation`
- `PATCH /api/compliance/findings/{finding_id}` (dismiss/accept)
- `GET /api/compliance/sites/{site_id}/packages` (CEE)
- `GET /api/compliance/rules?regulation`
- `POST /api/compliance/recompute-rules` (reload config)

### Tertiaire / OPERAT — 35 endpoints (`routes/tertiaire.py`)
- `GET /api/tertiaire/status?site_id`
- `POST /api/tertiaire/declare`
- `POST /api/tertiaire/export-csv` (OPERAT)
- `GET /api/tertiaire/pre-check`

### BACS — 29 endpoints (`routes/bacs.py`)
### APER — 2 endpoints (`routes/aper.py`)
### OPERAT — 5 endpoints (`routes/operat.py`)
### RegOps — 11 endpoints (`routes/regops.py`)

### Patrimoine CRUD — 21 endpoints (`routes/patrimoine_crud.py`)
- `GET|POST|PATCH|DELETE /api/patrimoine/organisations[/{id}]`
- `GET|POST /api/patrimoine/sites[/{id}]`
- `GET /api/patrimoine/sites/{site_id}` (détail complet : bâtiments, compteurs, consommation)
- `POST /api/patrimoine/batiments`
- `/api/patrimoine/entite-juridique/*`, `/api/patrimoine/portefeuille/*`

### Sites — 7 endpoints (`routes/sites.py`) — **6 deprecated**
### Geocoding — 3 endpoints

### Consommation
- `GET /api/consumption/unified/summary?site_id&start&end&source` → source unique SoT (metered/billed/reconciled)
- `GET /api/consumption/unified/reconciliation` → delta %
- `routes/consommations.py` (3), `routes/consumption_diagnostic.py` (23), `routes/consumption_context.py` (10), `routes/portfolio.py` (2)

### Facturation & Shadow billing — 29 endpoints (`routes/billing.py`)
- `POST /api/billing/import` (CSV)
- `GET /api/billing/periods`, `/coverage-summary`
- `POST /api/billing/missing-periods` (interpolation)
- `GET /api/billing/summary`, `/anomalies`
- `POST /api/billing/shadow/{invoice_id}/audit`

### Achat — 23 endpoints (`routes/purchase.py`)
- `GET /api/purchase/scenarios?site_id`
- `POST /api/purchase/simulate`
- `GET /api/purchase/contracts?org_id`
- `POST /api/purchase/recommender`
- `GET /api/purchase/market-prices?region&date_range`

### Contracts V2 — 19 endpoints · Contracts Radar — 4

### Flex & Pilotage
- `GET /api/flex/assets`
- `GET /api/flex/score` (NEBCO score 0-100, disaggregation par usages)
- `POST /api/flex/simulation` (DR simulation)
- `routes/pilotage.py` (5), `routes/power.py` (7)

### Marché
- `routes/market.py` (2), `market_data.py` (12), `market_intelligence.py` (7)

### Alertes & Actions
- `routes/action_center.py` (**38 endpoints**) : `/issues`, `/actions` CRUD, bulk/assign, close
- `routes/actions.py` (21), `action_templates.py` (3)
- `routes/notifications.py` (13), `alertes.py` (3)

### Monitoring — 11 endpoints (`routes/monitoring.py`)
### Analytics — 5 · Data Quality — 5 · EMS — 28

### Ingestion
- `POST /api/enedis/oauth/authorize` + `/callback` (PKCE)
- `POST /api/grdf/import` (ADICT)
- `routes/connectors_route.py` (4), `dataconnect_route.py` (6), `bridge_route.py` (4), `energy.py` (8), `import_sites.py` (2), `watchers_route.py` (5)

### Onboarding & config
- `routes/onboarding.py` (3), `onboarding_stepper.py` (4), `site_config.py` (4), `intake.py` (8), `segmentation.py` (7)

### Cockpit & dashboards
- `GET /api/cockpit/executive` (`cockpit_v2.py`) : hero + health + actions
- `GET /api/cockpit/2min` (`dashboard_2min.py`) : KPIs vue 2 min
- `cockpit.py` (7)

### KB & IA
- `routes/kb_usages.py` (13) — recos usages
- `routes/copilot.py` (4) — insights IA
- `guidance.py` (2), `site_intelligence.py` (2)

### Siège & public
- `POST /api/sirene/search` (rate-limited)
- `POST /api/sirene/import-org`
- `GET /api/public/diagnostic?siren` (freemium)

### Divers
- `demo.py` (11), `dashboard_2min.py` (1), `usage.py` (28), `referentiel.py` (1), `cx_dashboard.py` (4), `value_summary.py` (1), `feedback.py` (2), `nps.py` (1)

### Admin
- `auth.py` (9) : login, logout, switch-org, refresh, me
- `admin_users.py` (9)

**Total auditable : 607 endpoints.**

## 3. Services métier critiques — Top 20 par taille

| Service | Fichier | Lignes | Rôle |
|---------|---------|--------|------|
| Usage Service | `services/usage_service.py` | 1668 | 15 catégories NEGBI-flex, baseline, cost breakdown |
| Patrimoine Service | `services/patrimoine_service.py` | 1429 | CRUD orgs/entités/portefeuilles avec validation |
| Demo Seed Orchestrator | `services/demo_seed/orchestrator.py` | 1401 | HELIOS/TERTIAIRE/MERIDIAN master + readings + billing |
| Billing Catalog | `services/billing_engine/catalog.py` | 1271 | TURPE 6/7, accise, TICGN, TVA, CTA, capacité |
| Demo Readings | `services/demo_seed/gen_readings.py` | 1219 | Courbes horaires 730 jours + anomalies |
| Billing Shadow V2 | `services/billing_shadow_v2.py` | 1197 | Shadow bill canon ligne-par-ligne |
| Billing Service | `services/billing_service.py` | 1155 | Import, reconciliation, coverage, anomalies |
| Contract V2 | `services/contract_v2_service.py` | 1110 | Cadre+annexes, versioning, post-ARENH |
| Billing Engine | `services/billing_engine/engine.py` | 1057 | TURPE/taxes/capacité + TRVE |
| Consumption Diagnostic | `services/consumption_diagnostic.py` | 939 | Benchmark vs archétype, leaderboard |
| Tertiaire Service | `services/tertiaire_service.py` | 912 | DT trajectoire -40/-50/-60% |
| Usage Anomaly Detector | `services/analytics/usage_anomaly_detector.py` | 903 | Isolation forest + seuils |
| Demo Completion | `services/demo_seed/gen_seed_completion.py` | 873 | Compliance runs + alertes + actions |
| Reconciliation | `services/reconciliation_service.py` | 806 | Metered/billed avec confidence |
| Audit Report | `services/audit_report_service.py` | 786 | PDF/JSON + findings critiques |
| BACS Engine | `services/bacs_engine.py` | 780 | 10 critères R.175-3, TRI exemption |
| Compliance Rules | `services/compliance_rules.py` | 778 | 100+ règles DT/BACS/APER |
| Segmentation | `services/segmentation_service.py` | 754 | Archétypes NAF |
| **Compliance Score** | `services/compliance_score_service.py` | — | **SoT score A.2 (45% DT + 30% BACS + 25% APER)** |
| **Consumption Unified** | `services/consumption_unified_service.py` | — | **SoT conso metered/billed/reconciled** |

### Services configuration critiques
- `config/emission_factors.py` : ADEME V23.6 — ELEC 0.052, GAZ 0.227 kgCO2e/kWh
- `config/tarifs_reglementaires.yaml` : TURPE 6/7, accise, TICGN, TVA, CTA par région/saison
- `utils/naf_resolver.py` : cascade Site.naf_code → EntiteJuridique.naf_code → None
- `regops/config/regs.yaml` : seuils DT/BACS/APER, deadlines, poids 45/30/25
- `regops/config/scoring_profile.json` : pénalités + sévérités (critical 4 > high 3 > medium 2 > low 1)

## 4. Modèles SQLAlchemy

| Modèle | Table | Mixins | Relations |
|--------|-------|--------|-----------|
| Organisation | organisation | Timestamp, SoftDelete | entites[], portefeuilles[], sites[] |
| EntiteJuridique | entite_juridique | — | organisation, portefeuilles[] |
| Portefeuille | portefeuille | — | entite_juridique, sites[] |
| Site | site | Timestamp, SoftDelete | portefeuille, batiments[], compteurs[] |
| Batiment | batiment | — | site |
| Compteur | meter | Timestamp, SoftDelete | site, prm/pce, readings[] |
| MeterReading | meter_reading | — | meter (HOURLY/DAILY/MONTHLY) |
| EnergyInvoice | energy_invoice | Timestamp | site, period_start/end, kwh |
| RegAssessment | reg_assessment | Timestamp | site, regulation (DT/BACS/APER), score |
| ComplianceFinding | compliance_finding | Timestamp | reg_assessment, severity |
| ContractV2 | contract_v2 | Timestamp | site, tarif_type (FIXE/INDEXE/SPOT) |
| ActionItem | action_item | Timestamp, SoftDelete | site, source, status, owner |
| ActionNotification | action_notification | — | action_item, user |
| MarketPrice | market_price | Timestamp | region, timestamp, price_eur_mwh |
| Usage | usage | Timestamp | site, family (15 NEGBI), baseline |
| DeliveryPoint | delivery_point | Timestamp | site, prm/pce, status |
| User | user | Timestamp | role |
| UserOrgRole | user_org_role | — | user, organisation, role (ADMIN/MANAGER/VIEWER) |

**Mixins** : `TimestampMixin` (created_at/updated_at UTC), `SoftDeleteMixin` (deleted_at/deleted_by). Helper `not_deleted(query, model)`.

## 5. Seed démo

### Packs
- **HELIOS** (canonique, S) : 5 sites × (1-4 compteurs) × 730 jours + 24+ factures + actions + compliance + market prices + archétypes NAF
- **TERTIAIRE** (hidden, S/M) : 10-20 bâtiments
- **MERIDIAN** : 3 sites supplémentaires

### Commande
```bash
python -m services.demo_seed --pack helios --size S --reset
```

### 11 générateurs
`gen_master.py`, `gen_readings.py`, `gen_billing.py`, `gen_weather.py` (PVGIS), `gen_compliance.py`, `gen_actions.py`, `gen_alerts.py`, `gen_notifications.py`, `gen_market_prices.py`, `gen_pilotage_fields.py` (archetype + puissance_pilotable), `gen_cbam_fields.py`.

## 6. ParameterStore / YAML

| Fichier | Lignes | Versioning |
|---------|--------|-----------|
| `tarifs_reglementaires.yaml` | 1000+ | Manuel (commentaires # V85, # 2026-03-21) |
| `regs.yaml` | 150+ | Manuel (MAJ 2026-03-21) |
| `scoring_profile.json` | — | Manuel |
| `emission_factors.py` | — | Manuel (V23.6 en commentaire) |
| `naf_profiles.yaml` | — | Manuel |

**Manque** : versioning automatique (git blame / table ParameterAudit).

## 7. Gestion d'erreurs

### Structure uniforme
```json
{
  "code": "SITE_NOT_FOUND | VALIDATION_ERROR | INTERNAL_ERROR",
  "message": "Texte user-friendly",
  "hint": "Debug optionnel",
  "correlation_id": "8 chars UUID"
}
```

### Handlers (`middleware/error_handler.py`)
1. `HTTPException` → code map (400→BAD_REQUEST, 401→UNAUTHORIZED, 404→NOT_FOUND…)
2. `RequestValidationError` → liste erreurs Pydantic par champ + correlation_id
3. `Exception` → INTERNAL_ERROR + stack trace log

### Logging
- Loggers : `promeos.errors`, `promeos.startup`, `promeos.health`
- Format JSON structuré via `services/json_logger.py`
- Corrélation : `request_id` injecté par middleware

### Écart vs recommandé
✓ code/message/hint/correlation_id · ✓ logging structuré · ✓ middleware central · ⚠ pas de versioning format erreur

## 8. Tests backend

```
tests/
  ├── conftest.py (fixtures autouse + ensure_demo_data)
  ├── test_*.py (~330 fichiers)
  ├── snapshots/
  └── fixtures/
```

### Répartition (approx)
| Catégorie | Fichiers |
|-----------|----------|
| Unit | ~150 |
| Integration | ~100 |
| Source Guards | 2 nouveaux (refonte SOL) |
| E2E/Smoke | ~80 |

### Tests source-guards (refonte SOL)
- `test_no_compliance_logic_in_frontend_conformite.py` — vérifie routing `/api/compliance/*` reste backend
- `test_no_compliance_logic_in_frontend_pipeline.py` — vérifie pipeline RegAssessment backend-only

### Tests critiques
- `test_sprint2.py` — Patrimoine CRUD, soft-delete, héritage
- `test_step18_tarif_referentiel.py` — TURPE/taxes
- `test_step25_meter_unified.py` — unified metered/billed/reconciled
- `test_helios_seed_v83.py` — seed intégrité
- `test_purchase_auth_hardening.py` — auth stricte
- `test_market_data_service.py` — EPEX freshness

## 9. Diff backend MAIN vs REFONTE SOL

**34 fichiers différents** — ampleur **marginale**.

- **Config** (1) : `config/tarifs_reglementaires.yaml` (+100 LOC : ATRD7 GRDF + biométhane)
- **Routes** (1) : `routes/kb_usages.py` (UI hints mineurs)
- **Services** (6) : `analytics/usage_anomaly_detector.py`, `analytics/usage_disaggregation.py`, `patrimoine_conformite_sync.py`, `pilotage/portefeuille_scoring.py`, `scope_utils.py` (optimisations mineures)
- **Tests** (26) : maj fixtures + 2 nouveaux source-guards + conftest

**✓ Aucune logique métier critique modifiée** : scoring, compliance_score_service, consumption_unified_service, emission_factors, naf_resolver, demo_seed orchestrator — tous intacts.

**Verdict backend** : refonte SOL = **cosmétique front confirmée**, backend stable et SoT préservées.

## 10. Top 10 risques backend (statique)

| # | Risque | Localisation | Sévérité |
|---|--------|--------------|---------|
| 1 | Demo mode overly lenient : `get_optional_auth` = None si DEMO_MODE=true + no token | `middleware/auth.py:104-105` | HAUTE |
| 2 | Rate limits insuffisants pour `/api/public/diagnostic` (Sirene/gouv) | `main_limiter.py` + `public_diagnostic` | MOYENNE |
| 3 | Soft-delete inconsistency : mixin présent mais queries sans `not_deleted()` filter | `models/base.py` SoftDeleteMixin | MOYENNE |
| 4 | Compliance score hardcoded fallback 45/30/25 si regs.yaml absent | `compliance_score_service.py:53-68` | MOYENNE |
| 5 | Missing validation Pydantic sur certains POST/PATCH patrimoine | `routes/patrimoine_crud.py` | BASSE |
| 6 | 6+ routes deprecated=True toujours fonctionnelles | `routes/sites.py` | BASSE |
| 7 | TODO unresolved : temporal_signature_json, implementation_steps | `services/kb_service.py` | BASSE |
| 8 | Seed héros silencieux si échec → DemoState incohérent | `main.py._startup_restore_or_seed_helios` | BASSE |
| 9 | Circular imports potential : models → services → routes | `routes/__init__.py` | TRÈS BASSE |
| 10 | YAML regs.yaml sans schéma validation → typo clé silently ignored | `regops/config/regs.yaml` | TRÈS BASSE |

## 11. Synthèse chiffres

| Métrique | Valeur |
|----------|--------|
| Routers | 81 fichiers |
| Endpoints | 607 |
| Services | ~234 fichiers (7.3 MiB) |
| Modèles SQLAlchemy | 72 |
| Tests | 330 fichiers |
| Diff main vs refonte | 34 fichiers (backend ~identique) |
| LOC backend | ~70k (services/billing/demo/compliance/usage majeurs) |
| YAML configs | 5 (tarifs, regs, scoring, naf, cee) |
