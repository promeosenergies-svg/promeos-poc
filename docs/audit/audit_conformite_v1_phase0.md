# Audit Conformité v1 — Rapport intermédiaire Phase 0 (STOP GATE)

> **Date** : 2026-05-16 · **Branche** : `feat/m2-4-rollout` · **Mode** : 100 % READ-ONLY (aucun fichier source modifié)
> **Statut** : ⛔ STOP GATE — en attente de validation explicite avant Phase 1.
> **Périmètre** : module Conformité (Décret Tertiaire / BACS / APER / OPERAT / Audit SMÉ) — frontend + backend + tests.

---

## 0. Synthèse top-down (≤ 10 lignes)

Le module Conformité est **fonctionnellement riche mais structurellement fragmenté**. Côté frontend : **1 page canonique** (`/conformite`, 1000 LOC, propre — zéro calcul de score en JSX) + **4 pages tertiaire** + **2 pages `/compliance/*`** résiduelles + **1 page legacy morte**. Côté backend : **~60 fichiers Python**, **~900-1000 tests**, mais **4 moteurs d'évaluation parallèles** lisant **3 jeux de règles distincts**. La pondération scoring `regs.yaml` est correcte (DT 0.45 / BACS 0.30 / APER 0.25 = 1.00). **Violation cardinale C1 confirmée** : APER possède une **page dédiée (408 LOC)**, une **route `/conformite/aper`** et un **item sidebar** — les trois interdits par la doctrine. La DB ne contient qu'HELIOS (MERIDIAN absent). La baseline DT B (régression DJU `E=a×DJU+b` + r²) n'existe pas. **6 routes/pages, ~21 endpoints `/api/compliance/*`, ~900 tests** cartographiés. **3 anomalies P0 APER + 2 P0 data/calcul + 5 P1**.

---

## §1.1 — Routes & pages frontend (cartographie)

Router = `frontend/src/App.jsx` (pas de `router.jsx` séparé). Redirects legacy = `frontend/src/routes/legacyRedirects.js`. Tous les composants sont lazy-loaded.

| Route | Composant | Fichier | LOC | Lazy | Statut | Doublon ? |
|---|---|---|---|---|---|---|
| `/conformite` | `ConformitePage` | `pages/ConformitePage.jsx` | 1000 | oui (`App.jsx:33`) | **actif — canonique** | non |
| `/conformite/tertiaire` | `TertiaireDashboardPage` | `pages/tertiaire/TertiaireDashboardPage.jsx` | 580 | oui (`App.jsx:73`) | actif | non |
| `/conformite/tertiaire/wizard` | `TertiaireWizardPage` | `pages/tertiaire/TertiaireWizardPage.jsx` | 546 | oui (`App.jsx:74`) | actif | non |
| `/conformite/tertiaire/efa/:id` | `TertiaireEfaDetailPage` | `pages/tertiaire/TertiaireEfaDetailPage.jsx` | 1121 | oui (`App.jsx:75`) | actif | non |
| `/conformite/tertiaire/anomalies` | `TertiaireAnomaliesPage` | `pages/tertiaire/TertiaireAnomaliesPage.jsx` | 354 | oui (`App.jsx:76`) | actif | non |
| 🔴 `/conformite/aper` | `AperPage` | `pages/AperPage.jsx` | **408** | oui (`App.jsx:93,256`) | **actif — VIOLATION C1** | route dédiée interdite |
| `/regops/:id` | `RegOps` | `pages/RegOps.jsx` | 386 | oui (`App.jsx:38`) | **legacy/quasi-orphelin** (1 callsite `Site360.jsx:1908`, absent du rail) | partiel — chevauche `SiteCompliancePage` |
| `/compliance/pipeline` | `CompliancePipelinePage` | `pages/CompliancePipelinePage.jsx` | 369 | oui (`App.jsx:80`) | actif mais **caché** (`HIDDEN_PAGES`, `NavRegistry.js:1127`) | non |
| `/compliance/sites/:siteId` | `SiteCompliancePage` | `pages/SiteCompliancePage.jsx` | 732 | oui (`App.jsx:81`) | actif (deep-link, hors rail) | partiel — chevauche `/regops/:id` |
| `/compliance` *(redirect)* | — | `legacyRedirects.js:37` | — | — | redirect legacy → `/conformite` | OK |
| `/compliance/sites` *(redirect)* | — | `legacyRedirects.js:38` | — | — | redirect legacy → `/conformite` | OK |
| *(non routé)* | `CompliancePage` | `pages/CompliancePage.jsx` | 338 | non | **DEAD CODE** — `@deprecated LEGACY`, non importé hors tests | doublon mort de `ConformitePage` |

**Onglets `/conformite`** (`domain/compliance/complianceLabels.fr.js:133` `COCKPIT_TABS`) : `obligations` / `donnees` (« Données & Qualité ») / *(onglet 3 — label non confirmé, voir hypothèse H4)* / `preuves` (« Preuves & Rapports »). ⚠️ Le prompt §5.3 attend « Obligations, Données, Recommandations, Preuves » → écart de nommage à arbitrer.

---

## §1.2 — Backend (endpoints, services, modèles)

Fichier de routes principal : `backend/routes/compliance.py` (1002 lignes, prefix `/api/compliance`). Routes complémentaires : `regops.py`, `tertiaire.py`, `bacs.py`, `aper.py`, `operat.py`.

### Endpoints `/api/compliance/*` (extrait représentatif — ~21 endpoints)

| Endpoint | Méthode | Service | Modèle | Règle YAML | Tests | Statut |
|---|---|---|---|---|---|---|
| `/meta` | GET | `compliance_score_service` | — | `regs.yaml > scoring` | `test_compliance_score_service` | actif |
| `/bundle` | GET | `compliance_rules.get_compliance_bundle` | `ComplianceFinding` | `rules/decret_*_v1.yaml` | `test_compliance_bundle` (14) | actif — consommé par `ConformitePage` |
| `/summary` `/sites` | GET | `compliance_rules` | `ComplianceFinding` | `rules/decret_*_v1.yaml` | `test_compliance_scope` (13) | actif |
| `/recompute-rules` | POST | `compliance_rules.evaluate_organisation` | `ComplianceFinding` + `ComplianceRunBatch` | `rules/decret_*_v1.yaml` | `test_regops_rules` | actif |
| `/recompute` | POST | `compliance_coordinator` | `RegAssessment` | — | `test_compliance_coordinator` | actif (legacy snapshot) |
| `/findings` `/findings/{id}` | GET/PATCH | ORM directe | `ComplianceFinding` | — | `test_compliance_*` | actif |
| `/sites/{id}/score` `/portfolio/score` | GET | `compliance_score_service.compute_*` | `RegAssessment` | `regs.yaml > scoring` | `test_compliance_score_service` (27) + `_adaptive` (22) | **actif — SoT score A.2** |
| `/sites/{id}/summary` `/portfolio/summary` | GET | `compliance_readiness_service` | `RegAssessment` | `regs.yaml` | `test_compliance_v68` (21) | actif (V68) |
| `/score-trend` `/timeline` | GET | `compliance_score_trend` / `_build_timeline_events` (inline) | `ComplianceScoreHistory` / `ComplianceFinding`+`BacsAsset` | `regs.yaml` | — | actif |
| `/sites/{id}/packages` `/cee/dossier/*` `/mv/summary` | GET/POST/PATCH | `cee_service` | `WorkPackage` / `CeeDossier` | `cee_p6_catalog.yaml` | — | actif (CEE — hors score) |
| `sites.py:422 /{site_id}/compliance` | GET | — | — | — | — | **`deprecated=True`** |

### Services regops/compliance — rôles

| Service | Rôle | Note |
|---|---|---|
| `regops/engine.py` | **★ SoT scoring** — orchestre 5 évaluateurs, persiste `RegAssessment` | canonique |
| `services/compliance_score_service.py` | **★ Score unifié A.2** (0-100) — V1 figée + V2 adaptatif | canonique |
| `services/compliance_rules.py` | Évaluateur YAML legacy → `ComplianceFinding` ORM | déclaré `FUTURE-DEPRECATED` |
| `services/compliance_engine.py` | Pur wrapper de re-exports | **LEGACY mort** |
| `regops/scoring.py` | `compute_regops_score` / `score_explain` | **déclaré DÉPRÉCIÉ** |
| `services/compliance_coordinator.py` | `recompute_site/portfolio/organisation` | actif |
| `services/compliance_readiness_service.py` | Readiness gate V68 + summaries | actif |
| `services/bacs_engine.py` (+ `bacs_regulatory_engine`, `bacs_compliance_gate`, `bacs_alerts`, `bacs_ops_monitor`) | Moteur BACS V2 | actif |
| `services/audit_sme_service.py` | Audit énergétique / ISO 50001 | actif |
| `services/aper_service.py` | APER — dashboard + estimation PV PVGIS | ⚠️ sur-développé (voir §APER) |
| `services/operat_*` (`export`, `normalization`, `trajectory`) | OPERAT | ⚠️ baseline B absente |
| `services/tertiaire_*` | OPERAT/EFA | actif |
| `regulatory/applicability_service.py` + `regulatory/rules/*.py` | **Moteur d'assujettissement** (DT/BACS/APER/SMÉ/BEGES) — alimente Cockpit Stratégique | concern distinct, créé 13/05 |

---

## §1.3 — Sidebar / Navigation

Registry = `frontend/src/layout/NavRegistry.js`. Module `conformite` (emerald, `order: 2`, `NavRegistry.js:677-727`).

| Item sidebar | `to` | Ligne | Statut |
|---|---|---|---|
| « Conformité » | `/conformite` | `NavRegistry.js:686` | visible — item principal ✅ |
| « Décret Tertiaire / OPERAT » | `/conformite/tertiaire` | `NavRegistry.js:713` | visible ✅ |
| 🔴 **« Solarisation (APER) »** | `/conformite/aper` | `NavRegistry.js:720-724` | **visible — VIOLATION C1** |
| « Pipeline conformité » | `/compliance/pipeline` | `NavRegistry.js:1127` | dans `HIDDEN_PAGES` (caché — décision Phase 0.bis Q3) |

Autres : mapping module `'/conformite/aper': 'conformite'` (`NavRegistry.js:87`) · Quick Actions « Export OPERAT » / « Preuves manquantes » / « Corriger données » · `COMMAND_SHORTCUTS` « Voir la conformité » · `NavPanel.jsx:353-356` barre de progression DT/BACS/**APER** (encart % alimenté backend — **conforme**, ce n'est pas un menu).

🔴 **Flag rouge APER** : 1 item de menu + 1 route + 1 mapping module = APER traité comme un pilier de plein rang dans la nav, en violation directe de la contrainte C1.

---

## §1.4 — KPI & scoring conformité

### Pondération (vérifiée)

`backend/regops/config/regs.yaml:140-143` `scoring > framework_weights` :
```yaml
tertiaire_operat: 0.45   # Décret Tertiaire
bacs: 0.30               # Décret BACS
aper: 0.25               # Loi APER
```
**Somme = 1.00 ✓** — conforme à C4. Lu par `compliance_score_service.py:64-71` (avec fallback hardcodé). Dupliqué dans `regops/config/scoring_profile.json`.

### KPI conformité documentés

| KPI | Formule backend | Source | Pér. | Unité | Fichier | OK/KO |
|---|---|---|---|---|---|---|
| `compliance_score` (A.2) | `Σ(fw_score × poids) / Σ(poids dispo) − critical_penalty` ; `critical_penalty = min(20, n_crit × 5)` | `regs.yaml`, Décret 2019-771/2025-1343/Loi APER | snapshot | % 0-100 | `compliance_score_service.py:266-273` | **OK** |
| Pondération V2 adaptatif | poids recalculés à 100 % sur périmètre applicable, 6 dimensions | `_OFFICIAL_WEIGHTS_V2` `compliance_score_service.py:617` | snapshot | % | `compliance_score_service.py:739-842` | ⚠️ poids **hardcodés** |
| `trajectory_dt_progress` | `(conso_ref − conso_actuel)/(conso_ref × |jalon|)` | Décret 2019-771 | annuelle | % | `dt_progress_service` | OK |
| `_v2_score_aper` | sous-score 0-100 (100 engagement / 80 exemption / sinon findings) | — | snapshot | % | `compliance_score_service.py:698-705` | ⚠️ scoring chiffré APER dédié |
| pénalité finding | `estimated_penalty_eur` (float plat) + `penalty_source` + `penalty_basis` | variable | snapshot | € | `ComplianceFinding` | **KO — pas de `EurAmount` (C5)** |
| Bascule SMÉ #1 | composite post-scoring `0.84×findings + 0.16×SMÉ` | `WEIGHT_AUDIT_SME=0.16` | snapshot | % | `regops/engine.py:103-136` | ⚠️ incohérent avec #2 |
| Bascule SMÉ #2 | `audit_sme`(16)/`iso_50001`(20) intégré dans pondération relative V2 | — | snapshot | % | `compliance_score_service.py:766-772` | ⚠️ incohérent avec #1 |

⚠️ **Le jeu officiel C4 « DT 39 / BACS 28 / APER 17 / SMÉ 16 »** existe en constante (`doctrine/constants.py:343` `REGOPS_WEIGHTS_AUDIT_APPLICABLE`) et dans `audit_sme_service.py:280-282` (`0.39/0.28/0.17`) **mais n'est consommé par AUCUN moteur de score actif**.

### Baselines DT (C6)

| Baseline | Présence | Localisation |
|---|---|---|
| A — historique brut | ✓ partiel | `TertiaireEfa.reference_year` + `reference_year_kwh` ; `operat_trajectory.py:60` `TARGETS={2030:.60,2040:.50,2050:.40}` |
| **B — DJU-corrigé `E=a×DJU+b` + r²** | **❌ ABSENTE** | `operat_normalization.py:76` = ratio simple `conso × DJU_ref/DJU_obs`. Aucune régression, aucun a/b, aucun r². |
| C — année réf 2020 | ✓ champ libre | `TertiaireEfa.reference_year` (integer, non contraint à 2020) |

---

## §1.5 — Données (data dictionary conformité)

### Tables clés (30 tables liées identifiées) + counts DB

| Table | Colonnes clés | Rows DB |
|---|---|---|
| `compliance_findings` | site_id, regulation, rule_id, status, severity, deadline, evidence_json, estimated_penalty_eur, penalty_source/basis, engine_version | **15** |
| `compliance_run_batches` | org_id, triggered_by, started/completed_at, counts | **1** |
| `compliance_score_history` | site_id, org_id, month_key, score, grade, breakdown_json | **30** |
| `compliance_event_log` | entity_type/id, action, before/after_json, actor (audit-trail) | n/d |
| `reg_assessments` | object_type/id, computed_at, global_status, compliance_score, next_deadline, findings_json | **5** |
| `obligations` | type, statut (par site) | **9** |
| `tertiaire_efa` (+ `_consumption`, `_building`, `_dpe`, `_declaration`, `_proof_artifact`…) | statut, reference_year(_kwh), trajectory_status, baseline_normalization_status | **10** |
| `bacs_assets` (+ `_assessments`, `_inspections`, `_exemptions`…) | — | assets **5** / assessments **5** / exemptions **1** |
| `audit_energetique` | obligation, statut, score_audit_sme, sme_certifie_iso50001 | **1** |
| `eur_amounts` | montant tracé catégorie A/B + `CheckConstraint` | **0** (non utilisé par la conformité) |
| `operat_export_manifest` / `tertiaire_seuil_absolu` / `quality_findings` | — | **0** |

### Findings par pack (org HELIOS, id=1)

```
decret_tertiaire_operat : OK 2 / NOK 1 / UNKNOWN 2          → 5
bacs                    : OK 2 / NOK 1 / UNKNOWN 1 / OOS 1  → 5
aper                    : UNKNOWN 4 / OOS 1                 → 5
TOTAL = 15 findings
```

🔴 **MERIDIAN absent** : la DB `backend/data/promeos.db` ne contient qu'une org (`id=1 Groupe HELIOS`, 3 EJ, 5 sites). `compliance_findings` / `reg_assessments` / `compliance_run_batches` n'ont aucune donnée MERIDIAN. Seeds : `demo_seed/gen_compliance.py`, `gen_bacs.py`, `gen_tertiaire*.py`, `gen_audit_sme.py` (trigger MERIDIAN défini dans `packs.py` mais non appliqué).

### Traçabilité (doctrine)

| Champ doctrine | État |
|---|---|
| `source_article` | partiel — pas de colonne dédiée ; via `legal_ref` injecté à la persistance (`engine.py:355` → `regops/config/legal_refs.py`, ~13 rule_ids couverts, OPERAT/CEE/DPE manquants) |
| `evaluated_at` | partiel — équivalents `RegAssessment.computed_at`, `ComplianceFinding.created_at/updated_at` |
| `evidence_ref` | partiel — `evidence_json` (Text), pas de FK structurée |
| `EurAmount` cat. A/B + `CheckConstraint` | **modèle existe** (`models/eur_amount.py`) **mais NON appliqué à la conformité** — pénalités = floats plats sans contrainte |

---

## §1.6 — Tests

| Type | Fichiers | Nb tests (approx) | Couverture |
|---|---|---|---|
| BE unit — scoring/compliance core | `test_compliance_engine` (65), `_v1` (42), `_score_service` (27), `_score_adaptive` (26), `_v68` (23), `_contracts` (20), `_bundle` (14), `_evidence` (14), `_scope` (13), `_coordinator` (7), `_dual_engine` (7) | ~270 | **forte** |
| BE unit — BACS | `test_bacs_engine` (40), `_exemption` (17), `_api` (16), `_gate` (15), `_regulatory_engine` (15) + ~6 autres | ~190 | **forte** |
| BE unit — OPERAT | `test_operat_zones_climatiques` (78), `_cabs_service` (23), `_trajectory` (16), `_aper_enums` (15), `_hardening` (10), `_normalization` (8) | ~150 | **forte** |
| BE unit — DT/tertiaire | `test_phase9b_eti_tertiaire` (26), `test_rule_dt` (15), `step14_penalty`, `dt_progress`, `router_mount_tertiaire` (12) | ~70 | bonne |
| BE unit — APER | `test_step29_aper` (27), `test_rule_aper` (11), `test_site_aper_fields` (10) | ~48 | bonne |
| BE unit — Audit SMÉ | `test_rule_sme` (10) **seulement** — pas de `test_audit_sme_*` dédié | ~10 | **faible** |
| BE unit — RegOps | `test_regops_hardening` (30), `_rules` (40), `_dpe_tertiaire` (8), `_idor_multitenant_l35` (5) | ~85 | bonne |
| BE source-guards | `test_conformite_source_guards` (22), `_compliance_score_v2_adaptive` (3), `_regops_weights` (10), `_operat_cabs`, `_doctrine_sol`, `_applicability_engine`… | ~50+ | présents |
| FE unit (Vitest) | `NavRegistry.test.js` (88), `ConformitePage.test.js` (49), `complianceScoreConsistency.test.js` (42), `conformiteUxUpgrade` (29), `v14_questionnaire_conformite` (27), `RoutingSmoke` (25), `step21_conformite_messages` (22), `compliance_safety` (12) + 4 autres | ~346 | bonne |
| FE source-guards | `conformite_fe_source_guards.test.js` (8), `nav_fe_source_guards.test.js` (11) | 19 | présents |
| E2E (Playwright) | `e4-patrimoine-conformite.spec.js` (9), `audit-site360-conformity.spec.js` (9), `tertiaire-chips.spec.js` (3) | ~21 | moyenne |

**Total estimé conformité ≈ 900-1000 tests BE + ~365 FE + ~21 E2E.** Gap notable : **Audit SMÉ peu testé** ; **0 test** sur `AperPage.jsx`, les 4 pages `pages/tertiaire/*`, `RegOps.jsx`, `SiteCompliancePage.jsx` (732 LOC).

---

## §APER — Synthèse de la violation C1

| Vecteur | Localisation | Verdict |
|---|---|---|
| Page dédiée | `pages/AperPage.jsx` — **408 LOC** (BarChart Recharts, KPIs PV, timeline, estimation site) | 🔴 P0 — > 50 LOC |
| Route dédiée | `App.jsx:256` `<Route path="/conformite/aper">` + mapping `NavRegistry.js:87` | 🔴 P0 |
| Item sidebar | `NavRegistry.js:720-724` « Solarisation (APER) » (icône `Sun`) | 🔴 P0 |
| Backend sur-développé | `aper_service.py` (282 l. — dashboard + PVGIS), `routes/aper.py`, `regops/rules/aper.py` (251 l. — pénalités heuristiques `~20 €/m²` non sourcées), **triple implémentation** (`regops/rules/aper.py` + `regulatory/rules/aper.py` + `rules/loi_aper_v1.yaml`) | 🟠 P1 |
| Poids 25 % du score | `regs.yaml:143` | ✅ **conforme C4** — APER reste dans la pondération globale |

Encart APER **conforme** déjà présent : barre de progression `NavPanel.jsx:356` (% alimenté backend).

---

## Top 10 anomalies détectées (classées — sans correction)

| # | Anomalie | Sév. | Localisation | Contrainte |
|---|---|---|---|---|
| 1 | **APER — page dédiée** `AperPage.jsx` (408 LOC) | **P0** | `pages/AperPage.jsx` | C1 |
| 2 | **APER — route dédiée** `/conformite/aper` | **P0** | `App.jsx:256`, `NavRegistry.js:87` | C1 |
| 3 | **APER — item sidebar** « Solarisation (APER) » | **P0** | `NavRegistry.js:720-724` | C1 |
| 4 | **Baseline DT B absente** — pas de régression DJU `E=a×DJU+b` ni r² ; seule normalisation = ratio simple | **P0** | `operat_normalization.py:76` | C6 |
| 5 | **MERIDIAN absent de la conformité** — DB = HELIOS uniquement, aucun finding/assessment MERIDIAN | **P0** | `backend/data/promeos.db` | démo/pilote |
| 6 | **`EurAmount` non appliqué aux pénalités conformité** — floats plats `estimated_penalty_eur` sans `CheckConstraint` ni catégorie A/B | **P1** | `ComplianceFinding`, `models/eur_amount.py` | C5 |
| 7 | **2 bascules SMÉ incohérentes + poids officiel 39/28/17/16 jamais branché** dans un moteur de score actif | **P1** | `engine.py:103-136`, `compliance_score_service.py:766` | C4 |
| 8 | **4 moteurs d'évaluation parallèles + 3 jeux de règles** divergents (risque de scores incohérents entre `/bundle` UI et score A.2) | **P1** | `regops/engine.py`, `compliance_rules.py`, `compliance_engine.py`, `bacs_engine.py` | C2 |
| 9 | **Date OPERAT hardcodée en JSX** `new Date('2026-09-30')` (+ chemin doctrine cassé `__init__.py:12`, SHA256 inopérant) | **P1** | `TertiaireDashboardPage.jsx:157` ; `backend/doctrine/__init__.py:12` | C8 |
| 10 | **`CompliancePage.jsx` dead code** (338 LOC, `@deprecated`, non importé hors tests) | **P1** | `pages/CompliancePage.jsx` | doctrine §6 |

### Anomalies secondaires notées (annexe P2)

- **P2** — Heuristiques métier en frontend `ObligationsTab.jsx:168` (`maxSurface * 0.1` HVAC) et `:170` (`surface_m2 * 0.6` parking) pour bâtir le contexte KB. *(C8)*
- **P2** — `_build_timeline_events` (107 lignes de logique métier) inline dans `routes/compliance.py:734-973` au lieu d'un service.
- **P2** — Incohérence de nommage `/compliance/*` (EN) vs `/conformite/*` (FR) — routes actives `/compliance/pipeline`, `/compliance/sites/:id`.
- **P2** — Redondance fonctionnelle `RegOps.jsx` (386 LOC) ↔ `SiteCompliancePage.jsx` (732 LOC) — deux pages d'analyse conformité par site.
- **P2** — `legal_refs.py` couvre ~13 rule_ids ; OPERAT/CEE/DPE sans `legal_ref` → tooltip « NOR + date » manquant pour ces familles.
- **P2** — Couverture tests Audit SMÉ faible (10 tests) — échéance 11/10/2026 imminente.
- **P2** — `regops/scoring.py` et `compliance_engine.py` morts mais conservés (dette).
- **P2** — Libellés techniques anglais résiduels visibles : `ExecutionTab.jsx:188-189` (`source:`, `v{engine_version}`).
- **P2** — `regulatory_rates.js` (déprécié, fallback offline) : dates BACS `2027-01-01` et APER `2028-01-01` désalignées de la doctrine ; `acronyms.js:66` cite « 1ᵉʳ janv 2027 » BACS (obsolète, report 2030).

---

## Hypothèses prudentes (max 5)

1. **H1 — Fichier doctrine.** `docs/doctrine/doctrine_promeos_sol_v1_1.md` (cité dans le prompt) **n'existe pas**. La doctrine réelle est `docs/vision/promeos_sol_doctrine.md` (v1.1) — utilisée comme référence. C'est aussi le chemin cassé dans `backend/doctrine/__init__.py:12` (anomalie #9).
2. **H2 — Branche.** L'audit reflète `feat/m2-4-rollout` (et non `claude/refonte-sol2`). Les constats sont valides pour cette branche.
3. **H3 — Données démo.** La DB ne contient qu'HELIOS ; les counts findings (15) sont HELIOS uniquement. Je suppose que MERIDIAN doit être reseedé avant tout pilote — sans préjuger si c'est un défaut de seed ou un état attendu de la branche.
4. **H4 — Onglet 3 de `/conformite`.** Le label exact du 3ᵉ onglet (entre « Données » et « Preuves ») n'a pas été capturé (`complianceLabels.fr.js:136`). Le prompt §5.3 attend « Recommandations » ; le code semble exposer « Exécution ». À confirmer en Phase 1.
5. **H5 — Poids APER 25 %.** Le poids APER de 25 % dans le score global est tenu pour **doctrine-conforme** (C4 l'exige explicitement). Seule l'**interface de pilotage APER dédiée** (page/route/menu) est en violation — la suppression P0 ne touche pas la pondération.

---

## Questions bloquantes (max 3)

1. **Suppression APER — périmètre.** Confirmer le traitement cible : `/conformite/aper` → redirect `301` vers `/conformite#aper` ? La page `AperPage.jsx` (408 LOC, contient l'estimation PVGIS) est-elle **supprimée intégralement**, ou son estimation PV doit-elle être préservée (déplacée dans l'encart) ? Le service `aper_service.py` (PVGIS) reste-t-il pour alimenter l'encart, ou est-il aussi déprécié ?
2. **Pondération SMÉ.** Faut-il **implémenter le jeu officiel C4 « 39/28/17/16 »** dans le moteur de score actif (aujourd'hui présent en constante mais jamais branché) ? Et lequel des 2 moteurs de score (`regops/engine.py` post-scoring vs `compliance_score_service.py` V2 adaptatif) devient le canonique unique ?
3. **Baseline DT B.** La régression climatique DJU `E = a×DJU + b` avec suivi du r² (anomalie #4, effort important) est-elle **dans le périmètre de ce sprint**, ou traitée comme P0 documenté mais reporté à un sprint OPERAT dédié ?

---

## ⛔ STOP GATE

Phase 0 terminée. **Aucun fichier source modifié** (seul ce rapport a été créé dans `docs/audit/`).

➡️ **En attente de validation explicite avant de passer à la Phase 1 (diagnostic structuré).** Les 3 questions bloquantes ci-dessus orientent le périmètre de correction — une réponse même partielle suffit pour démarrer.
