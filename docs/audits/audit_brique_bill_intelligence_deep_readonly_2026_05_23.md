# Audit profond brique Bill Intelligence / Factures — READ-ONLY

> **Branche** : `claude/refonte-sol2 @ 79a3d2a1` (post-merge P0 patrimoine + hygiène CI + P0 conformité)
> **Date** : 2026-05-23
> **Mode** : READ-ONLY strict — aucune modification de code
> **Périmètre** : Bill Intelligence (`/bill-intel`, `/billing`, `/api/billing/*`, `/api/bill-intelligence/*`)
> **Hors scope** : Conformité (audité 2026-05-23 — verdict 8/10 post-P1), Patrimoine (audité, P0 mergé)

---

## TL;DR — Verdict

**🟡 GO conditionnel — note brique 7/10**

Le wedge facturation (audit ↔ contrat ↔ anomalies ↔ insights) est fonctionnel
de bout en bout. La Règle 1 ("aucune facture analysable sans contrat") est
**verrouillée par un source-guard et une garde applicative** avec message FR
doctriné. La Règle 2 ("aucune anomalie sans source / montant / période /
preuve / action") est **partiellement conforme** : tous les détecteurs peuplent
un `details_json` riche mais aucune **CHECK constraint DDL** ni **FK Evidence /
Action** n'est en place — l'invariant tient par convention, pas par contrat.

**3 risques P0 à corriger avant tout sprint Achat/Cockpit :**
1. `BillAnomaly.actual_value` nullable autorise des anomalies sans montant (KPI VNU à 0,0 €).
2. Aucune FK `evidence_id` / `action_id` formelle sur `BillAnomaly` — la preuve vit dans `details_json`.
3. `POST /api/billing/audit-all` retourne **HTTP 500** en DEMO_MODE sans JWT (regression silencieuse).

---

## 1. Cartographie modèles + routes

### 1.1 Entités cardinales

| Entité | Modèle (file:line) | Table | FK clés | Énergie |
|---|---|---|---|---|
| **EnergyInvoice** | `models/billing_models.py:381` | `energy_invoices` | `site_id`, `contract_id` (nullable), `annexe_site_id` | implicite via contract |
| **EnergyInvoiceLine** | `models/billing_models.py:499` | `energy_invoice_lines` | `invoice_id`, `period_code` (BASE/HP/HC/HPE/HCE), `line_category` (turpe_gestion/cta/accise/supply_hpe/tva) | — |
| **BillAnomaly** | `models/bill_anomaly.py:28` | `bill_anomaly` | `invoice_id`, `code` (R19/R20/R21+), `severity`, `actual_value` (nullable), `threshold_value` (nullable), `details_json` | — |
| **BillingInsight** | `models/billing_models.py:544` | `billing_insights` | `site_id`, `invoice_id` (nullable), `type` (overcharge/shadow_gap/price_drift/duplicate/missing_period), `insight_status`, `estimated_loss_eur` | — |
| **EnergyContract** | `models/billing_models.py:44` | `energy_contracts` | `site_id`, `fournisseur_id`, `entite_juridique_id`, `is_cadre`, prix HP/HC/HPE/HCE/BASE, `subscribed_power_kva`, `tariff_option` | `energy_type` (Enum ELEC/GAZ) |
| **ContratCadre** | `models/contract_v2_models.py:36` | `contrats_cadre` | `org_id`, `entite_juridique_id`, `type_prix` (fixe/indexé/spot/tunnel), prix HP/HC/BASE, `cee_inclus`, `capacite_incluse` | `energie` |
| **ContractAnnexe** | `models/contract_v2_models.py:249` | `contract_annexes` | `cadre_id`, `contrat_cadre_id` (legacy), `site_id` (UniqueConstraint) | — |
| **DeliveryPoint** | `models/patrimoine.py:258` | `delivery_points` | `site_id`, `code` (PRM/PCE), `grd_code`, `categorie_turpe`, `code_fta`, `version_turpe`, `atrd_option`, `accise_categorie_elec/gaz` | `energy_type` |
| **Compteur** | `models/compteur.py:12` | `compteurs` | `site_id`, `delivery_point_id`, `sub_meter_of_id` (self-FK), `sub_meter_usage`, `batiment_id` | (via DP) |
| **BillingImportBatch** | `models/billing_models.py:652` | `billing_import_batches` | `org_id`, `content_hash` (SHA-256 idempotence), `rows_inserted/skipped/errors_json` | — |

### 1.2 Couverture des 10 points de rattachement demandés

| Rattachement | État | Source |
|---|---|---|
| **organisation** | ✅ via chaîne Site → Portefeuille → EntiteJuridique → Organisation (4 JOINs) | `routes/bill_intelligence.py:58-186` |
| **site** | ✅ FK direct `EnergyInvoice.site_id` + index `(site_id, period_start)` + `(site_id, period_end DESC)` | `models/billing_models.py:406-412` |
| **point de livraison** | ⚠️ **N-N implicite** via table `contract_delivery_points` (EnergyContract ↔ DP). Pas de FK directe `invoice → DP` — la liaison passe par le contrat | `models/billing_models.py` |
| **contrat** | ✅ FK `EnergyInvoice.contract_id` (nullable, lookup via perimeter_check) + V2 `annexe_site_id` | `models/billing_models.py:406` |
| **période** | ✅ `period_start` + `period_end` (NOT NULL) + index `(period_end DESC)` | `models/billing_models.py:417` |
| **énergie** | ⚠️ **Pas de colonne directe** sur `EnergyInvoice` — déduite via `contract.energy_type` ou contexte ligne (`period_code`) | (Risque P2 : couplage faible) |
| **lignes tarifaires** | ✅ `EnergyInvoiceLine` 1→N avec `line_type` (ENERGY/NETWORK/TAX/OTHER) + `line_category` détaillée | `models/billing_models.py:499-542` |
| **anomalies** | ✅ `BillAnomaly` 1→N + `UniqueConstraint(invoice_id, code)` anti-doublon | `models/bill_anomaly.py:99` |
| **actions** | ⚠️ **Indirection** via `BillingInsight.recommended_actions_json` (JSON) — pas de FK formelle vers `ActionCenterItem` | `models/billing_models.py:611` |
| **preuves** | ❌ **Pas de modèle Evidence dédié au billing** — les preuves vivent dans `details_json` (champ texte semi-structuré) | (Risque P0 — cf. Règle 2) |

### 1.3 Routes backend (30 paths)

**Préfixes** : `/api/billing/*` (28 paths) + `/api/bill-intelligence/anomalies` (1) + `/api/persona/cfo/billing-anomalies-summary` (1).

Endpoints clés cartographiés :

| Méthode | Path | Handler | Org-scoping |
|---|---|---|---|
| `POST` | `/billing/perimeter/check` | Garde Règle 1 (FR doctriné) | implicite via site |
| `POST` | `/billing/import-csv` | Idempotent SHA-256 + rate-limit 20/60s | `resolve_org_id` ✅ |
| `POST` | `/billing/import-pdf` | Async + résolution Fournisseur via SIREN | `resolve_org_id` ✅ |
| `POST` | `/billing/audit/{id}` | `audit_invoice_full()` (10 règles) | — |
| `POST` | `/billing/audit-all` | Batch + auto-reconcile | `resolve_org_id` (⚠️ HTTP 500 sans JWT en DEMO) |
| `POST` | `/billing/reconcile-all` | rate-limit 5/60s | `resolve_org_id` ✅ |
| `GET` | `/billing/insights` | Workflow Insights | `resolve_org_id` ✅ |
| `PATCH` | `/billing/insights/{id}` | status/owner/notes | `resolve_org_id` ✅ |
| `GET` | `/billing/invoices/{id}/shadow-breakdown` | V2 engine 4 composantes (fourniture/TURPE/taxes/TVA) | — |
| `GET` | `/bill-intelligence/anomalies` | 4 JOINs IDOR-safe + KPI canonique post P1-CR-003 | `resolve_org_id` ✅ |

### 1.4 Services métier (11 services)

`backend/services/billing_service.py` (1500+ lignes) :
- `audit_invoice_full()` (L1039) — orchestrateur 10 règles
- `shadow_billing_simple()` (L338) — écart factures vs reconstitution
- `find_active_annexe()` (L70) — lookup V2 cadre+annexe
- `get_reference_price()` (L165) — cascade prix (V2 annexe > legacy > MarketPrice > config)

Et : `billing_reconcile.py`, `bill_intelligence.py`, `billing_shadow_v2.py`,
`billing_normalization.py`, `billing_explainability.py`, `fournisseur_resolver_service.py`,
`contract_coverage_service.py`, `perimeter_check.py`.

### 1.5 Anomaly Engine — 10 règles + 11 codes BillAnomaly

| Règle | Fichier | Type |
|---|---|---|
| R1 Shadow gap | `billing_service.py:446` | écart > 20% |
| R2 Unit price high | `:488` | > 0.30 €/kWh elec, > 0.15 gaz |
| R3 Duplicate | `:514` | même site/période/montant |
| R4 Missing period | `:547` | début ou fin absents |
| R5 Period too long | `:568` | > 62 jours |
| R6 Negative kWh | `:593` | conso < 0 |
| R7 Zero amount | `:613` | montant=0 / conso>0 |
| R8 Lines sum mismatch | `:639` | ∑lignes ≠ total |
| R9 Missing contract | (suite) | déclenche perimeter_check |
| R10 VNU dormant / Capacité variance | `bill_anomaly.py` Phase 5.1 | codes R19/R20+R21..R31 |

---

## 2. Règle 1 — "Aucune facture analysable sans contrat si DP actif"

**Statut** : ✅ **VERROUILLÉE par garde applicative + source-guard + message FR**

### Implémentation

1. **Service** [`backend/services/perimeter_check.py:26-78`](backend/services/perimeter_check.py#L26-L78) — fonction `check_perimeter(site_id, contract_id)` retourne `error_code=BILLING_CONTRACT_REQUIRED` + `blocking=True` si `contract_id is None` ET `_site_has_active_delivery_points()` est vrai.

2. **Message FR canonique** [`perimeter_check.py:21-23`](backend/services/perimeter_check.py#L21-L23) :
   > *"Impossible de fiabiliser cette facture : aucun contrat n'est rattaché au point de livraison."*

3. **Source-guard dédié** [`backend/tests/test_perimeter_check_requires_contract_when_delivery_points_active.py:112-167`](backend/tests/test_perimeter_check_requires_contract_when_delivery_points_active.py#L112-L167) — test `test_no_contract_id_with_active_dp_is_blocking` vérouille le comportement.

4. **Service de couverture contractuelle** [`backend/services/contract_coverage_service.py:257-442`](backend/services/contract_coverage_service.py#L257-L442) — `compute_site_contract_coverage()` retourne `contrat_manquant` + `ready_for_billing=False` si DP actifs + 0 contrat.

### Vérification curl (live runtime)

```
POST /api/billing/perimeter/check  body={"site_id":1,"contract_id":null}
→ 200 OK
   {
     "consistent": false,
     "site_exists": true,
     "contract_exists": null,
     "warnings": ["Impossible de fiabiliser cette facture : aucun contrat n'est rattaché au point de livraison."],
     "error_code": "BILLING_CONTRACT_REQUIRED",
     "blocking": true
   }
```

POST `contract_id=1` → `consistent: true`, `blocking: false`. ✅

### Risque résiduel

`EnergyInvoice.contract_id` reste `nullable=True` au niveau DDL pour permettre l'ingestion multi-étapes (import CSV avant assignment contrat). La garde applicative bloque avant marking `analysable=true`, mais une mutation directe SQL (ou un script admin) pourrait contourner. **Mitigation P2** : marquer la facture comme `MANUAL_REVIEW` et exposer un dashboard "factures sans contrat" au DAF.

**Verdict Règle 1** : ✅ — verrouillage triple (garde + source-guard + message FR).

---

## 3. Règle 2 — "Aucune anomalie sans source / montant / période / preuve / action"

**Statut** : ⚠️ **PARTIELLEMENT CONFORME** — invariant par convention, pas par contrat.

### Analyse colonnes BillAnomaly

| Champ Règle 2 | Colonne réelle | NOT NULL ? | Verdict |
|---|---|---|---|
| **source** | (implicite via `code` = R19/R20/...) | non | ⚠️ pas de champ explicite `source` / `detected_by` |
| **montant** | `actual_value` Numeric(15,4) | **nullable=True** | ❌ peut être NULL → KPI faussé |
| **période** | (héritée de `invoice → period_start/end` JOIN) | NOT NULL côté invoice | ⚠️ pas dénormalisée — coûteuse à requêter |
| **preuve** | (dans `details_json` semi-structuré) | nullable=True | ❌ pas de FK Evidence formelle |
| **action** | (dans `BillingInsight.recommended_actions_json`) | n/a | ❌ pas de FK ActionCenterItem |

### Mitigation observée

Tous les détecteurs R19/R20/R21-R31 dans [`backend/services/bill_intelligence/anomaly_detector.py`](backend/services/bill_intelligence/anomaly_detector.py) peuplent systématiquement `details_json` avec un contexte complet :

```python
# R19 (VNU dormant)
details_json = {"vnu_total_eur", "vnu_lines_count", "consumption_kwh", "vnu_labels", "explanation"}

# R20 (Capacité variance)
details_json = {"period_code", "capacite_facturee_kva", "capacite_souscrite_kva", "variance_pct", "contract_id"}
```

Pattern strict `try/except` par détecteur + `_logger.error()` si échec (résilience par-action).

### Couverture tests

19 tests dans [`test_bill_anomaly_detector.py`](backend/tests/test_bill_anomaly_detector.py) (456 lignes) — couverture R19/R20/R21+. **Aucun test "anomalie incomplète rejetée"** (grep négatif sur `incomplete`, `without.*source`, `evidence`).

### Vérification curl (live runtime)

```
GET /api/bill-intelligence/anomalies
→ 200 OK { "count": 50, "total_count": 52, "kpi_vnu_dormant_reclaim_eur": 0.0, ... }
```

⚠️ **52 anomalies présentes** mais `kpi_vnu_dormant_reclaim_eur=0.0` et `kpi_total_economie_potentielle_eur=0.0` — soit la DB demo est calibrée sans VNU effectif, soit les anomalies persistées ont `actual_value=NULL`.

**Verdict Règle 2** : ⚠️ — invariant respecté par convention (détecteurs peuplent toujours `details_json`), pas par DDL. À durcir en P1 billing : (a) `actual_value NOT NULL`, (b) FK `evidence_id` ou table `BillAnomalyEvidence`, (c) FK `action_id` vers `ActionCenterItem`, (d) test "anomalie incomplète rejetée".

---

## 4. Pages FE + routes mortes

### 4.1 Pages routées (2)

| Page | Route | Composants principaux |
|---|---|---|
| [`BillIntelPage.jsx`](frontend/src/pages/BillIntelPage.jsx) | `/bill-intel` | SolPageHeader, HealthSummary, InsightDrawer, ActionDetailDrawer, DossierPrintView |
| [`BillingPage.jsx`](frontend/src/pages/BillingPage.jsx) | `/billing` | CoverageBar, BillingTimeline, BillingCompareChart |

Navigation interne bidirectionnelle ([`BillIntelPage.jsx:641`](frontend/src/pages/BillIntelPage.jsx#L641) → `/billing`, [`BillingPage.jsx:368-376`](frontend/src/pages/BillingPage.jsx#L368-L376) → `/bill-intel`).

### 4.2 Composants spécialisés (6)

`InsightDrawer`, `BillingTimeline`, `CoverageBar`, `BillingCompareChart`, `SiteBillingMini`, `ShadowBreakdownCard`.

### 4.3 API client dead code (6 fonctions exportées jamais consommées)

`getBillingRules`, `auditInvoice`, `patchBillingInsight`, `getImportBatches`, `getBillingAnomaliesScoped`, `getNormalizedInvoices` — exportées mais non consommées par aucune page. **À déprécier en stubs** (pattern P1.5 conformité).

### 4.4 Endpoints 410 Gone côté billing

**Zéro** endpoint 410 Gone lié au billing détecté. Pas de dette legacy backend à purger.

### 4.5 Anti-régression Playwright golden path

Frontend démarré sur `http://127.0.0.1:5175` (DEMO_MODE backend up sur `:8001`).

| # | Étape | Capture | Observation |
|---|---|---|---|
| 0 | Login démo HELIOS | — | OK |
| 1 | `/bill-intel` rendu | `01_bill_intel_hero.png` | Title *"Vos factures vérifiées, recalculées, expliquées — shadow billing v1.2"*, KPIs 10,2 k€ / 48 anomalies / 4,9 k€ ✅ |
| 2 | `/billing` rendu | `02_billing_page.png` | Title *"Facturation — Chronologie"*, couverture 12/0/0, comparaison mensuelle 2026 vs 2025 ✅ |
| 3 | `/patrimoine` (anti-régression) | `03_patrimoine_anti_regression.png` | Page rend normalement ✅ |

**Métriques** :
- `console.error` : **1** (pré-existant `/api/kb/apply` 500, non billing)
- network 4xx/5xx : **1** (même cause)

Captures stockées `/tmp/promeos-audit-billing/*.png` (hors repo, gitignore actif).

---

## 5. Doctrine "/conformite hub unique" appliquée à Bill Intelligence

- ✅ Module `facturation` isolé dans `NavRegistry` ([`layout/NavRegistry.js`](frontend/src/layout/NavRegistry.js#L277))
- ✅ Aucun lien ACC / PMO / Flex / Partner Hub depuis les pages billing
- ✅ Aucune redondance avec Cockpit ou Conformité (pas de "tableau de bord factures" dupliqué)
- ✅ Persona-based positioning #2-#4 pour DAF/DG/Acheteur/Energy Manager

### ⚠️ Faute d'audit P1 Conformité — sidebar Conformité expose 3 sous-items

**Constat hors scope billing mais détecté ce jour** :

Inventaire sidebar `/conformite` (capture sidebar `04_sidebar_check.png`) montre 3 sous-items :
- *Conformité*
- *Décret Tertiaire / OPERAT*
- *Solarisation (APER)*

La doctrine "/conformite hub unique" formulée le 2026-05-23 dans le sprint P1
visait l'interdiction de menus **ACC / PMO / Flex / Partner Hub** — mais
l'audit P1 §10 *"Doctrine — vérification ligne par ligne"* n'a **pas vérifié**
la légitimité des sous-items DT et APER, alors qu'ils sont issus d'un sprint
antérieur (`94b595a9 — 2026-03-08 Sidebar Context-first`) très antérieur à la
doctrine.

**Action de suivi** : sprint dédié `cleanup-sidebar-conformite-souitems` à
ouvrir après ce verdict — retirer les sous-items DT/APER de `NavRegistry.js`,
les replier en tabs internes à `/conformite`. **Ne bloque pas Bill Intelligence**.

---

## 6. Audit fonctionnel curl — synthèse

| # | Cmd | HTTP | Verdict FR |
|---|---|---|---|
| 1 | `GET /api/billing/rules` | 200 | ✅ liste 10 règles JSON |
| 2 | `GET /api/billing/summary` | 200 | ✅ 36 invoices / 78 insights / 294 890 € / 19 808 € loss |
| 3 | `GET /api/billing/insights` | 200 | ✅ messages FR "*Écart shadow billing de +31.4%*" |
| 4 | `POST /api/billing/perimeter/check` (no contract) | 200 | ✅ `BILLING_CONTRACT_REQUIRED` + FR doctriné |
| 5 | `POST /api/billing/perimeter/check` (with contract) | 200 | ✅ `consistent: true` |
| 6 | `GET /api/billing/coverage-summary?org_id=1` | 200 | ✅ 12 mois couverts, 0 manquant |
| 7 | `GET /api/billing/missing-periods?site_id=1` | 200 | ✅ payload avec `regulatory_impact` (cross-brique) |
| 8 | `GET /api/bill-intelligence/anomalies` | 200 | ⚠️ 52 anomalies mais `kpi_vnu_dormant=0.0` |
| 9 | `GET /api/billing/site/1` | 200 | ✅ contracts + invoices agrégés |
| 10 | `POST /api/billing/audit-all` (DEMO mode, no JWT) | **500** ❌ | `INTERNAL_ERROR` + FR `"Erreur interne du serveur"` + correlation_id — **regression P0** |

---

## 7. Synthèse exécutive

### Note brique Bill Intelligence : **7 / 10**

| Axe | Note | Verdict |
|---|---|---|
| Cartographie modèles (9 tables + 30 routes + 11 services) | 9/10 | ✅ Architecture mature, V2 cadre+annexe livré, TURPE 7 / TVA Phase 7.7 / Phase F2 fournisseur SIREN |
| Org-scoping cardinal (4 JOINs IDOR-safe) | 9/10 | ✅ Pattern strict, KPI canonique post P1-CR-003 |
| **Règle 1 — facture sans contrat = bloquante** | 10/10 | ✅ Triple verrouillage, FR doctriné |
| **Règle 2 — anomalie complète obligatoire** | 5/10 | ❌ `actual_value` nullable, pas de FK Evidence/Action, pas de test rejet |
| Couverture contractuelle (perimeter_check + contract_coverage) | 8/10 | ✅ Service dédié, statuts cardinaux |
| Audit Engine (10 règles + 11 codes BillAnomaly) | 8/10 | ✅ Détecteurs résilients, `details_json` riche |
| Shadow Billing V2 (4 composantes) | 8/10 | ✅ V2 engine + V1 fallback, explainability livrée |
| Pages FE (`/bill-intel`, `/billing`) | 8/10 | ✅ 2 pages distinctes, navigation bidirectionnelle, FR strict |
| Tests | 7/10 | ✅ 2250 lignes / 6 fichiers, source-guards P0-C présents — lacune E2E ingestion→anomalie |
| Dead code FE (6 API exports jamais consommées) | 6/10 | ⚠️ À déprécier en stubs (pattern P1.5 conformité) |

### 3 risques majeurs P0 — à clôturer avant le prochain sprint

1. **Anomalies avec `actual_value=NULL` non explicitement rejetées** — la colonne est nullable, les détecteurs peuplent toujours mais sans CHECK constraint ni assertion. KPI VNU dormant `0,0 €` observé live malgré 52 anomalies. **Fix** : assertion en pipeline R19-R31 + migration `actual_value NOT NULL` après scan DB.

2. **Pas de modèle Evidence/Proof formel pour les anomalies** — les preuves vivent dans `details_json` (champ JSON semi-structuré). Aucune FK vers `Evidence` V4 ou table dédiée `BillAnomalyEvidence`. **Fix P1 billing** : créer `BillAnomalyEvidence(anomaly_id FK, file_url, hash, timestamp)` + endpoint download (cf. pattern Evidence V4 conformité C6 P1).

3. **`POST /api/billing/audit-all` retourne HTTP 500 sans JWT en DEMO mode** — devrait retourner 401 `NO_ORG_CONTEXT` comme `/conformite/sync-remediation-actions`. **Fix immédiat** : aligner sur le pattern V4 ou ajouter une garde org_id explicite.

### 2 risques P1 — à inscrire au backlog

4. **Pas de FK action vers `ActionCenterItem`** — les anomalies suggèrent des actions via `BillingInsight.recommended_actions_json` mais aucun item n'est créé. Reproduit le gap "boucle non fermée" identifié sur Conformité (résolu en P1 par `POST /api/conformite/sync-remediation-actions`).

5. **6 fonctions API FE jamais consommées** : `getBillingRules`, `auditInvoice`, `patchBillingInsight`, `getImportBatches`, `getBillingAnomaliesScoped`, `getNormalizedInvoices`. **Fix** : les transformer en stubs Error JS (pattern P1.5 conformité C3) ou les supprimer.

### Verdict pour le passage à la brique suivante

🟡 **GO conditionnel — passer au sprint Bill Intelligence P1** (items 1-3 P0 ci-dessus) **avant** d'attaquer une autre brique. Une fois ces P0 livrés :
- KPI VNU fiable (assertion `actual_value`)
- Preuves opposables (FK BillAnomalyEvidence)
- Boucle anomalie → action fermée (similaire à conformité P1)

→ La brique sera prête pour passage en revue clients DAF.

### Doctrine respectée

- ✅ `/conformite` hub unique respecté pour le billing (pas de cross-menu)
- ✅ Module `facturation` isolé
- ✅ Aucun menu ACC / PMO / Flex / Partner Hub
- ⚠️ Faute d'audit P1 Conformité §10 : sous-items DT / APER restent dans la sidebar — à corriger dans un sprint séparé `cleanup-sidebar-conformite-souitems` (hors scope billing)

---

*Audit clôturé le 2026-05-23 sur `claude/refonte-sol2 @ 79a3d2a1`. Mode READ-ONLY
strict respecté — aucune modification de code. Méthode conforme
[[feedback-audit-sprint-visuel-fonctionnel]] : 3 agents Explore parallèles +
audit fonctionnel curl (10 cas) + audit visuel Playwright golden path
(`/bill-intel`, `/billing`, `/patrimoine` anti-régression). Captures hors
repo dans `/tmp/promeos-audit-billing/`.*

---

## 14. Corpus documentaire Bill Intelligence analysé (mise à jour 2026-05-24)

Phase 0-bis exploration documentaire profonde réalisée le 2026-05-24 — doc dédié :
[phase_0bis_exploration_drive_billing_2026_05_24.md](phase_0bis_exploration_drive_billing_2026_05_24.md).

### 14.1 Couverture corpus

| Source | Volume analysé | Output |
|---|---|---|
| 17 PDFs CRE locaux (`docs/base_documentaire/CRE/`) | TURPE 7 HTA-BT (CRE 2025-40 + 2025-77), ATRT 8 (2025-270), ATRD 7 ELD (2026-15), CTA (2026-14), CART-P (2026-44), GRDF non péréqué (2026-48), minoration VNU 2026 (2026-52), capacité 2026-2027 (2026-43), 4 délibérations CRE annexes (2026-49/54/61/62/63/67) | Verbatim formules (CS, CMDPS, CG, CC, CACNC), constantes (12,41 €·h, 6,48 € bimestriel, CTA 15% post 02/2026), évolution annuelle Z=IPC+X+k |
| 10 PDFs Enedis locaux | Flux F15 CACNC (6 cas codés), API SGE Mesures/Point/Affaires v0 (mai 2026), homologations V25.6→V26.2, mapping R6X, reprogrammation HC, référentiel listes de valeurs | Référentiel codes FTA, segments C1-C5, plages tarifaires |
| 8 skills `.claude/skills/` (~2000 lignes) | `promeos-billing`, `bill-intelligence-fr`, `promeos-enedis`, `promeos-energy-market`, `energy-contracts-b2b`, `cee-p6`, `energy-autoconsommation`, `promeos-regulatory` | 5 règles bien couvertes, 5 partielles, 5 manquantes |
| Google Drive (80+ hits) | 7 dossiers déjà connus + **5 nouveaux à ajouter à memory** | Templates Energisme schéma facture (80+ champs), 30 factures réelles golden set OCR, brochure tarifaire TURPE 7 officielle CRE 2025-78, doc anatomie facture RTE HTB |

### 14.2 Verbatim officiels acquis (extraits)

- **Formule TURPE 7 CS** (CRE 2025-78) : `CS = b₁·P₁ + Σ bᵢ·(Pᵢ–Pᵢ₋₁) + Σ cᵢ·Eᵢ`
- **CMDPS HTA** (CRE 2025-78) : `Σ 0,04·bᵢ·√Σ(ΔP²)` (vs constante PROMEOS = formule différente — à valider)
- **CMDPS BT >36 kVA** : `12,41 €·h` (vs constante PROMEOS 12,65 — **divergence à clarifier**)
- **CACNC non-Linky** : socle 6,48 €/bimestre + maj 4,14 €/bimestre si non-communication index
- **Évolution annuelle TURPE 7** : `Z = IPC + X (=−0,35%) + k (∈ [−3%, +3%])`
- **CTA** : 15% × part fixe TURPE depuis 02/2026 (historique 27,04% avant 08/2021, 21,93% avant 02/2026)
- **Accise élec** : T1 = 30,85 €/MWh (ménages), T2 = 26,58 €/MWh (PME/pro) depuis 01/02/2026 — appliquer **taux à la date de conso**, pas la date de facture
- **Accise gaz (TICGN)** : 16,39 €/MWh (10,73 base + 5,66 ZNI) depuis 02/2026
- **Flux F15 CACNC** : 6 cas codés (F5/F6/F1/F2 + cessation + annulation) avec valeurs ASCS-E=+6,48, ASCS-R=−6,48, ASCS-F-U=+2,12 prorata, ASCA=4,14

### 14.3 Matrice règles (résumé — détail dans Phase 0-bis)

- **Électricité fourniture** : 4 règles cardinales (composante énergie, prix indexé, minoration VNU, prix négatifs marché)
- **Électricité acheminement (TURPE 7)** : 11 règles (CS, CG, CC, CMDPS HTA + BT>36, CER, CACS, CACNC, CT, formule évolution, réforme HC)
- **Électricité taxes** : 7 règles (CTA versioning, accise élec versioning, TVA 5,5%, TVA 20%, somme TVA, capacité, CEE)
- **Gaz** : 6 règles (fourniture, ATRD 7 par option, ATRT 8, CTA gaz, TICGN, dépassement CJN)
- **Régularisations** : 5 règles (CACNC ASCS, avoirs, régul annuelle, hausse après baisse HTB, index relevé vs estimé)
- **Anomalies transverses** : 23 codes (R001..R027) dont 5 nouveaux à créer en P1 (R022/R023/R024/R025/R026/R027)

### 14.4 Impact sur les 3 risques P0 de cet audit

| P0 audit Bill Intel | Source canonique Phase 0-bis | Plan correction P1 |
|---|---|---|
| **`BillAnomaly.actual_value` nullable** | Skill `promeos-billing` + tous détecteurs R19-R31 peuplent toujours `details_json` | Assertion runtime + plan migration `NOT NULL` après scan DB |
| **Pas de FK Evidence formelle** | Templates Energisme + flux F15 Enedis + factures golden set 30 PDFs | Créer `BillAnomalyEvidence` (pattern Evidence V4 conformité C6 P1) + endpoint download |
| **`POST /api/billing/audit-all` HTTP 500** | Pattern V4 `populate_org_context` éprouvé (conformité P1) | Retour FR `NO_ORG_CONTEXT` 401 (pattern conformité P1) |

### 14.5 Constantes canoniques manquantes en code

| Constante | Valeur cible | Status | Source officielle |
|---|---|---|---|
| `CEE_PRIX_MWHC_CUMAC_EUR` | 8,50 | ❌ absente `constants.py` | Skill `cee-p6` p.44 + arrêté DGEC P6 |
| `BACS_SEUIL_2025` | 290 kW | ❌ absente `constants.py` | Décret 2020-887 |
| `BACS_SEUIL_2030` | 70 kW | ❌ absente `constants.py` | Décret 2023-259 + 2025-1343 |
| `CMDPS_COEFFICIENT` | **12,41** (CRE) vs **12,65** (PROMEOS actuel) | ⚠️ **divergence** | CRE 2025-78 |

### 14.6 Note de qualité

1 doc interne PROMEOS identifié comme **généré par ChatGPT** avec **facteurs CO₂ erronés** (0,079 kgCO₂/kWh élec vs 0,052 canonique ADEME V23.6). À isoler / archiver — toute reprise = bug data quality.

### 14.7 Mise à jour verdict suite Phase 0-bis

**Note brique Bill Intelligence : maintenue à 7/10** post-Phase 0-bis. La cartographie code restait correcte ; la Phase 0-bis confirme la solidité de l'org-scoping et de la Règle 1, et chiffre l'effort de durcissement R2 (FK Evidence + 5 anomalies à créer + grilles gaz ATRD/ATRT à importer).

**Verdict ajusté** : 🟡 **GO conditionnel pour sprint Bill Intelligence P1** — corpus documentaire validé, sources officielles disponibles, gap par règle documenté. Le sprint peut démarrer avec un cadre canonique de 60+ règles documentées.
