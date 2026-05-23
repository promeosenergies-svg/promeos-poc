# Audit Conformité PROMEOS — Front + Back — READ-ONLY

> **Date** : 2026-05-16 · **Branche** : `feat/m2-4-rollout` · **Mode** : 100 % READ-ONLY (aucun fichier source modifié)
> **Périmètre** : module Conformité (Décret Tertiaire / BACS / APER / OPERAT / Audit SMÉ) — frontend + backend + tests + données.
> **Rapport Phase 0 lié** : [audit_conformite_v1_phase0.md](audit_conformite_v1_phase0.md)

---

## 1. Résumé exécutif

- **Note globale** : **5.5 / 10**
- **Verdict** : **STOP GATE** — 3 P0 cardinaux à arbitrer avant correction (APER suppression, baseline DT B, MERIDIAN seed).
- **5 constats majeurs**
  1. 🔴 **Violation cardinale C1 « APER = encart seulement »** : APER possède une page dédiée [AperPage.jsx](frontend/src/pages/AperPage.jsx) **408 LOC**, une route `/conformite/aper` et un item sidebar « Solarisation (APER) » — les trois interdits.
  2. 🟠 **Fragmentation backend lourde** : **4 moteurs d'évaluation parallèles** (`regops/engine.py`, `compliance_engine.py`, `compliance_rules.py`, `bacs_engine.py`) lisant **3 jeux de règles distincts** (`regs.yaml`, `rules/decret_*_v1.yaml`, `regulatory/rules/*.py`). Risque de scores incohérents entre `/api/compliance/bundle` (UI) et le score A.2.
  3. 🟠 **Pondération SMÉ jamais branchée** : le jeu officiel C4 « DT 39 / BACS 28 / APER 17 / SMÉ 16 » existe en constante `doctrine/constants.py:343` (`REGOPS_WEIGHTS_AUDIT_APPLICABLE`) mais **aucun moteur de score actif ne le consomme**. Deux bascules SMÉ incohérentes coexistent (`engine.py:103-136` post-scoring vs `compliance_score_service.py:766` V2 adaptatif).
  4. 🟠 **Baseline DT B absente** : pas de régression DJU `E = a×DJU + b` avec r². [operat_normalization.py:76](backend/services/operat_normalization.py#L76) implémente une normalisation ratio simple → trajectoire `-40/-50/-60 %` non climatiquement rigoureuse → non défendable face à OPERAT.
  5. 🟠 **`EurAmount` non appliqué aux pénalités conformité** : les `estimated_penalty_eur` sont des floats plats sans `CheckConstraint` ni catégorie A/B (le modèle traçable existe `models/eur_amount.py` mais n'est utilisé que par le Cockpit — table `eur_amounts` = **0 row**). Violation contrainte C5 « traçabilité euro ».

**Couverture cartographiée** : 12 routes/pages frontend · ~21 endpoints `/api/compliance/*` (+ regops, tertiaire, bacs, aper, operat) · ~60 fichiers backend Python · ~900-1000 tests BE / ~365 FE / ~21 E2E · 30 tables DB (HELIOS uniquement, MERIDIAN absent).

---

## 2. Cartographie navigation frontend

Registry = [frontend/src/layout/NavRegistry.js](frontend/src/layout/NavRegistry.js) (module `conformite` emerald, `order: 2`, lignes 677-727). Router = [frontend/src/App.jsx](frontend/src/App.jsx) (pas de `router.jsx`). Redirects legacy = [frontend/src/routes/legacyRedirects.js](frontend/src/routes/legacyRedirects.js).

| Route | Label menu | Composant | Fichier | Statut | Problème | Priorité |
|---|---|---|---|---|---|---|
| `/conformite` | « Conformité » | `ConformitePage` | [pages/ConformitePage.jsx](frontend/src/pages/ConformitePage.jsx) | actif **canonique** | onglet 3 « Plan d'exécution » ≠ « Recommandations » attendu par doctrine cible | P1 |
| `/conformite/tertiaire` | « Décret Tertiaire / OPERAT » | `TertiaireDashboardPage` | [pages/tertiaire/TertiaireDashboardPage.jsx](frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx) (580 LOC) | actif | `new Date('2026-09-30')` hardcodé `:157` → C8 | P1 |
| `/conformite/tertiaire/wizard` | — | `TertiaireWizardPage` (546 LOC) | actif sub-route | — | OK |
| `/conformite/tertiaire/efa/:id` | — | `TertiaireEfaDetailPage` (**1121 LOC**) | actif sub-route | aucun test | P2 |
| `/conformite/tertiaire/anomalies` | — | `TertiaireAnomaliesPage` (354 LOC) | actif sub-route | — | OK |
| 🔴 **`/conformite/aper`** | 🔴 **« Solarisation (APER) »** | `AperPage` | [pages/AperPage.jsx](frontend/src/pages/AperPage.jsx) **408 LOC** | **actif — VIOLATION C1** | route + menu + page interdits par doctrine | **P0** |
| `/regops/:id` | *(absent du rail)* | `RegOps` (386 LOC) | [pages/RegOps.jsx](frontend/src/pages/RegOps.jsx) | quasi-orphelin — 1 callsite `Site360.jsx:1908` + 1 fixture `evidence.fixtures.js:25` | redondance avec `SiteCompliancePage` | P1 |
| `/compliance/pipeline` | « Pipeline conformité » (caché) | `CompliancePipelinePage` (369 LOC) | actif **caché** (`HIDDEN_PAGES`, `NavRegistry.js:1127`) | nommage `/compliance/*` EN + label « Pipeline » EN | P2 |
| `/compliance/sites/:siteId` | *(deep-link)* | `SiteCompliancePage` (**732 LOC**) | actif hors rail | redondance avec `RegOps` + préfixe EN | P1 |
| `/compliance` *(redirect)* | — | — | `legacyRedirects.js:37` → `/conformite` | OK | — |
| `/compliance/sites` *(redirect)* | — | — | `legacyRedirects.js:38` → `/conformite` | OK | — |
| *(non routé)* | — | `CompliancePage` (338 LOC) | [pages/CompliancePage.jsx](frontend/src/pages/CompliancePage.jsx) | **DEAD CODE** `@deprecated LEGACY` | suppression jamais faite (commentaire « prochain sprint de nettoyage ») | P1 |

### Quick Actions, raccourcis et indicateurs nav (extraits)
- [NavRegistry.js:533](frontend/src/layout/NavRegistry.js#L533) « Export OPERAT » → `/conformite/tertiaire` ✅
- [NavRegistry.js:540](frontend/src/layout/NavRegistry.js#L540) « Preuves manquantes » → `/conformite?tab=preuves` ✅
- [NavRegistry.js:556](frontend/src/layout/NavRegistry.js#L556) « Corriger données » → `/conformite?tab=donnees` ✅
- [NavRegistry.js:1212-1218](frontend/src/layout/NavRegistry.js#L1212-L1218) `COMMAND_SHORTCUTS` « Voir la conformité » → `/conformite` ✅
- [NavPanel.jsx:353-356](frontend/src/layout/NavPanel.jsx#L353-L356) barre de progression DT / BACS / APER — affichage % alimenté backend ✅ **conforme (encart léger)**

### Onglets `/conformite` (cartographie réelle)

[domain/compliance/complianceLabels.fr.js:133-138](frontend/src/domain/compliance/complianceLabels.fr.js#L133-L138) :
```
obligations · donnees (« Données & Qualité ») · execution (« Plan d'exécution ») · preuves (« Preuves & Rapports »)
```
⚠️ Doctrine cible attend **« Recommandations »** en onglet 3 ; le code expose **« Plan d'exécution »** → écart sémantique à arbitrer.

---

## 3. Cartographie pages et composants

| Page/composant | Rôle | Fichier | LOC | Données consommées | Doublon ? | Risque |
|---|---|---|---|---|---|---|
| `ConformitePage` | Hub Conformité (4 onglets) | [pages/ConformitePage.jsx](frontend/src/pages/ConformitePage.jsx) | 1000 | `getComplianceBundle()`, `/api/compliance/sites/:id/score`, `/portfolio/score`, `/api/compliance/recompute-rules` | non | aucun (page propre, 0 calcul métier) ✅ |
| `ObligationsTab` | Onglet 1 — liste obligations + KB | `pages/conformite-tabs/ObligationsTab.jsx` | n/d | findings, sites, KB context | non | **P2** : 2 heuristiques métier en frontend (`maxSurface * 0.1` HVAC `:168`, `surface_m2 * 0.6` parking `:170`) |
| `PreuvesTab` | Onglet 4 — preuves & rapports | `pages/conformite-tabs/PreuvesTab.jsx` | n/d | `proofFiles`, `obligations` | non | OK (sommes triviales d'affichage) |
| `ExecutionTab` | Onglet 3 — plan d'exécution | `pages/conformite-tabs/ExecutionTab.jsx` | n/d | findings, actions | non | **P2** : libellés techniques anglais `source:`, `v{engine_version}` visibles `:188-189` |
| `TertiaireDashboardPage` | Sous-cockpit OPERAT/EFA | [pages/tertiaire/TertiaireDashboardPage.jsx](frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx) | 580 | `/api/tertiaire/*`, `getOperatStatus`, `getOperatDeadlines` | non | **P1** : `new Date('2026-09-30')` hardcodé `:157` (C8) |
| `TertiaireWizardPage` | Wizard saisie OPERAT | `pages/tertiaire/TertiaireWizardPage.jsx` | 546 | EFA POST | non | aucun test dédié |
| `TertiaireEfaDetailPage` | Détail EFA + conso historiques | `pages/tertiaire/TertiaireEfaDetailPage.jsx` | **1121** | `/api/tertiaire/efa/:id/*` | non | **P2** taille + 0 test |
| `TertiaireAnomaliesPage` | Anomalies données tertiaire | `pages/tertiaire/TertiaireAnomaliesPage.jsx` | 354 | `/api/tertiaire/anomalies` | non | aucun test |
| 🔴 `AperPage` | Dashboard PV + estimation PVGIS + timeline | [pages/AperPage.jsx](frontend/src/pages/AperPage.jsx) | **408** | `aperApi.getDashboard`, `aperApi.estimateSite` | **interdit (doctrine)** | **P0 suppression** |
| `RegOps` | Vue analyse conformité site (legacy) | [pages/RegOps.jsx](frontend/src/pages/RegOps.jsx) | 386 | `/api/regops/*` | **partiel** avec `SiteCompliancePage` | **P1** quasi-orphelin (1 callsite) |
| `CompliancePipelinePage` | Pipeline RegOps (workflow batch) | `pages/CompliancePipelinePage.jsx` | 369 | `/api/compliance/recompute-rules`, `/findings` | non | caché — décision Phase 0.bis Q3 |
| `SiteCompliancePage` | Vue conformité par site (deep-link) | `pages/SiteCompliancePage.jsx` | **732** | `/api/compliance/sites/:id/*` | **partiel** avec `RegOps` | **P1** redondance + 0 test |
| `CompliancePage` | Page legacy morte | [pages/CompliancePage.jsx](frontend/src/pages/CompliancePage.jsx) | 338 | — | **doublon mort** | **P1** suppression |

### Wrappers API frontend conformité
- [services/api/conformite.js](frontend/src/services/api/conformite.js) (13 KB) — `getComplianceBundle`, `getRegOpsAssessment`, `getRegOpsDashboard`, `getRegOpsScoreExplain`, `getAuditSmeAssessment`, `recomputeComplianceRules`, etc.
- Hook : `frontend/src/hooks/useComplianceMeta.js`.
- Contexte : `frontend/src/contexts/RegulatoryConstantsContext.jsx` (fetch `/api/config/regulatory-constants` + `FALLBACK_CONSTANTS`).
- Labels FR : [domain/compliance/complianceLabels.fr.js](frontend/src/domain/compliance/complianceLabels.fr.js) (`REG_LABELS`, `STATUT_LABELS`, `COCKPIT_TABS`).

### États gérés sur `/conformite` (`ConformitePage.jsx`)
✅ `loading` (lignes 580-587, `<SkeletonKpi>` + `<SkeletonTable>`) · `error` (589-640, `<ErrorState>` + retry + debug expert) · `empty` (751-766, `<EmptyState>` piloté par `emptyReason`).

### Labels anglais visibles utilisateur
Seules occurrences résiduelles : `ExecutionTab.jsx:188-189` (`source:`, `v{engine_version}`). Aucun « compliance », « finding », « pipeline », « kind », « domain » EN visible utilisateur dans la page principale. Le wording côté nav est en français ✅.

---

## 4. Cartographie backend / API

Fichier principal : [backend/routes/compliance.py](backend/routes/compliance.py) (**1002 lignes**, prefix `/api/compliance`). Routes complémentaires : `regops.py`, `tertiaire.py`, `bacs.py`, `aper.py`, `operat.py`.

### 4.1 Endpoints `/api/compliance/*` (extrait représentatif, ~21 endpoints)

| Endpoint | Méthode | Router | Service | Modèle | Règles | Tests | Risque |
|---|---|---|---|---|---|---|---|
| `/meta` | GET | `compliance.py` | `compliance_score_service` | — | `regs.yaml > scoring` | `test_compliance_score_service` | aucun |
| `/bundle` | GET | `compliance.py` | `compliance_rules.get_compliance_bundle` | `ComplianceFinding` | `rules/decret_*_v1.yaml` | `test_compliance_bundle` (14) | **incohérence** avec `regs.yaml` (2 jeux de seuils) |
| `/summary` `/sites` | GET | `compliance.py` | `compliance_rules` | `ComplianceFinding` | `rules/decret_*_v1.yaml` | `test_compliance_scope` (13) | idem |
| `/recompute-rules` | POST | `compliance.py` | `compliance_rules.evaluate_organisation` | `ComplianceFinding` + `ComplianceRunBatch` | `rules/decret_*_v1.yaml` | `test_regops_rules` | idem |
| `/recompute` | POST | `compliance.py` | `compliance_coordinator` | `RegAssessment` | — | `test_compliance_coordinator` | snapshot legacy |
| `/findings` `/findings/{id}` | GET/PATCH | `compliance.py` | ORM directe | `ComplianceFinding` | — | — | OK |
| `/batches` | GET | `compliance.py` | ORM directe | `ComplianceRunBatch` | — | — | OK |
| `/sites/{id}/score` `/portfolio/score` | GET | `compliance.py` | `compliance_score_service.compute_*` | `RegAssessment` | `regs.yaml > scoring` | `test_compliance_score_service` (27) + `_adaptive` (22) | ✅ SoT score A.2 |
| `/sites/{id}/summary` `/portfolio/summary` | GET | `compliance.py` | `compliance_readiness_service` | `RegAssessment` | `regs.yaml` | `test_compliance_v68` (21) | V68 OK |
| `/score-trend` | GET | `compliance.py` | `compliance_score_trend` | `ComplianceScoreHistory` | — | — | OK |
| `/timeline` | GET | `compliance.py` | `_build_timeline_events` **inline (107 l.)** | `ComplianceFinding`+`BacsAsset` | `regs.yaml` | — | **P2** logique métier dans la route |
| `/sites/{id}/packages` `/cee/dossier/*` `/mv/summary` | GET/POST/PATCH | `compliance.py` | `cee_service` | `WorkPackage`/`CeeDossier` | `cee_p6_catalog.yaml` | — | hors score |
| `sites.py:422 /{site_id}/compliance` | GET | `sites.py` | — | — | — | — | **`deprecated=True`** |

### 4.2 Endpoints connexes
- `/api/regops/*` (`backend/routes/regops.py`) : `/dashboard`, `/score_explain`, `/data_quality`, `/audit-sme/scope`, `/audit-deadline-status`, `/recompute`, `/bacs/asset`, `/bacs/seed_demo` — fortement consommés par le frontend.
- `/api/tertiaire/*` — OPERAT/EFA workflow complet (declare conso, proofs, perimeter events).
- `/api/bacs/*` — assessments, inspections, exemptions, remediation.
- `/api/aper/*` (`backend/routes/aper.py`) : 2 endpoints — `getDashboard`, `estimateSite` (PVGIS).
- `/api/operat/*` — export CSV, normalisation DJU.
- `/api/config/regulatory-constants` — SoT runtime constantes (alimente `RegulatoryConstantsContext`).

### 4.3 Services backend conformité (rôles)

| Service | Rôle | Statut |
|---|---|---|
| `regops/engine.py` | **★ SoT scoring** — orchestre 5 évaluateurs (tertiaire/bacs/aper/dpe/cee_p6), persiste `RegAssessment` | canonique |
| `services/compliance_score_service.py` | **★ Score A.2** unifié (0-100) — V1 figée + V2 adaptatif | canonique |
| `services/compliance_rules.py` | Évaluateur YAML legacy → `ComplianceFinding` ORM | `FUTURE-DEPRECATED` |
| `services/compliance_engine.py` | Pur wrapper de re-exports | **mort** |
| `regops/scoring.py` | `compute_regops_score` / `score_explain` | **déprécié** |
| `services/compliance_coordinator.py` | `recompute_site/portfolio/organisation` | actif |
| `services/compliance_readiness_service.py` | Readiness gate V68 + summaries | actif |
| `services/compliance_rule_mapping.py` | Mapping rule_ids inter-moteurs (anti-dérive) | actif — symptôme de la fragmentation |
| `services/bacs_engine.py` (+ `bacs_regulatory_engine`, `bacs_compliance_gate`, `bacs_alerts`, `bacs_ops_monitor`) | Moteur BACS V2 | actif |
| `services/audit_sme_service.py` | Audit énergétique / ISO 50001 | actif |
| `services/aper_service.py` | APER dashboard + estimation PV PVGIS | ⚠️ sur-développé (cf. §7) |
| `services/operat_*` (export, normalization, trajectory, mutualisation, modulation, proofs) | OPERAT | ⚠️ baseline B absente |
| `services/tertiaire_*` | OPERAT/EFA qualification | actif |
| `regulatory/applicability_service.py` + `regulatory/rules/*.py` | **Moteur d'assujettissement** (DT/BACS/APER/SMÉ/BEGES) alimente Cockpit Stratégique | concern distinct, créé 13/05 |

### 4.4 Risques d'incohérence backend
- **R1 — 2 jeux de seuils YAML** : `regops/config/regs.yaml` (lu par `compliance_score_service`) vs `backend/rules/decret_*_v1.yaml` (lu par `compliance_rules`). Divergence silencieuse possible.
- **R2 — UI ≠ score A.2** : `ConformitePage` consomme `/api/compliance/bundle` (`compliance_rules`) tandis que le score A.2 vient de `regops/engine.py` (`compliance_score_service`). Deux familles de findings → potentiel d'affichage incohérent.
- **R3 — Triple implémentation APER/BACS** : `regops/rules/{aper,bacs}.py` + `regulatory/rules/{aper,bacs}.py` + `rules/decret_*_v1.yaml`. `regulatory/rules/` (nouveau) est sémantiquement distinct (assujettissement), mais nommage trop proche.
- **R4 — `/timeline` inline** : `_build_timeline_events` (107 lignes — comptage findings, puissance CVC, pénalités) dans `routes/compliance.py:734-973` au lieu d'un service dédié → testabilité dégradée.

---

## 5. Scoring et règles réglementaires

### 5.1 Pondérations

[backend/regops/config/regs.yaml:140-143](backend/regops/config/regs.yaml#L140-L143) `scoring > framework_weights` :
```yaml
tertiaire_operat: 0.45   # Décret n°2019-771
bacs: 0.30               # Décret n°2025-1343 (alignement EPBD)
aper: 0.25               # Loi 2023-175 art. 40
# DPE et CSRD : évaluateurs non implémentés, poids exclus
```
**Somme = 1.00** ✅ — conforme C4 (mode standard). Lu par [compliance_score_service.py:64-71](backend/services/compliance_score_service.py#L64-L71) avec fallback hardcodé.

### 5.2 Table scoring & règles

| Réglementation | Source règle | Moteur | Pondération | Formule | Problème | Correction cible |
|---|---|---|---|---|---|---|
| **Décret Tertiaire / OPERAT** | `regs.yaml > tertiaire` (seuils Cabs annexe II) + `rules/decret_tertiaire_v1.yaml` + `regops/rules/tertiaire_operat.py` | `regops/engine.py` + `compliance_rules.py` | **0.45** (V1) / 39 % (jeu C4 jamais branché) | `(C_ref − C_actuel)/(C_ref × |jalon|)` ; baseline ratio simple | **baseline B (régression DJU `E=a×DJU+b` + r²) absente** [operat_normalization.py:76](backend/services/operat_normalization.py#L76) | implémenter régression linéaire + tracking r² ; archiver coefficients par EFA |
| **Décret BACS** | `regs.yaml > bacs` + `rules/decret_bacs_v1.yaml` + `regops/rules/bacs.py` + `services/bacs_engine.py` + `services/bacs_regulatory_engine.py` | 4 services BACS distincts | **0.30** (V1) / 28 % (C4) | classe ISO 52120-1 ∈ {A,B,C} + Putile + TRI | seuils 290 kW (en service) / 70 kW (2030) corrects ; pénalité 1500 €/an OK | unifier les 4 services BACS sous un orchestrateur |
| **Loi APER** | `regs.yaml > aper` + `rules/loi_aper_v1.yaml` + `regops/rules/aper.py` (251 l.) + `regulatory/rules/aper.py` (205 l.) | triple implémentation | **0.25** (V1) / 17 % (C4) | `surface_solarisée / surface_concernée ≥ 50 %` | pénalités heuristiques `~20 €/m²` / `~15 €/m²` **non sourcées réglementairement** (`penalty_source="estimation"`) — `regops/rules/aper.py` | sourcer le coefficient ou retirer le montant ; ramener au sous-score minimal nécessaire au poids 25 % |
| **Audit SMÉ / ISO 50001** | `services/audit_sme_service.py` + `regulatory/rules/sme.py` | service dédié | **0.16** (jeu C4) ou intégré V2 adaptatif | seuil 2.75 GWh (audit) / 23.6 GWh (ISO 50001) ; échéance 11/10/2026 | **2 bascules SMÉ incohérentes** : `engine.py:103-136` post-scoring `0.84×findings + 0.16×SMÉ` vs `compliance_score_service.py:766` V2 dimension supplémentaire — le jeu officiel 39/28/17/16 défini en constante mais **jamais utilisé** | unifier sur un moteur ; brancher `REGOPS_WEIGHTS_AUDIT_APPLICABLE` |
| **BEGES / CSRD** | `regulatory/rules/beges.py` | service applicability | **0** dans le score conformité | seuil PME (250 ETP / 50 M€ CA / 43 M€ bilan) | hors périmètre score A.2 (assujettissement uniquement) | maintenir séparé (Cockpit Stratégique) |
| **CEE P5 → P6** | `cee_p6_catalog.yaml` + `services/cee_service.py` | service dédié | **0** dans le score conformité | calcul kWhc cumac par fiche BAT-* | financement, hors score | maintenir séparé |

### 5.3 KPI conformité documentés (réels backend)

| KPI | Formule | Source | Période | Unité | Fichier |
|---|---|---|---|---|---|
| `compliance_score` (A.2) | `Σ(fw_score × poids) / Σ(poids dispo) − critical_penalty` ; `critical_penalty = min(20, n_crit × 5)` | `regs.yaml` + Décret 2019-771 / 2025-1343 / Loi APER | snapshot | % 0-100 | [compliance_score_service.py:266-273](backend/services/compliance_score_service.py#L266-L273) |
| `trajectory_dt_progress` | `(C_ref − C_actuel)/(C_ref × |jalon|)` | Décret 2019-771 | annuelle glissante | % | `services/dt_progress_service.py` |
| `_v2_score_aper` | 100 (engagement) / 80 (exemption) / fallback findings | — | snapshot | % | [compliance_score_service.py:698-705](backend/services/compliance_score_service.py#L698-L705) |
| `bacs_status` | `installed AND class ∈ {A,B,C} AND inspection_valid` | Décret 2025-1343 | snapshot | bool | `services/bacs_engine.py` |
| `aper_status` (cible doctrine) | `parking_surface ≥ 1500 m² ? "concerned" : "not_concerned"` | Loi APER art. 40 | snapshot | enum | **À CRÉER** |
| `audit_sme_score` | composite findings + statut ISO 50001 | Loi 2025-391 | snapshot | % | `services/audit_sme_service.py` |
| `compliance_score_history.month_key` | snapshot mensuel persisté | — | mensuel | % | `models/compliance_score_history.py` |
| `readiness_score` | `0.30 × data + 0.40 × conformity + 0.30 × actions` | — | snapshot | % | `services/compliance_readiness_service.py` |

### 5.4 Logique métier en frontend (audit C8)

| Fichier:ligne | Extrait | Verdict |
|---|---|---|
| `ConformitePage.jsx:982` | `reduce((s, f) => s + (f.estimated_penalty_eur ‖ 0), 0)` | ✅ somme triviale d'affichage (valeurs déjà calculées backend) |
| `PreuvesTab.jsx:168,172` | reduce sur `obligations` / `proofFiles` | ✅ comptes triviaux |
| `ObligationsTab.jsx:166,696` | reduce sur surfaces / pénalités | ✅ trivial |
| ⚠️ `ObligationsTab.jsx:168` | `Math.round(maxSurface * 0.1)` (estimation HVAC) | **P2** — coefficient métier en frontend |
| ⚠️ `ObligationsTab.jsx:170` | `Math.round(largeSites[0].surface_m2 * 0.6)` (estimation parking) | **P2** — coefficient métier en frontend |
| 🔴 `TertiaireDashboardPage.jsx:157` | `new Date('2026-09-30')` daysToOperat | **P1** — date hardcodée, ignore `RegulatoryConstantsContext` |

**Verdict global C8** : la page Conformité principale est **propre** (score = pure consommation backend). 3 violations résiduelles (1 P1, 2 P2) sur sous-pages.

---

## 6. Incohérences UX / métier / data

### P0 — Bloquant (à corriger avant toute démo)

| # | Anomalie | Loc | Contrainte |
|---|---|---|---|
| P0.1 | **APER — page dédiée** `AperPage.jsx` (408 LOC) | [pages/AperPage.jsx](frontend/src/pages/AperPage.jsx) | C1 |
| P0.2 | **APER — route dédiée** `/conformite/aper` | [App.jsx:256](frontend/src/App.jsx#L256) + [NavRegistry.js:87](frontend/src/layout/NavRegistry.js#L87) | C1 |
| P0.3 | **APER — item sidebar** « Solarisation (APER) » | [NavRegistry.js:720-724](frontend/src/layout/NavRegistry.js#L720-L724) | C1 |
| P0.4 | **Baseline DT B absente** (régression DJU `E=a×DJU+b` + r²) | [operat_normalization.py:76](backend/services/operat_normalization.py#L76) | C6 |
| P0.5 | **MERIDIAN absent de la conformité** — DB = HELIOS uniquement (15 findings, 1 org) | `backend/data/promeos.db` + `services/demo_seed/packs.py` | démo/pilote |

### P1 — Crédibilité (calculs, unités, cohérence, messages)

| # | Anomalie | Loc | Contrainte |
|---|---|---|---|
| P1.1 | **`EurAmount` non appliqué aux pénalités conformité** — floats plats sans `CheckConstraint` ni catégorie A/B (modèle existe, table `eur_amounts` = 0 row) | `models/compliance_finding.py`, `models/eur_amount.py` | C5 |
| P1.2 | **2 bascules SMÉ incohérentes** + jeu officiel 39/28/17/16 jamais branché dans le scoring actif | [regops/engine.py:103-136](backend/regops/engine.py#L103-L136) + [compliance_score_service.py:766](backend/services/compliance_score_service.py#L766) + `doctrine/constants.py:343` | C4 |
| P1.3 | **4 moteurs d'évaluation parallèles + 3 jeux de règles** (risque scores divergents UI vs A.2) | `regops/engine.py`, `compliance_rules.py`, `compliance_engine.py`, `bacs_engine.py` | C2 |
| P1.4 | **APER backend sur-développé** : `aper_service.py` (282 l. — PVGIS), pénalités heuristiques `~20 €/m²` non sourcées, triple implémentation (`regops/rules/aper.py` 251 l. + `regulatory/rules/aper.py` 205 l. + `rules/loi_aper_v1.yaml`) | `services/aper_service.py`, `regops/rules/aper.py` | C5 + doctrine |
| P1.5 | **Date OPERAT hardcodée en JSX** `new Date('2026-09-30')` | [TertiaireDashboardPage.jsx:157](frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx#L157) | C8 |
| P1.6 | **Chemin doctrine cassé** `DOCTRINE_FILE = "docs/doctrine/doctrine_promeos_sol_v1_1.md"` (n'existe pas — réel = `docs/vision/promeos_sol_doctrine.md`) → garde-fou SHA256 inopérant | [backend/doctrine/__init__.py:12](backend/doctrine/__init__.py#L12) | C7 |
| P1.7 | **`CompliancePage.jsx` dead code** (338 LOC, `@deprecated LEGACY`, non importé hors tests) | [pages/CompliancePage.jsx](frontend/src/pages/CompliancePage.jsx) | doctrine §6 (anti-pattern dead code) |
| P1.8 | **Incohérence nommage** `/compliance/*` (EN) vs `/conformite/*` (FR) — routes actives `/compliance/pipeline`, `/compliance/sites/:siteId` | `App.jsx:386-401` | C7 |
| P1.9 | **Redondance `RegOps.jsx` ↔ `SiteCompliancePage.jsx`** — deux pages d'analyse conformité par site (386 + 732 LOC) ; `RegOps` quasi-orphelin (1 callsite `Site360.jsx:1908`) | `pages/RegOps.jsx`, `pages/SiteCompliancePage.jsx` | doctrine §6 |
| P1.10 | **Couverture tests Audit SMÉ faible** : 10 tests (`tests/regulatory/test_rule_sme.py`), pas de `test_audit_sme_*` dédié, échéance 11/10/2026 imminente | `backend/tests/regulatory/test_rule_sme.py` | qualité |

### P2 — Amélioration (best-in-world)

| # | Anomalie | Loc |
|---|---|---|
| P2.1 | Heuristiques métier en frontend `* 0.1` HVAC / `* 0.6` parking | [ObligationsTab.jsx:168,170](frontend/src/pages/conformite-tabs/ObligationsTab.jsx#L168-L170) |
| P2.2 | `_build_timeline_events` (107 l. logique métier) inline dans la route | `routes/compliance.py:734-973` |
| P2.3 | `legal_refs.py` couvre ~13 rule_ids ; OPERAT/CEE/DPE sans `legal_ref` → tooltip « NOR + date » manquant | `regops/config/legal_refs.py` |
| P2.4 | `regops/scoring.py` + `compliance_engine.py` morts mais conservés | dette |
| P2.5 | Libellés techniques anglais résiduels `source:` / `v{engine_version}` | `ExecutionTab.jsx:188-189` |
| P2.6 | `_OFFICIAL_WEIGHTS_V2` **hardcodés** (ligne 617-624) au lieu de YAML | `compliance_score_service.py:617` |
| P2.7 | `regulatory_rates.js` (déprécié, fallback offline) — dates BACS `2027-01-01` et APER `2028-01-01` désalignées doctrine ; `acronyms.js:66` cite « 1ᵉʳ janv 2027 » BACS (obsolète) | `frontend/src/domain/regulatory_rates.js`, `utils/acronyms.js:66` |
| P2.8 | Aucun test dédié pour les pages volumineuses : `AperPage` 408, `TertiaireEfaDetailPage` 1121, `SiteCompliancePage` 732, `RegOps`, `CompliancePipelinePage`, 4 pages `tertiaire/*` | couverture |
| P2.9 | `compliance_event_log` existe mais non consommé en UI (audit-trail invisible) | `models/compliance_event_log.py` |

---

## 7. Analyse spécifique menu Conformité

### 7.1 Faut-il garder APER dans le menu ? **NON.**

**Raisons** :
1. **Doctrine PROMEOS C1 explicite** : APER = encart léger dans la page Conformité (bandeau réglementaire + statut indicatif + 2-3 recommandations max). Pas de page, pas de route, pas d'onglet, pas de menu.
2. **APER est une obligation parmi d'autres** : son traitement de plein rang dans la nav (`order: 3` dans le module conformité) crée une dissymétrie injustifiable face à DT (qui a une route mais c'est un workflow OPERAT lourd) et BACS/SMÉ (absents du menu).
3. **Sur-développement actuel** : le combo page 408 LOC + route + menu + service `aper_service.py` (282 l. PVGIS) + 251 l. de règles `regops/rules/aper.py` avec pénalités heuristiques non sourcées = surface d'attaque doctrinale énorme.
4. **Le poids 25 % au score global reste légitime** (C4 l'exige) — la suppression UI ne touche **pas** la pondération.

### 7.2 Entrées menu à supprimer

| Entrée | Localisation | Action |
|---|---|---|
| 🔴 « Solarisation (APER) » | `NavRegistry.js:719-725` | **Supprimer** l'item du module Conformité |
| Mapping `'/conformite/aper': 'conformite'` | `NavRegistry.js:87` | **Supprimer** |
| Page `AperPage` lazy import + route | `App.jsx:93, 256` | **Supprimer** (ou conserver une route minuscule de redirect) |

### 7.3 Entrées menu à garder

| Entrée | `to` | Justification |
|---|---|---|
| « Conformité » | `/conformite` | Hub canonique — ✅ inchangé |
| « Décret Tertiaire / OPERAT » | `/conformite/tertiaire` | **Workflow lourd justifié** (OPERAT EFA + wizard + détail + anomalies = 4 sous-routes, ~2600 LOC). Pas un simple « pilier » mais un sous-cockpit autonome. À garder en sub-item du module. |

### 7.4 Routes à rediriger

| Source | Cible | Type |
|---|---|---|
| `/conformite/aper` | `/conformite?tab=obligations&filter=aper` | 301 redirect (preserve les anciens bookmarks / liens externes) |
| `/compliance/pipeline` | inchangé mais **caché** (déjà le cas via `HIDDEN_PAGES`) | OK |
| `/compliance/sites/:siteId` | `/conformite/sites/:siteId` (renommage FR) — **OU** rediriger vers `/sites/:id?tab=conformite` | à arbitrer |
| `/compliance/sites` | `/conformite` | déjà OK ([legacyRedirects.js:38](frontend/src/routes/legacyRedirects.js#L38)) |
| `/regops/:id` | `/compliance/sites/:siteId` (consolider) ou supprimer si `SiteCompliancePage` devient canonique | à arbitrer |

### 7.5 Composants à fusionner / supprimer

| Action | Composants | Justification |
|---|---|---|
| **Supprimer** | `pages/CompliancePage.jsx` (338 LOC) | dead code `@deprecated`, non importé hors tests |
| **Supprimer** | `pages/AperPage.jsx` (408 LOC) | violation C1 |
| **Conserver service** (avec downgrade) | `backend/services/aper_service.py` | l'estimation PVGIS peut alimenter l'encart APER de la page Conformité — service réutilisé, page supprimée |
| **Fusionner** | `pages/RegOps.jsx` (386 LOC) ↔ `pages/SiteCompliancePage.jsx` (732 LOC) | redondance ; choisir `SiteCompliancePage` comme canonique, basculer le seul callsite `Site360.jsx:1908`, déprécier `RegOps.jsx` |
| **Renommer** | `CompliancePipelinePage` → `PipelineConformitePage` (label FR) | cohérence préfixe `/conformite/*` ; reste caché |
| **Créer** | `<AperEncart>` composant (≤ 50 LOC) intégré à `ObligationsTab` | bandeau + statut indicatif + 2-3 recos ; consomme `GET /api/aper/status?site_id=` minimal |

### 7.6 Modèle cible recommandé

```
Sidebar (module Conformité — emerald)
├── Conformité (/conformite)
│   ├── Onglet 1 — Obligations
│   │   ├── DT (récap site par site)
│   │   ├── BACS (récap site par site)
│   │   ├── Audit SMÉ (récap org)
│   │   └── ▸ Encart APER (bandeau + statut indicatif + 2-3 recos)
│   ├── Onglet 2 — Données & qualité
│   ├── Onglet 3 — Recommandations  (renommer "Plan d'exécution")
│   └── Onglet 4 — Preuves & rapports
└── Décret Tertiaire / OPERAT (/conformite/tertiaire) — workflow lourd sub-route
    ├── /conformite/tertiaire/wizard
    ├── /conformite/tertiaire/efa/:id
    └── /conformite/tertiaire/anomalies

Routes deep-link (hors rail)
├── /conformite/sites/:siteId   (ex-/compliance/sites/:siteId, renommé FR)
└── /conformite/pipeline        (caché, ex-/compliance/pipeline, renommé FR)

Routes supprimées
├── /conformite/aper            → 301 vers /conformite?tab=obligations&filter=aper
├── /regops/:id                 → 301 vers /conformite/sites/:siteId
└── /compliance/*               (legacy redirects conservés)
```

**Endpoint cible** à ajouter pour l'encart APER :
```
GET /api/aper/status?site_id=&org_id=
Response:
  status: "concerned" | "not_concerned" | "to_verify"
  parking_surface_m2: int | null
  reasoning: str   # texte court explicatif
  recommendations: [str]  # 2-3 maximum, depuis backend
  source: { regulation: "Loi 2023-175 art. 40", url: str, evaluated_at: ISO }
```

---

## 8. Plan de correction proposé

### P0 — Actions immédiates (avant démo)

| # | Action | Fichier(s) | Risque | Test à créer |
|---|---|---|---|---|
| P0.1 | Supprimer l'item sidebar APER + mapping module | [NavRegistry.js:87,719-725](frontend/src/layout/NavRegistry.js#L719-L725) | aucun (item indépendant) | `nav_no_aper_item.test.js` (snapshot NavRegistry) |
| P0.2 | Supprimer la route `/conformite/aper` + lazy import `AperPage` | [App.jsx:93,255-261](frontend/src/App.jsx#L93) | bookmarks externes → ajouter redirect 301 dans `legacyRedirects.js` | `RoutingSmoke.test.js` (route absente + redirect) |
| P0.3 | Supprimer `pages/AperPage.jsx` (408 LOC) | [pages/AperPage.jsx](frontend/src/pages/AperPage.jsx) | aucun (couvert par P0.1+P0.2) | source-guard `no_aper_dedicated_page.test.js` |
| P0.4 | Implémenter encart `<AperEncart>` dans `ObligationsTab` (≤ 50 LOC) + endpoint backend `GET /api/aper/status` | `ObligationsTab.jsx` + `routes/aper.py` + `services/aper_service.py` (réutiliser) | léger (nouvelle UI ; conserver `aper_service.py` pour le PVGIS) | `test_aper_status_endpoint.py` + `AperEncart.test.js` |
| P0.5 | Implémenter baseline DT B (régression DJU `E=a×DJU+b` + r²) | `services/operat_normalization.py` + `services/operat_trajectory.py` + `models/tertiaire_efa.py` (colonnes `slope_a`, `intercept_b`, `r2`) | élevé (touche le calcul de trajectoire ; nécessite recalcul historiques) | `test_operat_baseline_b_regression.py` + golden tests |
| P0.6 | Reseed MERIDIAN dans la DB (3 sites + findings DT/BACS/APER) | `services/demo_seed/packs.py` + `gen_compliance.py` + `gen_bacs.py` + `gen_tertiaire.py` | aucun (seed démo) | `test_seed_meridian_compliance.py` |

### P1 — Consolidation (crédibilité)

| # | Action | Fichier(s) | Risque | Test à créer |
|---|---|---|---|---|
| P1.1 | Migrer pénalités `estimated_penalty_eur` vers `EurAmount` (catégorie A obligatoire pour pénalités réglementaires) | `models/compliance_finding.py` + migration Alembic + `models/eur_amount.py` | moyen (schéma + backfill) | `test_compliance_finding_eur_amount_traceability.py` |
| P1.2 | Brancher `REGOPS_WEIGHTS_AUDIT_APPLICABLE` (39/28/17/16) dans `compliance_score_service` ; supprimer la bascule post-scoring `engine.py:103-136` | `services/compliance_score_service.py` + `regops/engine.py` | élevé (changement de score pour sites SMÉ-applicable) | `test_compliance_score_weights_sme_applicable.py` + dual-engine consistency |
| P1.3 | Unifier les moteurs : déprécier `compliance_engine.py` et `compliance_rules.py`, faire converger UI bundle sur `regops/engine.py` (ou inversement, choix doctrinal) | `services/compliance_rules.py`, `services/compliance_engine.py`, `routes/compliance.py` | élevé | `test_dual_engine_convergence.py` (étendre existant) |
| P1.4 | Downgrade APER backend : retirer les pénalités heuristiques non sourcées de `regops/rules/aper.py` ; consolider triple implémentation | `regops/rules/aper.py`, `regulatory/rules/aper.py`, `rules/loi_aper_v1.yaml` | moyen (sub-score APER affecté) | `test_aper_no_unsourced_penalty.py` |
| P1.5 | Remplacer `new Date('2026-09-30')` par lecture `RegulatoryConstantsContext` | [TertiaireDashboardPage.jsx:157](frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx#L157) | aucun | source-guard `no_hardcoded_dates_in_jsx.test.js` |
| P1.6 | Corriger `DOCTRINE_FILE` vers `docs/vision/promeos_sol_doctrine.md` + activer `doctrine_sha256()` dans un test | [backend/doctrine/__init__.py:12](backend/doctrine/__init__.py#L12) | aucun | `test_doctrine_sha256_frozen.py` |
| P1.7 | Supprimer `pages/CompliancePage.jsx` (dead code) + tests associés | [pages/CompliancePage.jsx](frontend/src/pages/CompliancePage.jsx) | aucun | — |
| P1.8 | Renommer `/compliance/pipeline` → `/conformite/pipeline` et `/compliance/sites/:id` → `/conformite/sites/:id` + redirects | `App.jsx`, `legacyRedirects.js` | léger (deep-links externes) | `test_legacy_compliance_routes_redirect.py` |
| P1.9 | Fusionner `RegOps.jsx` → `SiteCompliancePage.jsx` ; basculer `Site360.jsx:1908` ; supprimer `RegOps.jsx` | `pages/RegOps.jsx`, `Site360.jsx`, `evidence.fixtures.js` | léger (1 callsite + 1 fixture) | `test_regops_replaced_by_site_compliance.py` |
| P1.10 | Compléter tests Audit SMÉ : fichier dédié `test_audit_sme_service.py` couvrant scoring, seuils, exemption ISO 50001, échéance 2026-10-11 | `backend/tests/test_audit_sme_service.py` (à créer) | aucun (tests) | n/d |

### P2 — UX premium

| # | Action | Fichier(s) | Risque | Test à créer |
|---|---|---|---|---|
| P2.1 | Sortir les heuristiques `* 0.1` (HVAC) et `* 0.6` (parking) du frontend vers un endpoint `GET /api/sites/:id/derived_metrics` | `ObligationsTab.jsx`, `routes/sites.py` | léger | `test_sites_derived_metrics.py` |
| P2.2 | Extraire `_build_timeline_events` (107 l.) vers `services/compliance_timeline_service.py` | `routes/compliance.py`, nouveau service | moyen (refactor) | `test_compliance_timeline_service.py` |
| P2.3 | Compléter `legal_refs.py` pour les rule_ids OPERAT, DPE, CEE | `regops/config/legal_refs.py` | aucun | `test_legal_refs_coverage.py` |
| P2.4 | Supprimer `regops/scoring.py` (déprécié) + `compliance_engine.py` (mort) après migration `score_explain` | les 2 fichiers | léger | source-guard `no_legacy_compliance_modules.py` |
| P2.5 | Renommer en FR les libellés résiduels `source:` / `v{engine_version}` | `ExecutionTab.jsx:188-189` | aucun | snapshot |
| P2.6 | Migrer `_OFFICIAL_WEIGHTS_V2` hardcodé → `regs.yaml > scoring > weights_v2` | `compliance_score_service.py:617` | léger | `test_regs_yaml_weights_v2.py` |
| P2.7 | Synchroniser `regulatory_rates.js` + `acronyms.js:66` avec doctrine (dates BACS 2030, APER 2028-07-01) | `domain/regulatory_rates.js`, `utils/acronyms.js` | aucun | source-guard `regulatory_rates_aligned_with_doctrine.test.js` |
| P2.8 | Ajouter tests unitaires pour `TertiaireEfaDetailPage`, `SiteCompliancePage`, pages `tertiaire/*` | tests FE | aucun | n/d |
| P2.9 | Exposer en UI le `compliance_event_log` (timeline audit-trail visible dans onglet « Preuves » ou nouvel onglet « Historique ») | `ConformitePage.jsx`, nouveau composant | léger | `test_compliance_event_log_ui.js` |

---

## 9. Tests à ajouter / mettre à jour

| Test | Type | Fichier cible | Cas couvert | Critère d'acceptation |
|---|---|---|---|---|
| `no_aper_dedicated_page` | source-guard FE | `frontend/src/__tests__/source_guards/no_aper_dedicated_page.test.js` | grep `pages/AperPage` interdit | 0 occurrence |
| `no_aper_route_in_router` | unit FE | `frontend/src/__tests__/RoutingSmoke.test.js` (étendre) | route `/conformite/aper` non résolue + redirect 301 vers `/conformite?tab=obligations&filter=aper` | 200 + Location header attendu |
| `no_aper_item_in_sidebar` | unit FE | `frontend/src/layout/__tests__/NavRegistry.test.js` (étendre) | aucun item avec `to === '/conformite/aper'` | assert vide |
| `aper_encart_renders` | unit FE | `frontend/src/pages/conformite-tabs/__tests__/AperEncart.test.js` | rendu encart APER avec statut concerned / not_concerned / to_verify ; max 3 recos | snapshot |
| `aper_status_endpoint` | unit BE | `backend/tests/test_aper_status_endpoint.py` | `GET /api/aper/status` retourne statut + recos + source | 200 + schéma Pydantic |
| `compliance_score_weights_sme_applicable` | unit BE | `backend/tests/test_compliance_score_weights_sme_applicable.py` | bascule weights 45/30/25 → 39/28/17/16 quand `sme_applicable=True` | assertion poids exacts + somme 100% |
| `compliance_score_sum_100` | unit BE + source-guard | `backend/tests/test_compliance_weights_consistency.py` | somme poids = 100% en V1, V2, et jeu SMÉ | assertion `Σ == 1.00` |
| `compliance_finding_eur_amount_traceability` | unit BE | `backend/tests/test_compliance_finding_eur_amount.py` | toute pénalité conformité utilise `EurAmount` cat. A avec `source_article` non null | CheckConstraint OK |
| `operat_baseline_b_regression` | unit BE | `backend/tests/test_operat_baseline_b_regression.py` | régression `E=a×DJU+b` produit a, b, r² pour une série conso×DJU | r² > 0.5 sur golden |
| `operat_no_simple_ratio_for_modulation` | source-guard BE | `backend/tests/source_guards/test_operat_no_simple_ratio.py` | absence de pattern `conso × DJU_ref/DJU_obs` dans `operat_trajectory.py` | 0 match |
| `seed_meridian_compliance` | unit BE | `backend/tests/test_seed_meridian_compliance.py` | après reseed pack MERIDIAN, `compliance_findings` contient ≥ 5 findings org MERIDIAN | count > 0 |
| `no_hardcoded_dates_in_jsx` | source-guard FE | `frontend/src/__tests__/source_guards/no_hardcoded_dates_jsx.test.js` | grep `new Date\('20\d\d-` dans `pages/**/*.jsx` | 0 match |
| `doctrine_sha256_frozen` | unit BE | `backend/tests/test_doctrine_sha256_frozen.py` | `doctrine_sha256() == DOCTRINE_SHA256_FROZEN` | égalité stricte |
| `legacy_compliance_routes_redirect` | unit FE | `frontend/src/__tests__/legacy_compliance_redirects.test.js` | `/compliance`, `/compliance/sites`, `/conformite/aper` → 301 | Location headers OK |
| `regops_replaced_by_site_compliance` | unit FE | `frontend/src/__tests__/regops_consolidation.test.js` | grep `pages/RegOps` retourne 0 import | 0 callsite hors tests |
| `dual_engine_convergence` (étendre existant) | unit BE | `backend/tests/test_compliance_dual_engine_consistency.py` | score `/bundle` (compliance_rules) == score A.2 (compliance_score_service) pour mêmes inputs | diff ≤ 1 point |
| `compliance_timeline_service` | unit BE | `backend/tests/test_compliance_timeline_service.py` | extraction service de `_build_timeline_events` | golden output identique |
| `audit_sme_service` | unit BE | `backend/tests/test_audit_sme_service.py` | scoring SMÉ, seuils 2.75/23.6 GWh, exemption ISO, échéance 2026-10-11 | ≥ 20 tests |
| `finding_traceability_complete` | unit BE | `backend/tests/test_finding_traceability_complete.py` | chaque finding a `legal_ref` + `evaluated_at` + `evidence_json` non null | 100% des rules avec legal_ref couverte |
| `aper_no_unsourced_penalty` | unit BE | `backend/tests/test_aper_no_unsourced_penalty.py` | finding APER ne contient pas `penalty_source="estimation"` | 0 finding heuristique |
| `e2e_conformite_aper_encart` | e2e | `e2e/e9-conformite-aper-encart.spec.js` | scénario : navigation `/conformite` → onglet Obligations → encart APER visible avec statut + recos | Playwright pass |
| `e2e_no_dedicated_aper_route` | e2e | `e2e/e9-conformite-aper-encart.spec.js` | navigation directe `/conformite/aper` → redirect `/conformite?tab=obligations&filter=aper` | URL finale attendue |

---

## 10. Definition of Done

La refonte du menu Conformité est **DONE** quand TOUTES les conditions ci-dessous sont remplies :

### Doctrine & UX
- [ ] Aucune route `/conformite/aper`, `/aper`, `/compliance/aper` ne résout — toutes redirigent vers `/conformite?tab=obligations&filter=aper` (301).
- [ ] Aucun item sidebar « APER », « Solarisation », « Solar » sous le module Conformité.
- [ ] `pages/AperPage.jsx` supprimé du repo.
- [ ] Encart APER visible dans l'onglet « Obligations » de `/conformite` : bandeau + statut indicatif + ≤ 3 recommandations + source citée (NOR + date).
- [ ] Onglet 3 renommé « Recommandations » (ou décision explicite de conserver « Plan d'exécution »).
- [ ] Aucun label utilisateur visible en anglais (« compliance », « finding », « pipeline », « kind », « domain ») hors abréviations sourcées (NOR, ISO).

### Scoring & métier
- [ ] Score A.2 = score affiché dans `/conformite` (cohérence cross-écran ; pas de divergence Cockpit ↔ Conformité ↔ Site360).
- [ ] Pondération mode standard : DT 0.45 / BACS 0.30 / APER 0.25 — somme 1.00.
- [ ] Pondération mode SMÉ-applicable : DT 0.39 / BACS 0.28 / APER 0.17 / SMÉ 0.16 — somme 1.00, branché dans le moteur actif.
- [ ] Baseline DT B opérationnelle (régression DJU `E=a×DJU+b`, r² tracké et exposé sur la fiche EFA).
- [ ] Pénalités conformité utilisent `EurAmount` catégorie A avec `source_article` non null (CheckConstraint actif).
- [ ] Aucune pénalité APER avec `penalty_source="estimation"`.

### Backend & data
- [ ] Un seul moteur de score canonique (au choix : `regops/engine.py` ou `compliance_score_service.py`) — les autres dépréciés et marqués pour suppression.
- [ ] Un seul jeu de règles YAML par réglementation (élimination de la divergence `regs.yaml` ↔ `rules/decret_*_v1.yaml`).
- [ ] MERIDIAN seedé : ≥ 5 findings DT + 5 BACS + 5 APER pour `org_id=MERIDIAN`.
- [ ] `_build_timeline_events` extrait en service dédié.
- [ ] `compliance_engine.py` et `regops/scoring.py` supprimés (après migration `score_explain`).

### Tests & qualité
- [ ] Tous les tests existants restent verts (BE ≥ baseline 6 027, FE ≥ baseline 4 751).
- [ ] Nouveaux tests verts (≥ 22 nouveaux tests listés §9).
- [ ] Source-guards actifs : `no_aper_dedicated_page`, `no_hardcoded_dates_in_jsx`, `regulatory_rates_aligned_with_doctrine`, `operat_no_simple_ratio_for_modulation`.
- [ ] `npm run build` : 0 erreur, 0 warning.
- [ ] `npx eslint src --max-warnings=0` : OK.
- [ ] Playwright `e2e/e4-patrimoine-conformite.spec.js` + nouveau `e9-conformite-aper-encart.spec.js` : pass.

### Doctrine & traçabilité
- [ ] `DOCTRINE_FILE` pointe vers `docs/vision/promeos_sol_doctrine.md` (chemin valide).
- [ ] `doctrine_sha256()` testé et égal à `DOCTRINE_SHA256_FROZEN`.
- [ ] `legal_refs.py` couvre 100 % des rule_ids consommés (OPERAT, DPE, CEE inclus).
- [ ] `compliance_event_log` exposé en UI (onglet « Preuves » ou « Historique »).

### Non-régression
- [ ] Cockpit / Patrimoine / Billing / Achat / Actions : zéro régression visible (smoke Playwright 10/10 routes).
- [ ] Score conformité affiché identique avant/après refonte sur le seed HELIOS (modulo bascule SMÉ explicite).

---

## Conclusion

> **STOP GATE : il faut clarifier avant correction.**

**Raisons** :

1. **3 P0 cardinaux interdépendants** nécessitent un arbitrage produit explicite avant toute écriture de code :
   - **Suppression APER** : le contenu utile (estimation PVGIS) doit-il être préservé dans l'encart, et `aper_service.py` reste-t-il (downgradé) ou est-il purement supprimé ?
   - **Baseline DT B** (régression DJU) : effort important (touche le calcul de trajectoire OPERAT, modèles `TertiaireEfa`, recalcul historiques) — dans le périmètre de ce sprint, ou P0 reporté à un sprint OPERAT dédié ?
   - **MERIDIAN seed** : reseed à la racine ou pack séparé, et impact sur les baselines DB existantes ?

2. **2 P1 architecturaux structurants** : (a) choix du moteur de score canonique unique (`regops/engine.py` vs `compliance_score_service.py`) — l'un nourrit `/bundle` UI, l'autre nourrit le score A.2 ; (b) implémentation de la pondération SMÉ officielle 39/28/17/16 qui changera les scores observés pour les sites SMÉ-applicable. Ces deux décisions doivent être arbitrées avant les commits P1.

3. **Écart sémantique doctrine ↔ code** sur l'onglet 3 (« Plan d'exécution » vs « Recommandations » attendu). Décision produit nécessaire pour éviter de coder le mauvais wording.

4. **Le rapport Phase 0 STOP GATE** (`audit_conformite_v1_phase0.md`) reste prioritaire — sa validation conditionne ce plan : les anomalies remontées ici reprennent et étendent celles du STOP GATE.

➡️ **Mes 3 questions bloquantes** (rappelées du rapport Phase 0) attendent toujours réponse :
- (Q1) APER suppression — périmètre exact + sort de `aper_service.py` ?
- (Q2) Pondération SMÉ — implémenter 39/28/17/16 dans le moteur actif + lequel devient canonique ?
- (Q3) Baseline DT B — in-scope sprint actuel, ou P0 reporté ?

Dès validation des P0 / réponses Q1-Q3, le **plan P0 ci-dessus est exécutable en ~3-5 jours/homme** (APER 1.5 j + DT B 2-3 j + MERIDIAN seed 0.5 j), suivi de **~6-10 jours/homme P1** (unification moteurs + SMÉ + EurAmount + renommages + tests). Les **P2** sont best-effort.
