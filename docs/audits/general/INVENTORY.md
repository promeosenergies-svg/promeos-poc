# INVENTORY - PROMEOS POC
**Date**: 2026-02-09

---

## REPO MAP

```
promeos-poc/
├── backend/                 # FastAPI + SQLAlchemy
│   ├── ai_layer/           # 5 AI agents + stub mode
│   │   ├── agents/         # regops_explainer, recommender, data_quality, reg_change, exec_brief
│   │   ├── prompts/        # Prompt templates
│   │   ├── client.py       # AIClient (stub if no API_KEY)
│   │   └── registry.py     # Agent discovery
│   ├── connectors/         # 5 connecteurs externes
│   │   ├── base.py         # ABC Connector
│   │   ├── rte_eco2mix.py  # ✅ REAL - Grid CO2 intensity
│   │   ├── pvgis.py        # ✅ REAL - Solar estimates
│   │   ├── enedis_*.py     # 🔒 STUB - Needs OAuth
│   │   └── meteofrance.py  # 🔒 STUB - Needs API key
│   ├── watchers/           # 3 watchers réglementaires
│   │   ├── base.py         # ABC Watcher
│   │   ├── rss_watcher.py  # Generic RSS parser
│   │   ├── legifrance_watcher.py
│   │   ├── cre_watcher.py
│   │   └── rte_watcher.py
│   ├── regops/             # Moteur RegOps (4 régulations)
│   │   ├── config/         # YAML configs
│   │   │   ├── regs.yaml   # Tertiaire, BACS, APER, CEE P6
│   │   │   ├── naf_profiles.yaml
│   │   │   ├── location_profiles.yaml
│   │   │   └── cee_p6_catalog.yaml
│   │   ├── rules/          # 4 rule engines
│   │   │   ├── tertiaire_operat.py
│   │   │   ├── bacs.py
│   │   │   ├── aper.py
│   │   │   └── cee_p6.py
│   │   ├── engine.py       # Orchestrator + scoring
│   │   ├── schemas.py      # Finding, Action, SiteSummary
│   │   ├── completeness.py # Input validation
│   │   └── versioning.py   # Hash-based cache invalidation
│   ├── jobs/               # JobOutbox async pattern
│   │   ├── worker.py       # Enqueue, process, cascade
│   │   └── run.py          # CLI (--once, --watch, --drain)
│   ├── models/             # 18 tables SQLAlchemy
│   │   ├── organisation.py, site.py, batiment.py, compteur.py
│   │   ├── datapoint.py    # External data lineage
│   │   ├── reg_assessment.py # Cached RegOps evaluations
│   │   ├── job_outbox.py   # Async job queue
│   │   ├── ai_insight.py   # AI outputs (NEVER modifies status)
│   │   ├── reg_source_event.py # Regulatory news (hash + snippet)
│   │   ├── evidence.py     # Compliance proofs
│   │   └── enums.py        # 11 enums (ParkingType, RegStatus, etc.)
│   ├── routes/             # 37 API endpoints
│   │   ├── regops.py       # 4 endpoints (site, cached, recompute, dashboard)
│   │   ├── connectors_route.py # 3 endpoints
│   │   ├── watchers_route.py # 4 endpoints
│   │   ├── ai_route.py     # 5 endpoints
│   │   ├── compliance.py, sites.py, cockpit.py, demo.py, guidance.py
│   │   └── alertes.py, compteurs.py, consommations.py
│   ├── services/           # Business logic
│   │   ├── compliance_engine.py # Legacy engine (56 tests OK)
│   │   ├── action_plan_engine.py
│   │   ├── guardrails.py
│   │   ├── demo_state.py
│   │   └── demo_templates.py
│   ├── scripts/
│   │   └── seed_data.py    # 120 sites + RegOps data
│   ├── tests/              # 98 test cases (73% pass)
│   └── main.py             # FastAPI app entry
├── frontend/               # React + Vite
│   ├── src/
│   │   ├── pages/          # 7 pages
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Cockpit.jsx
│   │   │   ├── SiteDetail.jsx
│   │   │   ├── ActionPlan.jsx
│   │   │   ├── RegOps.jsx         # ⭐ NEW - Dual panel Audit/IA
│   │   │   ├── ConnectorsPage.jsx # ⭐ NEW
│   │   │   └── WatchersPage.jsx   # ⭐ NEW
│   │   ├── components/     # DemoBanner, UpgradeWizard
│   │   ├── contexts/       # DemoContext
│   │   ├── services/
│   │   │   └── api.js      # 15+ API functions
│   │   └── App.jsx         # Router + nav
│   └── vite.config.js
├── docs/                   # Documentation
│   ├── regops_ultimate.md  # ✅ Complete guide
│   ├── audit/              # ⭐ THIS AUDIT
│   ├── security/           # RBAC, secrets, auth
│   ├── architecture/       # Bricks interfaces, ADRs
│   ├── kb/                 # Knowledge base
│   │   ├── sources/        # PDFs, regulations
│   │   ├── decisions/      # ADRs
│   │   ├── proofs/         # Evidence
│   │   ├── prompts/        # Claude prompts versioned
│   │   ├── regulations/    # YAML + mappings
│   │   └── playbooks/      # Runbooks
│   └── backlog/            # Proof backlog (ICE)
├── .env.example            # ✅ All env vars documented
└── .gitignore              # ⚠️ TO VERIFY - .env included?
```

---

## BRIQUE 1: REGOPS (COMPLET)

### Composants Implémentés ✅

#### Moteur Règles (4 régulations)
- **Tertiaire/OPERAT**: Scope ≥1000m², deadlines 2026-07-01 & 2026-09-30
  - Fichier: `backend/regops/rules/tertiaire_operat.py`
  - Config: `backend/regops/config/regs.yaml:1-12`
  - Tests: `tests/test_regops_rules.py:82-127` (4 cas, 0 pass - YAML mismatch)

- **BACS**: >290kW (2025), >70kW (2030)
  - Fichier: `backend/regops/rules/bacs.py`
  - Config: `backend/regops/config/regs.yaml:14-25`
  - Tests: `tests/test_regops_rules.py:135-187` (4 cas, 0 pass - YAML mismatch)

- **APER**: Parking solaire + toiture
  - Fichier: `backend/regops/rules/aper.py`
  - Config: `backend/regops/config/regs.yaml:26-38`
  - Tests: `tests/test_regops_rules.py:195-244` (4 cas, 0 pass - YAML mismatch)

- **CEE P6**: Audit énergétique
  - Fichier: `backend/regops/rules/cee_p6.py`
  - Config: `backend/regops/config/regs.yaml:40-41` + `cee_p6_catalog.yaml`
  - Tests: `tests/test_regops_rules.py:252-303` (4 cas, 0 pass - enum + YAML mismatch)

#### YAML Configs
- `regs.yaml`: 50 lignes, deadlines + thresholds + scoring weights
- `naf_profiles.yaml`: 20 NAF codes → usage families
- `location_profiles.yaml`: 13 régions → climate zones (H1/H2/H3)
- `cee_p6_catalog.yaml`: 10 action codes → CEE hints

#### Engine Orchestrator
- `backend/regops/engine.py`: evaluate_site(), evaluate_batch(), persist_assessment()
- Scoring: `100 - (Σ(severity × urgency × confidence) / total × 100)`
- Cache: Hash-based (deterministic_version + data_version)
- Performance: 3 queries bulk (sites, batiments, evidences)

#### API Endpoints (4)
- `GET /api/regops/site/{id}` → Fresh evaluation
- `GET /api/regops/site/{id}/cached` → From reg_assessments table
- `POST /api/regops/recompute` → Trigger recalcul (scope: site/entity/org/all)
- `GET /api/regops/dashboard` → Org KPIs

#### UI Page
- `frontend/src/pages/RegOps.jsx`:
  - Panel gauche "Audit (Règles)": Score, findings, actions déterministes, données manquantes
  - Panel droit "IA (Suggestions)": AI brief, suggestions (tagged), data quality

#### Tests
- Total: 16 cas
- Pass: 0 (100% fail - YAML config mismatch)
- Fichier: `tests/test_regops_rules.py`

### Composants Manquants ❌

1. **Regulation BREEAM**: Mentionné dans specs initiales mais pas implémenté
2. **Regulation RT2012/RE2020**: Pas couvert
3. **Evidence upload UI**: Pas de page upload documents
4. **Audit trail UI**: Pas de page historique modifications

---

## BRIQUE 2: BILL INTELLIGENCE (ABSENT - PREP REQUISE)

### Existant: ❌ RIEN

**Grep**: `grep -ri "bill\|facture\|invoice" backend/ frontend/`
- Résultats: Modèle `Evidence` avec type FACTURE, champ `anomalie_facture` dans Site
- **Conclusion**: Structure minimale, pas de feature Bill Intelligence

### À Préparer (sans coder)

#### Tables Attendues
- `energy_bills`: id, site_id, period_start, period_end, supplier, amount_eur, kwh_total, unit_price, tariff_type, pdf_url, parsed_at, quality_score
- `bill_anomalies`: id, bill_id, anomaly_type (PRICE_SPIKE, VOLUME_MISMATCH, TARIFF_ERROR), severity, detected_at, resolved_at, resolution_note
- `tariff_references`: id, supplier, tariff_name, valid_from, valid_to, price_kwh, subscription_eur

#### API Endpoints
- `POST /api/bills/upload` → Upload PDF + OCR
- `GET /api/bills/site/{id}` → Historique factures
- `GET /api/bills/{id}/anomalies` → Détection anomalies
- `POST /api/bills/{id}/validate` → Marquer validé
- `GET /api/bills/analytics` → Dashboard économies détectées

#### UI Pages
- `BillsPage.jsx`: Upload + liste + drill-down
- `BillAnalyticsPage.jsx`: Économies, anomalies, benchmarks

#### Sources Externes
- Connecteurs: Enedis, GRDF (factures auto-fetch)
- OCR: Tesseract ou AWS Textract
- Tarifs référence: CRE open data

#### Contrat Cross-Brick
- Input: DataPoint (metric="energy_cost_eur", source="bill_parser")
- Output: Finding (regulation="BILL_ANOMALY", severity, evidence_required=["FACTURE"])

---

## BRIQUE 3: SCÉNARIOS ACHAT POST-ARENH (ABSENT - PREP REQUISE)

### Existant: ❌ RIEN

**Grep**: `grep -ri "arenh\|achat\|procurement\|marche" backend/ frontend/`
- Résultats: Aucun
- **Conclusion**: Brique 3 totalement absente

### À Préparer (sans coder)

#### Tables Attendues
- `procurement_scenarios`: id, org_id, name, created_at, assumptions_json (volume_profile, risk_appetite, budget_constraint)
- `scenario_options`: id, scenario_id, option_type (SPOT, FORWARD_1Y, FORWARD_3Y, PPA, MIX), price_estimate, risk_score, pros_cons_json
- `market_data`: id, date, product (SPOT_FR, FORWARD_CAL+1), price_eur_mwh, source (EPEX, EEX)
- `hedging_strategies`: id, org_id, strategy_name, target_hedge_ratio, rebalance_frequency

#### API Endpoints
- `POST /api/procurement/scenarios` → Créer scénario
- `GET /api/procurement/scenarios/{id}/options` → Options recommandées
- `GET /api/procurement/market-data` → Prix actuels (SPOT, forwards)
- `POST /api/procurement/simulate` → Monte Carlo simulation
- `GET /api/procurement/analytics` → P&L scenarios, VaR

#### UI Pages
- `ProcurementPage.jsx`: Créer scénario + dashboard
- `ScenarioCompare.jsx`: Tableau comparatif options
- `MarketDataPage.jsx`: Courbes prix, calendrier spreads

#### Sources Externes
- Connecteurs: EPEX SPOT API, EEX forwards, RTE Transparency
- Data: Historical prices (3 ans min), forward curves

#### Contrat Cross-Brick
- Input: DataPoint (metric="annual_kwh_total" from RegOps)
- Output: Action (owner_role="PROCUREMENT_MANAGER", priority, effort, expected_impact="cost_reduction_eur")

---

## DONNÉES

### Seed Data (backend/scripts/seed_data.py)

**Contenu**:
- 1 Organisation (Groupe Casino)
- 1 Entité juridique
- 3 Portefeuilles
- 120 Sites (avec 12 champs RegOps: tertiaire_area_m2, parking, roof, OPERAT status, etc.)
- 120 Bâtiments (cvc_power_kw réaliste)
- ~300 Usages
- ~150 Obligations
- 46 Compteurs (meter_id + energy_vector)
- ~8400 Consommations (7j)
- 615 Evidences (dont BACS, audits)
- 20 Alertes actives
- 60 DataPoints (RTE CO2, PVGIS)
- 4 RegSourceEvents (actualité réglementaire)
- 120 RegAssessments (computed by engine)
- 4 JobOutbox entries (historique)

**Qualité**: ✅ Cohérent, réaliste, couvre tous les cas RegOps

### DataPoints Sources
1. **RTE eCO2mix** (REAL): Grid CO2 intensity
   - Metric: "grid_co2_intensity", unit: "gCO2/kWh"
   - Source: https://odre.opendatasoft.com/api/
   - Fréquence: Monthly aggregates (5 mois historique)

2. **PVGIS** (REAL): Solar production estimates
   - Metric: "pv_prod_estimate_kwh", unit: "kWh/year"
   - Source: https://re.jrc.ec.europa.eu/api/seriescalc
   - Input: lat/lon + roof_area_m2

3. **Enedis** (STUB): Meter data
   - Needs: OAuth client ID/secret
   - Metric: "meter_kwh_consumed"

4. **Météo-France** (STUB): Weather data
   - Needs: API key
   - Metric: "temperature_c", "heating_degree_days"

---

## SCRIPTS UTILES

| Script | Commande | Usage |
|--------|----------|-------|
| **Seed DB** | `python backend/scripts/seed_data.py` | Drop/recreate tables + 120 sites |
| **Run API** | `cd backend && python main.py` | Start FastAPI on :8000 |
| **Run Tests** | `cd backend && python -m pytest tests/ -v` | Run 98 test cases |
| **Job Worker** | `cd backend && python -m jobs.run --watch` | Process JobOutbox queue |
| **Frontend Dev** | `cd frontend && npm run dev` | Vite dev server :5173 |
| **Frontend Build** | `cd frontend && npm run build` | Production build → dist/ |

---

## GAPS & INCONSISTENCIES

1. **YAML keys**: Tests expect nested dict, _load_configs() returns flat? ⚠️ TO VERIFY
2. **TypeEvidence enum**: Manque AUDIT_ENERGETIQUE (tests CEE P6)
3. **Site model**: Pas de organisation_id direct (via portefeuille) → Fixture AI agents broken
4. **JobOutbox**: enqueue_job() retourne object pas ID
5. **Watcher names**: Registry retourne sans suffixe '_watcher', tests avec
6. **No auth**: Routes sensibles sans protection
7. **No logging**: Pas de structured logging
8. **No metrics**: Pas de /metrics Prometheus
9. **SQLite**: Pas production-ready (locks, concurrency)
10. **No migrations**: Pas d'Alembic (schema drift risk)
11. **Pydantic v1**: Warnings deprecated config (routes/schemas.py)
12. **SQLAlchemy 1.x**: Warning declarative_base deprecated (models/base.py:10)

---

**Prochaine étape**: TEST_REPORT.md (analyse détaillée des 26 test failures)
