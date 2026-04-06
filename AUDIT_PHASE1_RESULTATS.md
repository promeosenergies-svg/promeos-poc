# HELIOS — AUDIT PHASE 1 : RÉSULTATS COMPLETS

**Date** : 2026-04-05
**Périmètre** : PROMEOS/HELIOS — `c:\Users\amine\promeos-poc\promeos-poc`
**Auditeur** : Claude Code (Opus 4.6)
**Durée** : 6 axes exécutés en 3 jours parallélisés

---

## TABLE DES MATIÈRES

1. [A1 — Structure & Navigation](#a1--structure--navigation)
2. [A2 — Données & Seed](#a2--données--seed)
3. [A3 — Moteurs Réglementaires](#a3--moteurs-réglementaires)
4. [A4 — Shadow Billing](#a4--shadow-billing)
5. [A5 — UX & Parcours Démo](#a5--ux--parcours-démo)
6. [A6 — Ingestion Données Réelles](#a6--ingestion-données-réelles)
7. [Consolidation Finale](#consolidation-finale)
8. [Résumé Exécutif](#résumé-exécutif)

---

## A1 — Structure & Navigation

**Score : 7/10** · P0: 2 · P1: 4 · P2: 8

### Cartographie

- **47 routes** dont 24 alias/redirects et 1 catch-all (`App.jsx`)
- **4 fichiers pages orphelins** (dead code) : `Dashboard.jsx`, `ActionPlan.jsx`, `CompliancePage.jsx` (@deprecated), `EnergyCopilotPage.jsx`

### Findings

| # | Finding | Fichier:ligne | Sévérité | Effort fix | Impact pilote |
|---|---------|--------------|----------|------------|---------------|
| 1 | Boutons "Modifier"/"Appliquer" planning `onClick={() => {}}` — noop visible en démo | `MonitoringPage.jsx:1013,1017` | **P0** | S | Bloquant |
| 2 | Texte "Brique 1" visible dans l'UI prospect ("Connectez-vous à votre patrimoine (Brique 1)") | `PurchaseAssistantPage.jsx:626` | **P0** | XS | Bloquant |
| 3 | Route `/action-center` sans `<PageSuspense>` — crash Suspense possible au lazy-load | `App.jsx:237` | P1 | XS | Visible |
| 4 | Route `/action-center` absente de NavRegistry et ROUTE_MODULE_MAP — page orpheline non navigable | `App.jsx:237` + `NavRegistry.js` | P1 | S | Visible |
| 5 | Bouton "Compléter les données du contrat" — CustomEvent `promeos:navigate` sans listener, navigation morte | `ShadowBreakdownCard.jsx:263` | P1 | S | Visible |
| 6 | Texte "post-ARENH" dans le PDF Pack RFP export | `ExportPackRFP.jsx:164` | P1 | XS | Visible |
| 7 | Fichier `Dashboard.jsx` orphelin, aucune route ni import — dead code | `frontend/src/pages/Dashboard.jsx` | P2 | XS | Mineur |
| 8 | Fichier `ActionPlan.jsx` orphelin, aucune route ni import — dead code | `frontend/src/pages/ActionPlan.jsx` | P2 | XS | Mineur |
| 9 | Fichier `CompliancePage.jsx` marqué `@deprecated` toujours présent | `frontend/src/pages/CompliancePage.jsx:2` | P2 | XS | Mineur |
| 10 | Fichier `EnergyCopilotPage.jsx` dead code, import commenté, route redirige vers `/` | `frontend/src/pages/EnergyCopilotPage.jsx` + `App.jsx:50` | P2 | XS | Mineur |
| 11 | Fichier `AnomalyActionModal.jsx` marqué `DEPRECATED (V92)` toujours présent | `frontend/src/components/AnomalyActionModal.jsx:2` | P2 | XS | Mineur |
| 12 | Fichier `domain/purchase/types.js` contient 2 exports `@deprecated V100` | `frontend/src/domain/purchase/types.js:80,93` | P2 | XS | Mineur |
| 13 | Fichier `domain/purchase/assumptions.js` contient export `@deprecated V100` | `frontend/src/domain/purchase/assumptions.js:9` | P2 | XS | Mineur |
| 14 | Imports `no-unused-vars` (eslint-disable) dans 4 pages de production | `Patrimoine.jsx`, `RegOps.jsx`, `Dashboard.jsx`, `Site360.jsx`, `AperPage.jsx` | P2 | XS | Mineur |

### Synthèse A1

Les 2 P0 sont critiques pour une démo pilote :
- Le label "Brique 1" visible par un prospect est un signal POC immédiat (fix: remplacer par "votre patrimoine").
- Les boutons noop "Modifier"/"Appliquer" dans Monitoring donnent une impression d'inachevé (fix: ajouter un toast ou masquer).

---

## A2 — Données & Seed

**Score : 7/10** · Module Achat : OUI · Cohérence KPIs : OUI avec réserve

### État du seed

- **Orchestrateur principal** : `demo_seed/orchestrator.py` — RNG locale déterministe (`random.Random(42)`), idempotent
- **Seed market** : `gen_market_prices.py` — déterministe (sin/cos), 36 mois 2024-2026
- **Seed legacy** : `purchase_seed.py` — **non idempotent**, prix aberrants

### Cohérence KPIs

- **Source of Truth compliance_score** : `RegAssessment` → `compliance_score_service.py` (DT 45% + BACS 30% + APER 25%) → `cockpit.py` → frontend. Chaîne respectée.
- **Exception** : `Patrimoine.jsx:766` recalcule `(conformes/total)*100` côté front — viole la règle "no-calc-in-front"
- **contract_risk_eur** : stubbé à 0 dans `cockpit.py:217`

### Module Achat / EPEX

- **Backend** : 15+ endpoints `/api/purchase/*` + `/api/market/*` complets
- **Frontend** : `PurchasePage.jsx` (maturité V82), `PurchaseAssistantPage.jsx`, `MarketWidget.jsx`
- **Seed market orchestrateur** : déterministe, forward curves incluses

### Formatters

- 259 utilisations de formatters centralisés (`fmtEur`, `fmtKwh`, `fmtNum`...)
- **281 formatters manuels résiduels** (30x `.toFixed()`, 87x `.toLocaleString()`, 164x `Math.round()` nu)
- Ratio centralisé/manuel : ~48% — insuffisant

### Findings

| # | Finding | Fichier:ligne | Sévérité | Effort fix | Impact pilote |
|---|---------|--------------|----------|------------|---------------|
| 1 | **purchase_seed.py non idempotent** — pas de garde INSERT OR IGNORE. Re-run crée des doublons PurchaseAssumptionSet/ScenarioResult | `purchase_seed.py:46-125` | **P0** | S | Bloquant |
| 2 | **Prix réf 0.18 EUR/kWh** alors que DEFAULT_PRICE_ELEC recalibré à 0.068. Écart x2.6 sur scénarios achat | `purchase_seed.py:70,140` | **P0** | XS | Bloquant |
| 3 | **Patrimoine.jsx recalcule conformité front** : `Math.round((conformes/total)*100)` viole "no-calc-in-front". Diverge du score composite | `Patrimoine.jsx:766` | P1 | XS | Visible |
| 4 | **contract_risk_eur stub à 0** dans cockpit.py. Risque contrat jamais remonté | `cockpit.py:217` | P1 | S | Visible |
| 5 | Variable mal nommée `actionsActives` — calcule un sub-score readiness, pas un compte d'actions. Fallback 80 arbitraire | `Cockpit.jsx:200-201` | P2 | XS | Mineur |
| 6 | seed_market_demo.py (legacy) non déterministe — `random.gauss` sans `random.seed` | `seed_market_demo.py:65-70` | P2 | XS | Mineur |
| 7 | 30x `.toFixed()` sans guard anti-NaN dans pages JSX (MarketWidget 6, MonitoringPage 5, Site360 4) | Multiples | P2 | S | Mineur |
| 8 | 87x `.toLocaleString()` manuels — bypass formatters centralisés | Multiples | P2 | M | Mineur |
| 9 | Cockpit.jsx:201 calcul readiness sub-score côté front, dupliqué dans dashboardEssentials.js:483 | `Cockpit.jsx:201` | P2 | S | Mineur |
| 10 | MarketWidget.jsx : `.toFixed()` direct sur data.decomposition sans null check — crash si API null | `MarketWidget.jsx:237` | P2 | XS | Mineur |

---

## A3 — Moteurs Réglementaires

**Score : 6/10** · DT: PARTIEL · BACS: PARTIEL · APER: OK · CEE: STUB · Export OPERAT: PARTIEL

### Présence des moteurs

| Moteur | Fichiers principaux | Présent |
|--------|-------------------|---------|
| **Décret Tertiaire (DT)** | `regops/rules/tertiaire_operat.py`, `services/operat_trajectory.py`, `services/dt_trajectory_service.py`, `services/tertiaire_modulation_service.py` | OUI |
| **BACS** | `services/bacs_engine.py`, `regops/rules/bacs.py`, `services/bacs_compliance_gate.py`, `services/bacs_ops_monitor.py`, `models/bacs_models.py`, `regulations/bacs/v2.yaml` | OUI |
| **APER** | `regops/rules/aper.py` | OUI |
| **CEE P6** | `regops/rules/cee_p6.py`, `services/cee_service.py`, `regops/config/cee_p6_catalog.yaml` | OUI (partiel) |

### RegAssessment comme source de vérité

- `RegAssessment` (`models/reg_assessment.py`) = cache persistant
- Orchestrateur `regops/engine.py` évalue les 4 frameworks, persiste dans RegAssessment
- Score unifié : `compliance_score_service.py` (DT 45% + BACS 30% + APER 25% - pénalité critiques max 20 pts)
- Endpoints : `GET /api/regops/site/{id}`, `GET /api/regops/score_explain`, `POST /api/regops/recompute`, `GET /api/regops/dashboard`

### Export OPERAT

- **CSV fonctionnel** : `operat_export_service.py` + `routes/operat.py` (POST /api/operat/export, preview, validate, manifests)
- **Frontend** : `ExportOperatModal.jsx` — modal avec sélection année, preview, download CSV
- **Format** : CSV conforme au format ADEME (17 colonnes)
- **Bug** : `_get_site_conso` classe tout en électricité — `gaz_kwh` toujours 0

### Vérification des calculs

**DT — Décret Tertiaire :**
- Trajectoire -40%/-50%/-60% (2030/2040/2050) : CORRECT
- DJU méthode COSTIC base 18°C via Open-Meteo : CORRECT
- Seuil assujettissement 1000 m2 : CONFORME (Décret n°2019-771)
- Pénalités 7500/1500 EUR : CONFORMES
- MAIS : le moteur regops ne calcule pas l'écart trajectoire (délégué à un service séparé)

**BACS :**
- Tier 1 > 290 kW / 2025-01-01 : CORRECT (Décret 2020-887)
- Tier 2 > 70 kW / 2030-01-01 : CORRECT (report décret 2025-1343)
- Calcul Putile (CASCADE/NETWORK vs INDEPENDENT) : CORRECT
- TRI exemption > 10 ans : CORRECT
- **MAIS : classe EN 15232 (A/B/C/D) NON évaluée dans le scoring** — un site GTB classe D serait marqué conforme

**APER :**
- Parking >= 10000 m2 / 2026-07-01 : CORRECT (Loi APER art. 40)
- Parking >= 1500 m2 / 2028-07-01 : CORRECT
- Toiture >= 500 m2 / 2028-01-01 : CORRECT
- Couverture 50% : CORRECT
- MAIS : pas de prise en compte des preuves d'installation existante

**CEE P6 :**
- Classification "financement" : CORRECT
- Catalogue 10 fiches : PRÉSENT
- **Calcul kWhc cumac : ABSENT** — aucune formule fiche x surface x zone x durée de vie

### Findings

| # | Finding | Fichier:ligne | Sévérité | Effort fix | Impact pilote |
|---|---------|--------------|----------|------------|---------------|
| 1 | **BACS : classe EN 15232 non évaluée** — le modèle stocke `system_class` (A/B/C/D) mais le moteur ne vérifie pas classe B minimum. Site GTB classe D marqué conforme | `bacs_engine.py` (absent) | **P0** | M (2-3j) | Bloquant |
| 2 | **Export OPERAT : gaz toujours à 0** — `_get_site_conso` classe tout en `elec_kwh` sans vérifier le type d'énergie | `operat_export_service.py:78` | **P0** | S (1j) | Bloquant |
| 3 | **CEE P6 : aucun calcul kWhc cumac auto** — catalogue OK, modèle OK, mais aucun moteur de calcul | `regops/rules/cee_p6.py:8-37` | P1 | L (3-5j) | Visible |
| 4 | **APER : pas de preuves installation existante** — faux positifs AT_RISK pour sites déjà équipés | `regops/rules/aper.py:9-109` | P1 | S (1-2j) | Visible |
| 5 | **RegAssessment scoring mono-row** — si un assessment couvre DT+BACS+APER, même `compliance_score` pour les 3. Pas de granularité framework | `compliance_score_service.py:367-406` | P1 | S (2j) | Visible |
| 6 | **DT regops ne calcule pas la trajectoire** — le finding ne dit pas si le site est on_track ou off_track pour 2030 | `regops/rules/tertiaire_operat.py:9-126` | P1 | S (1-2j) | Visible |
| 7 | BACS `cvc_alerts_count` hardcodé à 3 (stub) — dashboard ops toujours affiché à 3 | `bacs_ops_monitor.py:56` | P2 | XS | Mineur |
| 8 | DT `delta_percent` calculé vs `applicable_kwh`, pas vs baseline — non standard OPERAT | `operat_trajectory.py:257` | P2 | XS | Mineur |
| 9 | BACS YAML vs code legacy : constantes dupliquées, risque de désynchronisation | `bacs_engine.py:60-62` | P2 | XS | Mineur |
| 10 | DT `tertiaire_operat.py` moteur regops ne fait que vérifier statut OPERAT, pas trajectoire réelle | `tertiaire_operat.py:9-126` | P2 | S | Mineur |

---

## A4 — Shadow Billing

**Score : 8/10** · TURPE V7 : OUI · 34 règles anomalies · Export CSV : PARTIEL

### TURPE V7

**3 segments couverts (100+ codes tarifaires) :**

| Segment | Gestion | Comptage | Soutirage fixe | Soutirage variable | Options |
|---------|---------|----------|----------------|-------------------|---------|
| C5 BT (<=36 kVA) | 16.80 EUR/an | 22.00 EUR/an | CU4/MU4/LU/CU/MUDT | CU4(4p), MU4(4p), LU, CU, MUDT(HP/HC), Base, HP/HC | 7 options |
| C4 BT (>36 kVA) | 217.80 EUR/an | 283.27 EUR/an | CU(4p), LU(4p) | CU(4p), LU(4p), CMDPS | 2 options |
| C3 HTA | 435.72 EUR/an | 376.39 EUR/an | CU(5p), LU(5p) | CU(5p), LU(5p), CMDPS, réactive, CER | 2 options |
| C2/C1/HTB | **NON** | **NON** | **NON** | **NON** | 0 |

### Détection d'anomalies (34 règles)

**Moteur 1 — billing_service.py (14 règles ORM/DB) :**
Shadow gap (>20%), prix unitaire élevé (>0.30/0.15), doublons facture, période manquante, période trop longue (>62j), kWh négatifs, montant zéro, somme lignes != total (>2%), pic conso (>2x moyenne), dérive prix (>15%), cohérence TTC (>2% et >5 EUR), expiration contrat (0j/<90j), TURPE mismatch (>15%), taxes mismatch (>10%). Anti-stacking intelligent (R1 → skip R10/R13/R14).

**Moteur 2 — audit_rules_v0.py (20 règles dataclass/facture) :**
Somme composantes vs total HT, TTC=HT+TVA, TVA taux/montant, Qté x PU = montant, dates cohérentes, composantes obligatoires (accise, CTA), montant négatif, composante opaque, doublon composante, conso composantes vs globale, base accise vs conso, prix unitaire plage crédible, période >35j, facture sans composante, total TTC=0, PDL/PCE manquant, somme TVA vs total TVA, pénalité/dépassement, montant total élevé (>50k).

### Taxes & composantes

| Composante | Statut | Détail |
|------------|--------|--------|
| Accise électricité | COMPLET | 9 taux versionnés 2023-2026 (T1/T2) |
| Accise gaz | COMPLET | 4 taux versionnés 2023-2026 |
| CTA | COMPLET | 21.93% → 27.04% au 01/01/2026 |
| TVA | COMPLET | 5.5% → 20% au 01/08/2025 (bascule automatique) |
| Capacité | PRESENT | CAPACITE_ELEC_2025, réforme nov 2026 |
| TCFE | ABSENTE | Absorbée dans accise depuis réforme 2022 |
| VNU | DORMANT | Documenté dans YAML, pas dans moteur |
| Gaz (ATRD/ATRT/stockage/CPB/TDN) | COMPLET | Moteur engine V2 |

### Findings

| # | Finding | Fichier:ligne | Sévérité | Effort fix | Impact pilote |
|---|---------|--------------|----------|------------|---------------|
| 1 | **Pas de bouton export CSV anomalies côté frontend** — API `/api/bill/anomalies/csv` existe mais non connectée | `BillIntelPage.jsx` | P1 | XS (0.5j) | Visible |
| 2 | Segments C2/C1/HTB non supportés — retourne "segment non supporté" | `billing_engine/engine.py:167` | P2 | M (2-5j) | Mineur (rare PME) |
| 3 | Docstrings CTA erronées — dit "15%" au lieu de 27.04%. Code correct | `billing_engine/engine.py:333-334` | P2 | XS | Mineur |
| 4 | Seed démo utilise TURPE 6 pour montants réseau (0.0313 EUR/kWh C4 BT) | `billing_seed.py:68-95` | P2 | XS | Mineur |

### Synthèse A4

Le module shadow billing est le plus mature du projet. Les grilles TURPE 7 sont exceptionnellement détaillées avec résolution temporelle. Les 34 règles d'anomalies couvrent tous les cas courants avec anti-stacking intelligent. Le seul gap visible en démo est l'absence de bouton "Exporter CSV" dans l'UI.

---

## A5 — UX & Parcours Démo

**Score : 7/10** · Frictions parcours 2min : 3 · Frictions parcours 10min : 7

### Loading & Error States

**Pages critiques avec bonne couverture :**
Cockpit, Site360, ConformitePage, BillingPage, BillIntelPage, MonitoringPage, PurchasePage, ActionsPage, AnomaliesPage — tous avec SkeletonCard/SkeletonTable + ErrorState.

**Pages avec gaps :**

| Page | Loading | Error | Risque |
|------|---------|-------|--------|
| Contrats.jsx | SkeletonTable OK | **AUCUN** — skeleton infini si API fail | HAUT |
| ActionPlan.jsx | Texte "Chargement..." brut | Texte rouge brut, pas de retry | HAUT |
| CompliancePipelinePage.jsx | animate-pulse OK | Toast seul, page vide | MOYEN |
| PortfolioReconciliationPage.jsx | OK | **AUCUN** | BAS |
| PaymentRulesPage.jsx | OK | **AUCUN** | BAS |

### Empty States

- **98+ messages vides** "Aucun/Aucune" dans le frontend — bonne couverture générale
- **Gaps identifiés** : `Contrats.jsx` (filtre texte sans message vide), `ContractRadarPage.jsx` (listes avantages/inconvénients), `AdminRolesPage.jsx`, `PerformanceSitesCard.jsx`

### Navigation inter-modules

- Registry de routes propre avec 17 helpers (`services/routes.js`)
- Cockpit → Site360, Actions, Conformité : OK
- Anomalies → BillIntel, Conformité, Patrimoine : OK
- Purchase → Monitoring, ConsoDiag : OK
- **Problème** : double cockpit `CommandCenter.jsx` (useCommandCenterData) vs `Cockpit.jsx` (useCockpitData)

### Responsive

- 137 breakpoints Tailwind dans 64 fichiers — couverture correcte
- 32 tailles fixes en pixels — acceptable (colonnes table, badges)
- Pages sans breakpoint : `ActionPlan.jsx`, `RegOps.jsx`, `PortfolioReconciliationPage.jsx`

### Findings

| # | Finding | Page / Composant | Sévérité | Effort fix | Visibilité en démo |
|---|---------|-----------------|----------|------------|-------------------|
| 1 | **Contrats.jsx : pas d'error state** — skeleton infini si API échoue, puis tableau vide | `Contrats.jsx` | **P0** | S | Haute |
| 2 | **ActionPlan.jsx : loading primitif** — texte brut "Chargement..." + error texte rouge sans retry + pas de PageShell (header gradient custom) | `ActionPlan.jsx` | **P0** | S | Haute |
| 3 | **CompliancePipeline : error = toast seul** — page reste vide si API échoue | `CompliancePipelinePage.jsx` | P1 | S | Moyenne |
| 4 | **Double cockpit CommandCenter + Cockpit** — confusion navigation, 2 points d'entrée | `CommandCenter.jsx` / `Cockpit.jsx` | P1 | L | Haute |
| 5 | **Cockpit 5+ useEffect fetches parallèles** — popcorn loading, flash de contenu | `Cockpit.jsx` | P1 | M | Haute |
| 6 | **Contrats.jsx : filtre texte sans empty state** — table vide silencieuse si aucun match | `Contrats.jsx` | P1 | XS | Moyenne |
| 7 | ActionPlan.jsx : aucun breakpoint responsive | `ActionPlan.jsx` | P2 | M | Moyenne |
| 8 | PortfolioReconciliationPage.jsx : pas d'error state | `PortfolioReconciliationPage.jsx` | P2 | S | Basse |
| 9 | PaymentRulesPage.jsx : pas d'error state | `PaymentRulesPage.jsx` | P2 | S | Basse |
| 10 | AdminRolesPage : table vide sans message | `AdminRolesPage.jsx` | P2 | XS | Basse |
| 11 | cockpit/PerformanceSitesCard : pas de message vide post-loading | `PerformanceSitesCard.jsx` | P2 | XS | Basse |
| 12 | Contrats.jsx : search input taille fixe w-[280px] — non responsive | `Contrats.jsx` | P2 | XS | Basse |
| 13 | Cockpit : certains fetch errors silencieusement mis à null — KPI affiche "-" | `Cockpit.jsx` | P2 | S | Moyenne |

### Parcours démo — frictions par durée

**Parcours 2 min (Cockpit → Site360 → retour) :**
1. Double cockpit : confusion potentielle
2. Popcorn loading au chargement Cockpit (5 fetches)
3. KPIs qui affichent "-" si un fetch échoue silencieusement

**Parcours 10 min (Cockpit → Conformité → Actions → Contrats → Purchase) :**
4. Contrats sans error state
5. CompliancePipeline sans error visible
6. ActionPlan loading primitif + rupture visuelle
7. Contrats filtre sans empty state

---

## A6 — Ingestion Données Réelles

**Score : 7/10** · Feature CRITIQUE pour transformer la démo en pilote

### 1. Ce qui existe déjà (fondation solide)

**Endpoints d'import (9 endpoints fonctionnels) :**

| Endpoint | Description | Statut |
|----------|-------------|--------|
| `POST /api/patrimoine/staging/import` | Import CSV/Excel patrimoine dans pipeline staging | MATURE |
| `GET /api/patrimoine/import/template` | Template CSV/XLSX officiel avec feuille Aide | MATURE |
| `POST /api/billing/import-csv` | Import CSV factures (idempotent SHA-256) | FONCTIONNEL |
| `POST /api/billing/import-pdf` | Import PDF facture (parse EDF/Engie) | FONCTIONNEL |
| `POST /api/energy/import/upload` | Import CSV/XLSX/JSON relevés conso | FONCTIONNEL |
| `POST /api/import/sites` | Import CSV sites (legacy, standalone) | LEGACY |
| `GET /api/import/template` | Template CSV legacy | LEGACY |
| `POST /api/patrimoine/staging/import-invoices` | Import sites depuis metadata factures | FONCTIONNEL |
| `POST /api/patrimoine/{id}/sync` | Sync incrémentale fichier vs existant | FONCTIONNEL |

**Pipeline staging patrimoine (6 étapes) :**
1. Import (CSV/Excel) → StagingBatch + StagingSite + StagingCompteur
2. Quality Gate : règles de qualité (blocking/critical/warning/info)
3. Autofix : normalisation automatique (trim, code_postal, type_compteur)
4. Corrections manuelles : fix endpoint (merge, skip, edit)
5. Activation : transfert staging → tables finales
6. Rapport : export CSV post-import avec statuts

**Service import_mapping.py (world class) :**
- 22 colonnes canoniques (site + compteur + contrat + bâtiment + multi-entité)
- ~150 synonymes FR/EN auto-détectés (ex: "CP" → code_postal, "PRM" → delivery_code)
- Détection auto encodage (UTF-8/Latin-1/BOM) et délimiteur
- Normalisation valeurs : 30+ synonymes types de site, types compteur, codes postaux

**Modèles de données (tous en place) :**
Site, Compteur, DeliveryPoint, Meter, EnergyContract, EnergyInvoice, EnergyInvoiceLine, Consommation, MeterReading, DataImportJob, BillingImportBatch, StagingBatch/Site/Compteur

**Data lineage :** `data_source`, `data_source_ref`, `imported_at`, `imported_by` sur Site/Compteur/DeliveryPoint

**Frontend :**
- `PatrimoineWizard.jsx` — wizard 6 étapes (le vrai pipeline d'import)
- `ImportPage.jsx` — page legacy avec drag-drop + Demo Packs (redirige vers PatrimoineWizard)
- `BillIntelPage.jsx` — upload PDF/JSON factures

### 2. Ce qui manque

| # | Composant manquant | Description | Effort |
|---|--------------------|-------------|--------|
| 1 | **Resolver PRM→site_id dans import factures** | L'import factures requiert un `site_id` numérique. Un prospect fournirait un PRM ou un nom de site | S |
| 2 | **Mapping synonymes colonnes factures** | L'import factures CSV attend des colonnes exactes — pas de mapping flexible comme pour les sites | M |
| 3 | **Import relevés sans meter_id pré-créé** | L'endpoint `/api/energy/import/upload` exige un `meter_id` existant — un prospect ne connaît pas les IDs internes | S |
| 4 | **Import contrats CSV** | Aucun endpoint d'import CSV pour EnergyContract — seulement création unitaire via API JSON | M |
| 5 | **UI unifiée "Charger mes données"** | Les 4 types d'import sont sur des pages/endpoints différents — besoin d'un point d'entrée unique | L |
| 6 | **Templates factures & conso** | Le template CSV/XLSX officiel ne couvre que sites/compteurs | XS |
| 7 | **Rapport d'import consolidé multi-entité** | Après import, pas de vue récapitulative multi-entité | S |
| 8 | **Validation métier factures** | Pas de quality gate staging pour les factures (doublons période, incohérence kWh vs montant) | S |
| 9 | **Documentation utilisateur** | Pas de guide "préparez vos données" pour un prospect | S |
| 10 | **Progress bar upload** | Pas de feedback progressif sur les gros fichiers | XS |

### 3. Colonnes minimum requises par entité

**Site :**
| Colonne | Obligatoire | Format |
|---------|-------------|--------|
| `nom` | OUI | Texte libre (200 car max) |
| `type` | Recommandé | bureau/commerce/usine/hotel/sante/enseignement/entrepot/... |
| `adresse` | Recommandé | Texte libre |
| `code_postal` | Recommandé | 5 chiffres |
| `ville` | Recommandé | Texte libre |
| `surface_m2` | Recommandé | Nombre |

**Compteur / Point de livraison :**
| Colonne | Obligatoire | Format |
|---------|-------------|--------|
| `delivery_code` (PRM/PDL/PCE) | Recommandé | 14 chiffres |
| `type_compteur` | Recommandé | electricite/gaz/eau |
| `puissance_kw` | Optionnel | Nombre |

**Facture :**
| Colonne | Obligatoire | Format |
|---------|-------------|--------|
| `invoice_number` | OUI | Texte unique |
| `site_id` ou `PRM` | OUI | Entier ou 14 chiffres |
| `period_start` | Recommandé | YYYY-MM-DD |
| `period_end` | Recommandé | YYYY-MM-DD |
| `total_eur` | Recommandé | Nombre (EUR TTC) |
| `energy_kwh` | Recommandé | Nombre |

**Relevé de consommation :**
| Colonne | Obligatoire | Format |
|---------|-------------|--------|
| `timestamp` | OUI | ISO 8601 ou YYYY-MM-DD HH:MM |
| `value_kwh` | OUI | Nombre |
| `meter_id` ou `PRM` | OUI | Code PRM existant |

### 4. Verdict effort total

| Scénario | Effort | Description |
|----------|--------|-------------|
| **A — Import CSV sans UI (pilote accompagné)** | **2-3 jours** | Template multi-feuille + resolver PRM + mapping synonymes factures + script CLI chaîné + doc |
| **B — Import CSV avec UI d'upload (pilote autonome)** | **5-8 jours** | Scénario A + UI unifiée 4 onglets + wizard factures + resolver interactif + rapport consolidé |
| **C — Import "zéro friction" complet** | **10-15 jours** | Scénario B + import contrats + connecteur Enedis API + parse PDF multi-fournisseur + onboarding interactif |

**Recommandation** : Le scénario A suffit pour un premier pilote accompagné. Le resolver PRM→site_id est le composant critique à implémenter en premier.

---

## Consolidation Finale

### Backlog complet — tous les findings P0 + P1

| # | Axe | Finding | Fichier:ligne | Sév. | Effort | Impact pilote |
|---|-----|---------|--------------|------|--------|---------------|
| 1 | A1 | Boutons "Modifier"/"Appliquer" planning noop | `MonitoringPage.jsx:1013,1017` | **P0** | S | Bloquant |
| 2 | A1 | Texte "Brique 1" visible dans l'UI prospect | `PurchaseAssistantPage.jsx:626` | **P0** | XS | Bloquant |
| 3 | A2 | purchase_seed.py non idempotent — doublons à chaque re-run | `purchase_seed.py:46-125` | **P0** | S | Bloquant |
| 4 | A2 | Prix réf 0.18 au lieu de 0.068 — écart x2.6 | `purchase_seed.py:70,140` | **P0** | XS | Bloquant |
| 5 | A3 | BACS : classe EN 15232 non évaluée dans scoring | `bacs_engine.py` | **P0** | M | Bloquant |
| 6 | A3 | Export OPERAT : gaz toujours à 0 dans CSV | `operat_export_service.py:78` | **P0** | S | Bloquant |
| 7 | A5 | Contrats.jsx : pas d'error state — skeleton infini | `Contrats.jsx` | **P0** | S | Bloquant |
| 8 | A5 | ActionPlan.jsx : loading primitif + pas de PageShell | `ActionPlan.jsx` | **P0** | S | Bloquant |
| 9 | A1 | Route /action-center sans Suspense + orpheline NavRegistry | `App.jsx:237` | P1 | S | Visible |
| 10 | A1 | Bouton "Compléter données contrat" — navigation morte | `ShadowBreakdownCard.jsx:263` | P1 | S | Visible |
| 11 | A1 | Texte "post-ARENH" dans PDF Pack RFP | `ExportPackRFP.jsx:164` | P1 | XS | Visible |
| 12 | A2 | Patrimoine.jsx recalcule conformité côté front | `Patrimoine.jsx:766` | P1 | XS | Visible |
| 13 | A2 | contract_risk_eur stubbé à 0 | `cockpit.py:217` | P1 | S | Visible |
| 14 | A3 | CEE P6 : aucun calcul kWhc cumac auto | `cee_p6.py:8-37` | P1 | L | Visible |
| 15 | A3 | APER : pas de preuves installation existante | `aper.py:9-109` | P1 | S | Visible |
| 16 | A3 | RegAssessment scoring mono-row — pas de granularité | `compliance_score_service.py:367-406` | P1 | S | Visible |
| 17 | A3 | DT regops ne calcule pas trajectoire | `tertiaire_operat.py:9-126` | P1 | S | Visible |
| 18 | A4 | Pas de bouton export CSV anomalies frontend | `BillIntelPage.jsx` | P1 | XS | Visible |
| 19 | A5 | CompliancePipeline : error = toast seul | `CompliancePipelinePage.jsx` | P1 | S | Visible |
| 20 | A5 | Double cockpit CommandCenter + Cockpit | `CommandCenter + Cockpit` | P1 | L | Visible |
| 21 | A5 | Cockpit 5+ useEffect sans batching — popcorn loading | `Cockpit.jsx` | P1 | M | Visible |
| 22 | A5 | Contrats.jsx : filtre sans empty state | `Contrats.jsx` | P1 | XS | Visible |

### Findings P2 (polish — 20+)

| Axe | Nb | Résumé |
|-----|----|--------|
| A1 | 8 | Dead code (Dashboard, ActionPlan, CompliancePage, EnergyCopilot, AnomalyActionModal, deprecated exports, unused imports) |
| A2 | 6 | Variable mal nommée, seed legacy non déterministe, 30x toFixed() sans guard, 87x toLocaleString manuels, calcul readiness dupliqué front, MarketWidget null crash |
| A3 | 4 | BACS cvc_alerts stub, DT delta_percent non standard, BACS YAML/code dupliqués, DT moteur partiel |
| A4 | 3 | Segments C2/C1/HTB absents, docstrings CTA erronées, seed TURPE 6 |
| A5 | 6 | Responsive ActionPlan, error states pages secondaires (3), taille fixe search, cockpit errors silent |

---

## Résumé Exécutif

| Métrique | Valeur |
|----------|--------|
| **Score global actuel** | **60/100** |
| **Findings P0 (bloquants pilote)** | **8** |
| **Findings P1 (visibles en démo)** | **14** |
| **Findings P2 (polish)** | **~27** |
| **Effort total fix P0** | **~5 jours** |
| **Effort total fix P0+P1** | **~15 jours** |
| **Effort ingestion données réelles (B1)** | **2-3j (accompagné) / 5-8j (autonome)** |
| **Score cible après fix P0+P1** | **80/100** |

### Scores par axe

| Axe | Score | Point fort | Point faible principal |
|-----|-------|-----------|----------------------|
| A1 — Structure & Navigation | 7/10 | 47 routes, registry propre | Boutons noop, label "Brique 1" |
| A2 — Données & Seed | 7/10 | Module Achat complet, SoT compliance | Seed legacy non idempotent, prix x2.6 |
| A3 — Moteurs Réglementaires | 6/10 | Seuils corrects, DJU fonctionnel | BACS EN 15232 absent, CEE stub, export gaz=0 |
| A4 — Shadow Billing | 8/10 | TURPE 7 complet, 34 règles, accises versionnées | Bouton export CSV absent |
| A5 — UX & Parcours Démo | 7/10 | Pages critiques bien couvertes | Error states pages secondaires, double cockpit |
| A6 — Ingestion Données Réelles | 7/10 | Pipeline staging mature, 150 synonymes | Resolver PRM→site_id manquant, UI non unifiée |

### Verdict pilote-ready : CONDITIONNEL

**Conditions pour passer pilote-ready :**

1. **Fix les 8 P0** (~5 jours) :
   - Boutons noop MonitoringPage → masquer ou toast
   - Label "Brique 1" → "votre patrimoine"
   - purchase_seed.py → INSERT OR IGNORE + prix 0.068
   - BACS EN 15232 → ajouter vérification classe B minimum
   - Export OPERAT gaz → distinguer electricite/gaz dans `_get_site_conso`
   - Contrats.jsx → ajouter ErrorState
   - ActionPlan.jsx → SkeletonCard + ErrorState + PageShell

2. **Fix les P1 haute visibilité** (~3 jours) :
   - Navigation morte ShadowBreakdownCard (#10)
   - Recalcul front Patrimoine (#12)
   - Bouton export CSV anomalies (#18)
   - CompliancePipeline error state (#19)
   - Filtre Contrats empty state (#22)

3. **Resolver PRM→site_id** (~1 jour) :
   - Bloqueur n°1 pour le pilote données réelles

**Total minimum pour pilote : ~9 jours**

---

*Généré le 2026-04-05 par Claude Code (Opus 4.6) — 6 axes, 49 findings, 103+ fichiers analysés*
