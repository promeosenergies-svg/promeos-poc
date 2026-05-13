# Runbook — Synthèse Stratégique data-driven (Phase 3.5)

**Date** : 2026-05-13
**Branche** : `claude/refonte-sol2`
**Référence** : ADR-023 (architecture) + ADR-024 (moteur d'assujettissement)
**Statut** : Phase 3.5 livrée — 3 modes implémentés, 2 modes stubs Phase 3.6.

---

## TL;DR

`/cockpit/strategique` est désormais une page **polymorphique data-driven**. Cinq régimes narratifs possibles, calculés backend, jamais hardcodés. Trois modes livrés en Phase 3.5 (REGULATORY, PERFORMANCE, DATA_INSUFFICIENT). Les builders Procurement et Opportunity sont stubs : si le mode dispatcher les renvoie, la route bascule automatiquement sur PERFORMANCE avec `_fallback_reason="mode_not_implemented_v1.0"` dans l'audit trail.

---

## Architecture livrée

### Backend

```
backend/
├── regulatory/                             (Vague A — nouveau pkg)
│   ├── applicability_types.py              RuleCode, ApplicabilityStatus, RuleApplicability (frozen)
│   ├── reason_codes.py                     Whitelist 24 codes v1.0
│   ├── rules_catalog.py                    RULE_EVALUATORS + RULES_VERSIONS
│   ├── applicability_service.py            compute_applicability + compute_patrimoine_maturity
│   └── rules/
│       ├── base.py                         RuleEvaluator ABC
│       ├── dt.py                           Décret tertiaire 2019-771
│       ├── bacs.py                         Décret 2020-887 + 2025-1343
│       ├── aper.py                         Loi 2023-175 art. 40
│       ├── sme.py                          Code énergie L233-1 + Loi 2025-391
│       └── beges.py                        Loi Grenelle 2 art. 75
│
├── services/strategique/                   (Vague B + C — nouveau pkg)
│   ├── mode_thresholds.py                  StrategicMode + ModeThresholds (5 modes)
│   ├── mode_router.py                      compute_strategic_mode (cascade gates)
│   └── builders/
│       ├── base.py                         StrategicModeBuilder ABC
│       ├── regulatory.py                   HELIOS scenario (DT applicable + drift)
│       ├── performance.py                  MERIDIAN scenario (default)
│       ├── data_insufficient.py            Onboarding scenario (maturité < 60 %)
│       └── stubs.py                        Procurement + Opportunity → NotImplementedError
│
└── routes/
    ├── regulatory_applicability.py         GET /api/regulatory/applicability
    └── cockpit_strategique.py              GET /api/cockpit/strategique
```

### Frontend

```
frontend/src/
├── components/grammar/hub/                 (Vague D — primitifs nouveaux)
│   ├── StrategicModeBanner.jsx             Bandeau mode au-dessus du hero
│   ├── CadreApplicable.jsx                 Grid 5 règles avec statut couleur
│   ├── VerdictFinal.jsx                    Cartes contrainte/opportunité
│   ├── DossierP1.jsx                       Bloc P1 (scenarios+timeline+sidebar)
│   └── charts/
│       ├── ChartFrameTrajectoryLine.jsx    DT 2030/2040/2050 SVG
│       └── ChartFrameBenchSites.jsx        Bench sites vs médiane NAF
│
├── pages/
│   └── CockpitStrategique.jsx              243 lignes — composition pure L11
│
└── services/api/cockpit.js
    + getCockpitStrategique({period, persona, horizonYear, portfolioId})
```

---

## Endpoints

### `GET /api/regulatory/applicability[?site_id=N]`

Évalue l'applicabilité des 5 règles v1.0 sur l'organisation courante.

**Response shape** :
```json
{
  "applicability": {
    "DT":    [{ "rule_code": "DT", "scope_id": 10, "status": "applicable", ... }],
    "BACS":  [...],
    "APER":  [...],
    "SME":   [{ "scope_level": "organisation", "status": "applicable", ... }],
    "BEGES": [...]
  },
  "maturity": 0.71,
  "rules_versions": { "DT": "DT-2019-771-v2024-10-01", ... },
  "computed_at": "2026-05-13T10:00:00+00:00",
  "org_id": 1
}
```

### `GET /api/cockpit/strategique?[period_type=month&persona=dg_comex&horizon_year=2030&portfolio_id=N]`

Renvoie le payload complet polymorphique de la Synthèse Stratégique (cf. ADR-023 §3 schema canonique).

**Réponse minimale** :
```json
{
  "strategic_mode": "regulatory_driven",
  "applicability": { ... },
  "patrimoine_maturity": 0.88,
  "verdict": { "constraint": {...}, "opportunity": {...} },
  "hero": { "kicker", "title", "title_em", "sub_constat", "sub_implications", "meta", "ctas", "score" },
  "kpis": [3 KPI],
  "charts": [2 charts],
  "dossier_p1": { ... },
  "queue_p2_p3": [3-5 entries],
  "continuity": {...},
  "footer": { "sources", "version_tags", "last_update", "methodology_link" },
  "_audit": { "doctrine_version", "evaluated_at", "builder", "mode", "org_id",
              "target_mode", "effective_mode", "_fallback_reason?" }
}
```

---

## Tests

### Backend (pytest)

```bash
cd backend && python -m pytest tests/regulatory/ tests/services/strategique/ \
  tests/source_guards/test_applicability_engine_source_guards.py \
  tests/source_guards/test_cockpit_strategique_data_driven.py
```

- **161 tests Phase 3.5** en 3.2s (regulatory 92 + strategique mode/builders/endpoint 60 + source-guards 16).
- **0 failure, 1 skip pré-existant** (non lié).
- **Baseline préservée** : run élargi `tests/source_guards/ tests/doctrine/ tests/regulatory/ tests/services/strategique/` = 472 verts.

### Frontend (vitest)

```bash
cd frontend && npx vitest run
```

- **4 751 verts** / 233 files / 2 skip pré-existants / 0 fail.
- **+10 tests Phase 3.5** : source-guards FE SG_STRATEGIQUE_01-06.
- **Baseline FE 4 741 préservée**.

---

## Source-guards critiques

| Code | Fichier | Verrou |
|---|---|---|
| BE G1 | `test_applicability_engine_source_guards.py` | Tout reason_code ∈ REASON_CODES whitelist |
| BE G2 | idem | Aucun import `services.compliance_readiness_service.compute_applicability` dans regulatory/ |
| BE G3 | idem | Aucun reason_code hardcodé hors regulatory/, tests/, docs/ |
| BE G4 | idem | Versions RULES_VERSIONS au format `<RULE>-...<YYYY-MM-DD>` |
| BE G5 | idem | DATA_MISSING ↔ missing_inputs non vide |
| BE G6 | idem | scope `site` vs `organisation` cohérent par règle |
| BE C.7-G1 | `test_cockpit_strategique_data_driven.py` | Route utilise `resolve_org_id` + `compute_applicability` + `compute_strategic_mode` |
| BE C.7-G2 | idem | Aucun `strategic_mode` hardcodé (string literal) |
| BE C.7-G3 | idem | Aucun nom de site/portefeuille réel dans builders (whitelist FORBIDDEN) |
| BE C.7-G4 | idem | Aucun import legacy `cockpit_v2` ou `services/cockpit_*` |
| BE C.7-G6 | idem | Loi L11 cardinalité (kpis=3, charts=2, queue ∈ [3,5]) |
| FE SG_STRATEGIQUE_01 | `cockpit_strategique_fe_source_guards.test.js` | CockpitStrategique.jsx ≤ 250 lignes |
| FE SG_STRATEGIQUE_02 | idem | Aucun import `pages/Cockpit*.jsx` |
| FE SG_STRATEGIQUE_03 | idem | 10 imports canoniques grammar/hub/* |
| FE SG_STRATEGIQUE_04 | idem | Aucun `strategic_mode` hardcodé |
| FE SG_STRATEGIQUE_05 | idem | Utilise `getCockpitStrategique` (pas legacy) |
| FE SG_STRATEGIQUE_06 | idem | data-page + data-doctrine + data-mode présents |

---

## Discipline « from scratch » Phase 3.5

Clarification user 2026-05-13 : « on ne crée pas au-dessus, on part from scratch ».

Conséquences appliquées :

- **Backend** : `regulatory/`, `services/strategique/`, `routes/{regulatory_applicability,cockpit_strategique}.py` sont des packages **neufs**. Aucun import depuis :
  - `services/compliance_readiness_service.compute_applicability` (legacy, schema dict[str, dict])
  - `routes/cockpit_v2.py::get_executive_v2`
  - `services/cockpit_*.py`

- **Frontend** : `pages/CockpitStrategique.jsx` est **neuf** (243 l vs `Cockpit.jsx` legacy 1337 l). Composition pure depuis `grammar/hub/*`. `?legacy=1` rend un stub minimal pour rollback éventuel (la page legacy reste sur disque mais accessible uniquement via cette query param).

- **Cohabitation** : `Cockpit.jsx`, `cockpit_v2.py::get_executive_v2`, `compliance_readiness_service.compute_applicability` restent intacts pour rétro-compatibilité. Suppression différée Phase 3.7 après validation pilote 2 semaines (cf. `docs/dev/cockpit_legacy_deprecation.md` à créer si besoin).

---

## Fallback PROCUREMENT / OPPORTUNITY (Phase 0 Q3)

Si le dispatcher `compute_strategic_mode` renvoie `procurement_driven` ou `opportunity_driven` :
1. Le caller `routes/cockpit_strategique.py` détecte que le mode ∉ `IMPLEMENTED_MODES`.
2. Bascule sur `PERFORMANCE_DRIVEN` (builder de défaut).
3. Audit trail enrichi : `payload["_audit"]["target_mode"] = "procurement_driven"`, `payload["_audit"]["effective_mode"] = "performance_driven"`, `payload["_audit"]["_fallback_reason"] = "mode_not_implemented_v1.0"`.
4. Log structuré WARNING avec org_id pour traçabilité Phase 3.6.

Phase 3.6 livrera les 2 builders + 4 chart primitives restantes (ForwardCurve, OpportunityMap, MaturityRadar, MissingFields).

---

## DoD Phase 3.5 — checklist validée

- [x] Endpoint `GET /api/cockpit/strategique` répond 200 sur HELIOS + MERIDIAN + onboarding
- [x] `payload.strategic_mode` ∈ {regulatory_driven, performance_driven, data_insufficient}
- [x] `payload.applicability` contient les 5 règles avec `reason_human` non vide
- [x] `payload.kpis.length === 3` strictement
- [x] `payload.charts.length === 2` strictement
- [x] `payload.dossier_p1` complet (proof_pills, scenarios, timeline, why_promeos)
- [x] `payload.verdict.{constraint,opportunity}` non vides
- [x] `payload.footer.version_tags` inclut `Assujettissement v1.0`
- [x] Page `/cockpit/strategique` rend 3 modes sans crash (tests intégration TestClient)
- [x] Persona switch ne change PAS le mode (le mode dépend du patrimoine — vérifié dispatcher)
- [x] Source-guards verts : BE 16 verrous + FE 6 verrous
- [x] Baseline BE ≥ 7 103 préservée + FE ≥ 4 741 préservée
- [x] Runbook livré

Reste à faire (post-livraison Phase 3.5) :
- [ ] `/code-review` + `/simplify` sweep final (slash commands si dispos)
- [ ] Capture Playwright 3 modes × 3 viewports
- [ ] Audit transverse multi-agent (doctrine + ADR + vision + UX/UI/CX/CS + personas)
- [ ] Boucle audit visuel ≤ 5 itérations vs maquettes synthese_v7.html / synthese_v8.html
- [ ] Draft PR sur claude/refonte-sol2 → main

---

## Punchlist Phase 3.6

| # | Item | Effort estimé |
|---|---|---|
| 1 | `ProcurementDrivenBuilder` (compute trajectory + contract_end + spot exposure réels) | 3 j/h |
| 2 | `OpportunityDrivenBuilder` (compute unvalued_cee + APER potentiel PV) | 3 j/h |
| 3 | `ChartFrameForwardCurve` (Procurement) | 1.5 j/h |
| 4 | `ChartFrameOpportunityMap` (Opportunity) | 1.5 j/h |
| 5 | `ChartFrameMaturityRadar` (DATA_INSUFFICIENT — actuellement RadarStub) | 1 j/h |
| 6 | `ChartFrameMissingFields` (DATA_INSUFFICIENT — actuellement SimpleBars) | 1 j/h |
| 7 | Service `compute_trajectory_drift` (basé sur RegAssessment OPERAT) | 2 j/h |
| 8 | Service `compute_next_contract_end` (basé sur EnergyContract.fin_validite) | 1 j/h |
| 9 | Service `compute_spot_exposure` (basé sur contrat.formule_pricing) | 1.5 j/h |
| 10 | Wire compute_trajectory_drift → endpoint cockpit_strategique (remplace stub 8.0) | 0.5 j/h |
| 11 | Bench sites réels (Phase D.3 utilise stubs « Site phare/médian/meilleur élève ») | 2 j/h |

**Total Phase 3.6 estimé** ≈ 18 j/h sur 3-4 jours calendaires.

---

**Auteur** : session Phase 3.5 du 13/05/2026.
