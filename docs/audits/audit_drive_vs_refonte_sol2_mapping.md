# Audit mapping Drive ↔ refonte-sol2 — gaps par verbe cardinal PROMEOS

> **Mission** : pour chaque verbe cardinal de la doctrine v1.3 (Centraliser, Fiabiliser, Comparer, Auditer, Piloter), identifier les fonctionnalités attendues côté Drive, l'état réel du code sur `claude/refonte-sol2`, et le gap restant.
> **Date** : 2026-05-23 · **Mode** : READ-ONLY strict, aucune modification de code.
> **HEAD audité** : commit `ade3d0a0` (worktree dédié `.claude/worktrees/audit-mapping-sol2/`).
> **Sources** : 5 sous-agents Explore parallèles (TURPE 7+SGE, BACS+Tertiaire+APER, NEBCO+Flex, veille hebdos fév-mai 2026, multi-énergie+KPI+Centre d'Action) + cross-checks `rg` directs + 6 audits Drive précédents (`audit_docs_drive_promeos_sans_acc.md` + READ-ONLY scope sans ACC).
> **Doctrine source** : `project_promeos_vision_consolidee_v1_3_2026_05_08.md` + 5 verbes (Centraliser · Fiabiliser · Comparer · Auditer · Piloter).
> **Périmètre exclu court terme** : ACC, PMO, clé de répartition, settlement local (cf. `audit_readonly_promeos_scope_sans_acc_usage_steering.md`) · **chaleur réseau urbain** (Cofely, Citelec, Engie Solutions — reporté Mois 6+, traité comme post-MVP au même titre que vapeur process) · CBAM / CSRD côté Centraliser (reporté), thermostat pièce par pièce 2027.

## Légende verdicts

| Symbole | Sens |
|---|---|
| ✅ | Présent + à jour |
| 🟢 | Présent, à jour à confirmer en source-guard |
| 🟡 | Partiel — structure présente mais données ou logique incomplètes |
| ⚠️ | Présent mais incohérence ou dette identifiée |
| ❌ | Absent du code |
| 🔵 | Hors scope court terme (Mois 6+) |

---

## 1. CENTRALISER — « réunir factures, contrats, conformité, consommation d'un parc dispersé dans une seule tour de contrôle »

### 1.1 Centralisation des consommations

| Fonctionnalité attendue (Drive) | Code attendu | File:line | Verdict |
|---|---|---|---|
| Ingestion Enedis Data Connect (élec, P par 1/2 h) | `enedis.py` + `dataconnect_route.py` | `backend/routes/enedis.py` (29 LoC) + `backend/routes/dataconnect_route.py` (stub OAuth2/PKCE) | 🟡 — légacy XML R4X/R50/R151 OK, **APIs SGE V25→V26.2 + CleFIDO2 absents** |
| Ingestion GRDF ADICT (gaz, OAuth2, 5 req/s) | `connectors/grdf_adict.py` + `services/grdf_pcs_service.py` | `backend/services/grdf_pcs_service.py` (~60 LoC) + `backend/routes/grdf_route.py` (7 LoC) | ✅ + IDOR fix Phase C-7 (CWE-639 validation PCE ↔ org) |
| PCS gaz régional (R17 effectif 1/2/2026 — 11,2 kWh/m³ Sud, etc.) | `grdf_pcs_service.py:m3_to_kwh()` | `backend/services/grdf_pcs_service.py` | ✅ 14 régions + fallback 11,2 |
| Connecteur réseau de chaleur urbain (Cofely, Citelec, Engie Solutions) | `heat_network_invoicing_service.py` | `backend/schemas/contract_perimeter.py` seul hit (enum) | 🔵 **Hors scope court terme** — reporté Mois 6+. `EnergyVector.HEAT` enuméré mais pas de parser facture fournisseur attendu en MVP. |
| Connecteur vapeur process industriel | `steam_process_service.py` | — | 🔵 Hors scope court terme (industrie lourde, Mois 6+) |
| SoT consommation multi-source (metered / billed / reconciled) | `consumption_unified_service.py` | `backend/services/consumption_unified_service.py:46-396` | ✅ Couverture 80 % threshold, source_used + confidence documentés |
| DJU correction climatique (élec chauffage + clim + gaz) | `weather_dju_service.py` + `gas_weather_service.py` | `backend/services/weather_dju_service.py` + `backend/services/gas_weather_service.py` | ✅ DJU18 COSTIC via Open-Meteo Archive API, fallback saisonnier sinusoïdal |

### 1.2 Centralisation des factures

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Parser facture PDF élec (TURPE 7, CG/CC/CS/CMDPS/CER/CACS/CR/CT/CACNC) | `billing_canonical_service.py` + `billing_normalization.py` | `backend/services/billing_canonical_service.py` (200+) + `billing_normalization.py` (150+) | 🟡 Composantes principales OK, **CACNC absent** (bimestriel BT≤36), **CER pas codifié en facturation** (HTA seul) |
| Parser facture PDF gaz (ATRD7, ATRT8, CTA, accise, TVA) | `billing_normalization.py` | `backend/services/billing_normalization.py` + `tarifs_reglementaires.yaml` | ✅ ATRD7 +6,06 % 1/7/2025, ATRT8 +3,41 % 1/4/2026, CTA gaz 20,80 % stable, accise gaz 10,73 €/MWh |
| Parser facture chaleur réseau | parseur dédié | — | 🔵 Hors scope court terme (Mois 6+) |
| Format e-facture obligatoire 1/9/2026 (Factur-X / UBL / CII) | module e-facture | — | ❌ **P0** — `FRN_20260123 Atelier RéformeFacturationElectronique` Drive non implémenté |
| Importer batch idempotent (CSV + dedup hash) | `billing.py` + `BillingImportBatch` model | `backend/routes/billing.py:150+` + `backend/models/billing_models.py` | ✅ + tests dédiés |
| Réconciliation semi-auto | `billing_reconcile.py` + `reconciliation_service.py` | `backend/services/billing_reconcile.py` (120+) + `backend/services/reconciliation_service.py` (100+) | ✅ |

### 1.3 Centralisation des contrats

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| ContratCadre + ContractV2 (cadre + annexe) | `models/contract_v2_models.py` + `services/contract_v2.py` | `backend/models/contract_v2_models.py` + `backend/services/contract_v2.py` (140+) | ✅ ADR architecture v1.3 (D5 patrimoine v1) |
| ContractDeliveryPoint N:N (PDL ↔ contrat) | `models/contract_v2_models.py` (relation N:N) | — | 🟢 doctrine D5 actée 03/05, à vérifier en seed |
| Cohérence contrat ↔ patrimoine | `contrat_coherence.py` | `backend/services/contrat_coherence.py` (60+) | ✅ |
| Risque contrat (réajustement / pénalité) | `contract_risk_service.py` | `backend/services/contract_risk_service.py` (100+) | ✅ |
| Alertes fin contrat | `contract_expiration_alerts.py` + `contracts_radar.py` | `backend/services/contract_expiration_alerts.py` + `backend/routes/contracts_radar.py` | ✅ |
| Parser PDF contrat (extraction automatique) | nouveau parser | `backend/routes/contracts_parse.py` (2 LoC stub) | ❌ **P0** — sprint P0 repo pitch-ready, doctrine v1.3 |
| Entité Fournisseur (premier rang) | `models/fournisseur.py` + `routes/fournisseurs.py` | présent | ✅ Sprint P0 livré |

### 1.4 Centralisation de la conformité

| Fonctionnalité attendue (5 piliers) | Code attendu | File:line | Verdict |
|---|---|---|---|
| Décret Tertiaire (cibles -40/-50/-60 %, 30/09 annuel, historisation 5 ans, mutualisation intra-EJ) | `services/tertiaire_*` + `doctrine/constants.py` | `backend/doctrine/constants.py:111` (DT_MILESTONES) · `OPERAT_DECLARATION_DEADLINE_MONTH_DAY="09-30"` · `tertiaire_mutualisation_service.py` · `tertiaire_modulation_service.py` | ✅ — sanction 7500 € + name & shame présents |
| OPERAT (export ADEME, valeurs absolues 426 sous-catégories Annexe I) | `operat_export_service.py` + `config/operat_valeurs_absolues.yaml` | `backend/services/operat_export_service.py` (100+) + `backend/config/operat_valeurs_absolues.yaml` (zones climatiques L2) | ✅ structure complète + zone climatique |
| BACS (290 kW 2025 → 70 kW 2030, classes A/B/C/D ISO 52120-1:2022, TRI `S/(ΣG×C)`, 4 fonctions min, inspection 5 ans / 2 ans après install) | `bacs_regulatory_engine.py` + `bacs_alerts.py` + `bacs_ops_monitor.py` + `cascade_bacs_service.py` | `backend/services/bacs_regulatory_engine.py` (170 LoC) · `backend/doctrine/constants.py:140-158` (seuils, deadlines) | ✅ — alignement EPBD recast (décret 2025-1343 commenté) + articles CCH R.175-1 à R.175-5-1 référencés |
| APER (parking ≥ 10k m² avant 01/07/2026 — 40k €/an · 1500-10k m² avant 01/07/2028 — 20k €/an) | `aper_service.py` + `doctrine/constants.py` | `backend/doctrine/constants.py:248-277` (seuils + pénalité 20 €/m²/an) + `backend/services/aper_service.py` (~100 LoC) | ✅ — **deadline imminente < 6 semaines, alerte cockpit à vérifier** |
| Audit SMÉ (seuils 2,75 / 23,6 GWh, périodicité 4 ans, 1er audit 11/10/2026) | `audit_sme_service.py` + `doctrine/constants.py:308-317` | `backend/services/audit_sme_service.py` (150 LoC) | ✅ deadline imminente |
| BEGES (seuil 500 metropole / 250 DOM, périodicité 3 ans Décret 2022-982) | `regulatory/rules/beges.py` + constants | `backend/doctrine/constants.py:332-340` | ✅ |
| CSRD post-Omnibus (ordonnance 2023-1142, scope 1+2 GHG, taxonomie UE, audit OTI) | `regulatory/rules/csrd.py` | — | ❌ **P0** — non implémenté, blocage grandes entreprises 250+ salariés |
| EPBD 2024 + thermostat pièce par pièce 2027 | service zone × consigne | `regs.yaml:43-50` (DPE tertiaire 2026 OK) | ❌ **P1** — thermostat pièce par pièce 2027 absent |

### 1.5 Tour de contrôle (cockpit, briefing, synthèse)

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Cockpit stratégique CFO 3 min | `CockpitStrategique.jsx` + `routes/cockpit_strategique.py` | `frontend/src/pages/CockpitStrategique.jsx` + `backend/routes/cockpit_strategique.py` (5 LoC) | ✅ |
| Briefing du jour EM 30 s | `CockpitJour.jsx` | présent | ✅ |
| Anomalies hub canonique 4 piliers | `AnomaliesPage.jsx` (`/anomalies`) | `frontend/src/pages/AnomaliesPage.jsx` (835 LoC) | ✅ — repoint 2026-05-02 |
| KPI agrégés (annual_consumption_mwh, energy_cost_eur, compliance_score, etc.) | `doctrine/kpi_registry.py` (11 KPI) | `backend/doctrine/kpi_registry.py:36-170` | ✅ + ⚠️ 2 KPI multi-énergie manquants (gaz, chaleur) |
| Vue portfolio multi-sites | `portfolio_*` services | `backend/services/portfolio_intensity_service.py`, `patrimoine_portfolio_cache.py` | ✅ |

### Synthèse Centraliser

| Item | Verdict | Priorité |
|---|---|---|
| Élec (Enedis legacy XML) | 🟡 | P0 — migrer R6X JSON + CleFIDO2 |
| Gaz (GRDF ADICT) | ✅ | — |
| Chaleur réseau urbain | 🔵 | Hors scope court terme (Mois 6+) |
| Vapeur process | 🔵 | Hors scope court terme (Mois 6+) |
| Factures e-facture 1/9/2026 | ❌ | **P0** |
| Parser PDF contrat | ❌ | **P0** (sprint repo pitch-ready) |
| CSRD post-Omnibus | ❌ | **P0** (transposition ordonnance 2023-1142) |
| Thermostat pièce par pièce 2027 | ❌ | **P1** |
| Centre d'action / cockpit | ✅ | — |

---

## 2. FIABILISER — « nettoyer, normaliser, recouper les données ; signaler ce qui n'est pas fiable plutôt que de l'afficher faussement »

### 2.1 Normalisation des données

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Normalisation factures (mapping ligne → composante TURPE/CTA/accise/TVA) | `billing_normalization.py` + `price_decomposition_service.py` | `backend/services/billing_normalization.py` (150+) + `backend/services/price_decomposition_service.py` (90+) | ✅ |
| Décomposition prix (TURPE / CSPE / accise / VNU / TVA) | `price_decomposition_service.py` | présent | 🟡 — **VNU dormant** correctement (prix marché < seuil 78 €/MWh) mais à confirmer en source-guard |
| Granularité consommation (D/H/M/A) | `consumption_granularity_service.py` | `backend/services/consumption_granularity_service.py` (100+) | ✅ |
| Baseline + normalisation DJU | `baseline_service.py` (méthode B IPMVP-compatible : `E = a×DJU + b` + r²) | `backend/services/baseline_service.py:200-299` | ✅ |
| Parser R6X JSON (R64A/R64B mesures indexées, R63A/R63B puissance, R66B P max) | `data_ingestion/enedis/parsers/r6x.py` | seul `r4x.py` legacy XML | ❌ **P0** — migration urgente post 1/1/2027, nouveau format SGE V26.x |
| Authentification CleFIDO2 (MFA FIDO2 + GARDIAN) | `dataconnect_route.py` | `backend/routes/dataconnect_route.py` (stub PKCE seul) | ❌ **P0** — bloque accès Enedis prod |
| PCS gaz canonique post-R17 (0,238 ou régional) | `grdf_pcs_service.py` | `backend/services/grdf_pcs_service.py` | ✅ |

### 2.2 Recoupement et qualité

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Recoupement metered vs billed (delta 10 %) | `consumption_unified_service.py:reconcile_metered_billed()` | `backend/services/consumption_unified_service.py:309-396` | ✅ |
| Data quality score (% complétude par compteur) | `data_completeness_service.py` (référencé KPI registry) | référencé `kpi_registry.py` ligne `data_quality_score` | 🟢 |
| Confidence levels par source de conso | `consumption_unified_service.py` (`source_used`, `confidence`) | présent | ✅ |
| Coverage % par source | présent | ✅ |
| Climat correction DJU ADEME v2025+ | `regops/operat_zones.py` | présent | 🟡 — structure présente, version v2025 à confirmer |
| Détection capteur GTB silencieux (> 6 h) | `event_bus/detectors/data_quality_issue_detector.py` | présent | ✅ |
| Anomalies patrimoine (manquant / incohérent) | `patrimoine_anomalies.py` + `perimeter_check.py` | présent | ✅ |

### 2.3 Signalisation (vs falsification)

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| KPI registry strict (unit / formula / source / scope / period / freshness / confidence_rule / owner) | `doctrine/kpi_registry.py` + `kpi_tracability.py` | `backend/doctrine/kpi_registry.py:36-170` (11 KPI) + `kpi_tracability.py` | ✅ — 11 KPI canoniques, **2 unit issues** (`open_actions_count` et `billing_anomalies_count` typés `days` au lieu de `count`) |
| Test source-guard format KPI | `tests/doctrine/test_kpi_registry_format.py` | présent (référencé doctrine) | 🟢 à confirmer |
| Mirror frontend `kpiRegistry.js` + source-guard FE | `frontend/src/doctrine/kpiRegistry.js` | — | ❌ **P1** — absent, KPI affichés sans pointer vers id du registre |
| Affichage « donnée non fiable » UI (vs masquer) | composant Sol `KpiTile.confidence` | `frontend/src/ui/sol/KpiTile.jsx` (à vérifier) | 🟢 |
| Org-scoping 4 lignes de défense (IS11 ADR-027) | middleware + `resolve_org_id()` + repo + 57 source-guards | `backend/services/auth_guards.py` + matrice 288 cellules | ✅ — 95 % couvert, **5 routers à re-vérifier** (`bill_intelligence`, `kb_usages`, `onboarding`, `market_intelligence`, `public_diagnostic`) |
| MIME validation libmagic + whitelist + double-check signatures (Evidence ADR-029 IE9) | `Evidence` model | présent | ✅ |
| Rétention RGPD 5 ans (obligation DT) | `Evidence.retention_policy` | présent | 🟢 |

### 2.4 Traçabilité réglementaire (NOR + date + URL)

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Citations NOR + JORF sur DT / BACS / APER / OPERAT | `config/sources_reglementaires.yaml` + `config/acronymes_doctrine.yaml` | présent (470+ lignes audit trail) | ✅ |
| Articles CCH R.175-1 à R.175-5-1 (BACS) | référencés engine | `backend/services/bacs_regulatory_engine.py` (R175-3 ligne 142, R175-7, R175-12) | ✅ |
| Délibérations CRE pour NEBCO / capacité / TURPE | `config/cre_nebco_sources.yaml` | — | ❌ **P1** — `flex_nebco_service.py` opérationnel mais résolutions CRE non hardcodées |

### Synthèse Fiabiliser

| Item | Verdict | Priorité |
|---|---|---|
| Normalisation factures TURPE/CTA/accise | 🟡 (CACNC + CER manquants) | **P0** |
| Parser R6X JSON | ❌ | **P0** |
| Auth CleFIDO2 | ❌ | **P0** |
| KPI registry backend | ✅ + 2 unit issues | P1 fix unit issues |
| KPI registry frontend mirror | ❌ | **P1** |
| Org-scoping 5 routers | 🟡 | **P0** |
| Citations CRE NEBCO | ❌ | **P1** |
| Recoupement metered/billed | ✅ | — |
| DJU climat correction v2025 | 🟡 | P1 |

---

## 3. COMPARER — « benchmarks ADEME/OID par archétype, site vs site, fournisseur vs fournisseur, shadow billing vs facture réelle »

### 3.1 Benchmarks ADEME / OID par archétype NAF

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Résolution NAF canonique | `utils/naf_resolver.py:resolve_naf_code()` | `backend/utils/naf_resolver.py` (150 LoC) | ✅ SoT |
| Mapping NAF → typologie (11 classes) | `doctrine/naf_to_typology.py` | `backend/doctrine/naf_to_typology.py` (BUREAUX, COMMERCE, RESTAURATION, SANTE, ENSEIGNEMENT, LOGEMENT, HOTEL, INDUSTRIE_LEGERE, INDUSTRIE_LOURDE, AGRICULTURE, AUTRE) | ✅ |
| Benchmarks OID par archétype (kWh/m²/an, IPE) | `services/enedis_benchmarks.py` + `pilotage/*` | `backend/services/enedis_benchmarks.py` (100+) · `backend/services/pilotage/portefeuille_scoring.py` · `pilotage/usage_detector.py` | ✅ — sources réelles présentes |
| Valeurs absolues OPERAT par catégorie (426 sous-catégories Annexe I, climat-zone) | `config/operat_valeurs_absolues.yaml` | présent | ✅ |
| Comparaison site vs site | `cockpit_facts_service.py` + `portfolio_intensity_service.py` | présent | ✅ |
| Archétype industrie lourde process (vapeur, air comprimé) | archetype dédié | — | 🔵 P2 (Griffine Nucourt cas d'usage) |

### 3.2 Comparateur fournisseur vs fournisseur

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Pricing offres (fixe / indexé / spot / TRVE) | `offer_pricing_v1.py` + `market_tariff_loader.py` | `backend/services/offer_pricing_v1.py` (60+) + `backend/services/market_tariff_loader.py` (80+) | ✅ |
| Comparateur multi-FTA TURPE 7 (CU / MU / LU / CU4 / MU4 / MUDT) | `purchase_strategy.py` + UI tab achat | `backend/routes/purchase_strategy.py` + `frontend/src/pages/PurchasePage.jsx` | 🟡 — base présente, ranking FTA optimal à finaliser |
| Comparateur TURPE 6 vs TURPE 7 sur 12 mois historique | nouveau simulateur | — | ❌ **P1** — fenêtre changement FTA sans pénalité jusqu'au 31/01/2026 manquée si non livré |
| 8 modèles LUCIOLE flex (HP/HC, Tempo, bloc+SPOT, primo-agrégateur, etc.) | `archetype_recommendation.py` | présent | 🟡 — primo-agrégateur statut #8 non discriminé |
| Décision "Quel modèle ?" guidée UX | assistant FE | — | ❌ **P1** |

### 3.3 Shadow billing vs facture réelle

| Composante TURPE 7 | Code attendu | File:line | Verdict |
|---|---|---|---|
| CG Gestion (CARD vs Contrat Unique, par segment HTA / BT>36 / BT≤36) | `tarifs_reglementaires.yaml` + `billing_shadow_v2.py` | présent | ✅ |
| CC Comptage (mensuel / bimestriel) | idem | présent | ✅ |
| CS Soutirage HTA (5 plages, `b₁×P₁ + Σ bᵢ(Pᵢ−Pᵢ₋₁) + Σ cᵢ×Eᵢ`) | `billing_engine/catalog.py` | `backend/services/billing_engine/catalog.py:40-200` | 🟡 — C4 HPH/HCH/HPB/HCB OK, **HTA 5 FTA + PP1 RTE incomplet** |
| CS Soutirage BT > 36 (4 plages) | idem | `billing_engine/catalog.py:67-180` | ✅ |
| CS Soutirage BT ≤ 36 (5 tarifs : CU4 / MU4 / LU / CU / MUDT) | idem | `tarifs_reglementaires.yaml:100-102` + `billing_shadow_v2.py:100-120` | 🟡 — moyennes seulement, **5 grilles détaillées absentes** |
| CMDPS HTA (`Σ 0,04 × bᵢ × √Σ(ΔP²)` mesure 10 min) | idem | présent | 🟡 — formule HTA à compléter |
| CMDPS BT > 36 (`12,41 × h`) | idem | présent | ✅ |
| CER énergie réactive HTA (tg φ > 0,40 → 2,44 c€/kVAr·h) | logique facturation CER | `data_staging/models.py` (réactif ingestée) | ❌ **P0** — champs ingérés mais aucune logique de facturation CER |
| CER BT > 36 = 0 (supprimée 1/8/2025) | source-guard CER BT > 36 == 0 | — | ❌ **P0** — pas de garde-fou |
| CACNC bimestriel BT ≤ 36 (socle 6,48 € + majoration 4,14 € si > 12 mois) | constants + détection Linky | — | ❌ **P0** — composante entière absente du catalog |
| CACS Alim. complémentaire / secours | `tarifs_reglementaires.yaml` | présent | ✅ |
| Pointe mobile PP1 RTE (10–15 j/an, plages 7h-15h / 18h-20h) | hook RTE | `billing_engine/turpe_calendar.py:236` mention | 🟡 — calendrier statique, **boucle RTE PP1 absente** |
| Date pivot TURPE 7 = 1/8/2025 (avec mouvement exceptionnel 1/2/2025 +7,7 %) | `tarifs_reglementaires.yaml:96` | `valid_from: 2025-02-01` documenté Tier 1 P0.1 | ✅ |
| TVA 20 % uniforme 1/8/2025 (suppression 5,5 % abonnement/CTA/TURPE fixe) | test + constants | `tests/test_shadow_billing_gas.py:34-37` | ✅ |
| HC C1-C4 nouvelles plages 2026-2030 (`20260417 Rapport concertation HC C1-C4`) | scénario tarifaire 2027-2028 | — | ❌ **P1** — TURPE 7 HC daytime 2027-2028 non modélisé |

### Synthèse Comparer

| Item | Verdict | Priorité |
|---|---|---|
| Benchmarks OID NAF | ✅ | — |
| Site vs site | ✅ | — |
| Fournisseur vs fournisseur | 🟡 | P1 |
| Comparateur multi-FTA TURPE | 🟡 | **P1** (fenêtre 31/01/2026) |
| Shadow billing TURPE 7 — CG/CC/CS principaux | ✅ | — |
| Shadow billing — CER HTA | ❌ | **P0** |
| Shadow billing — CACNC BT ≤ 36 | ❌ | **P0** |
| Shadow billing — C5 grilles détaillées | 🟡 | **P0** |
| Shadow billing — Pointe mobile PP1 | 🟡 | **P1** |
| Shadow billing — HC daytime 2027-2028 | ❌ | **P1** |
| 8 modèles flex LUCIOLE | 🟡 | **P1** (primo-agrégateur) |

---

## 4. AUDITER — « détecter anomalies de facture, dérives de consommation, écarts réglementaires ; remonter à la source et à la formule »

### 4.1 Anomalies factures (Bill Intelligence)

| Anomalie attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| Surfacturation CG / CC | `bill_intelligence/anomaly_detector.py` règle R5+ | `backend/services/bill_intelligence/anomaly_detector.py` | ✅ règles existantes |
| Mauvais segment tarifaire (Psouscrite > 36 kVA en BT ≤ 36) | règle dédiée | — | ❌ **P1** — non détectée |
| CMDPS abusif (> 30 % facture ET > 25× ΔP non souscrit) | règle dédiée | — | ❌ **P1** |
| CER non facturé HTA (Qréactive > seuil ET CER = 0) | règle dédiée | — | ❌ **P1** (et bloqué par P0 §3.3 absence facturation CER) |
| CER facturé BT > 36 post 1/8/2025 (= anomalie) | règle dédiée | — | ❌ **P1** |
| CACNC persistant (BT ≤ 36 sans Linky après 2026) | règle dédiée | — | ❌ **P1** (et bloqué par P0 §3.3) |
| Mauvaise version tarifaire (coût alternatif < 0,95 × coût observé) | comparateur multi-FTA | — | ❌ **P1** |
| Surdimensionnement Psouscrite (Pmax < 0,7 × Psouscrite stable 6 mois) | règle dédiée | présent ? `bill_intelligence` | 🟢 à confirmer |
| ATRD7 / ATRT8 gaz incohérent | règle dédiée gaz | `backend/services/bill_intelligence/` (B14-B17 doctrine v1.4) | 🟢 |
| Anomalies factures multi-énergie (cohérence facture vs GTB théorique) | règle dédiée | — | ❌ **P1** |
| Phase L17 dead code découvert : pipeline détection 13 règles R19→R31 non appelée en production | `detect_anomalies_for_invoice` callsite | aucun callsite routes/services trouvé (mémoire L17) | ⚠️ **P0 cardinal** — pipeline wiring à confirmer (cf. `project_phase_L17_pipeline_dead_code_discovery_2026_05_09.md`) |
| Réclamation CMDPS / récupération CER (action générée Centre d'Action) | `purchase_actions_engine.py` | présent | 🟢 |

### 4.2 Dérives consommation (pilotage advisory)

| Détecteur attendu | Code attendu | File:line | Verdict |
|---|---|---|---|
| Talon nocturne (P par 1/2 h 22h–05h > 15 % conso) | `consumption_diagnostic.py:_actions_base_load()` (Q10 vs median) | `backend/services/consumption_diagnostic.py:120-140` | ✅ |
| Dérive WE (ConsoWE / ConsoJourOuvré > seuil) | `event_bus/detectors/consumption_drift_detector.py` | présent | ✅ — détecteur backend, **widget FE manquant** (cf. audit Sol2 §8) |
| Surpuissance (dépassement P souscrite) | `routes/power.py` + détecteurs | présent | ✅ |
| HP coûteuses (HPH/HCH disproportionnée vs HC) | `tariff_periods_service.py` + `tou_service.py` | présent | ✅ |
| Conso déplaçable | `schedule_detection_service.py` + `flex_nebco_service.py` | présent | ✅ |
| Signature énergétique (régression `E = a×DJU + b`, r²) | `baseline_service.py` méthode B IPMVP | `backend/services/baseline_service.py:200-299` | ✅ |
| Drift saisonnier (ConsoHiverN vs N-1 après DJU correction) | `consumption_diagnostic.py:_linear_slope()` | présent | ✅ |
| Incohérence météo-chauffage (r(DJU, ConsoChauffage) < 0,70) | dans signature | présent | ✅ |
| Carpet plot 24 h × N jours palette septile | `CarpetPlot.jsx` (228 LoC) | `frontend/src/components/CarpetPlot.jsx` | ✅ — différenciant marché, à promouvoir (audit Sol2 P2-1) |
| CUSUM cumul résiduel ±3σ ISO 50001 explicite | `cusum_service.py` | linear slope seul | ❌ **P2** — différenciant ISO 50001 |
| IPMVP options B/C/D formel (M&V ISO 14064-2) | `baseline_service.py` étendu | méthode B simple | ❌ **P2** — bloquant clients audités CSRD |
| Décomposition 6-sources base load (CVC veille / pompes / HVAC min / éclairage / IT / pertes) | `base_load_decomposition_service.py` (heuristiques NAF) | — | ❌ **P1** — méthodologie Endesa Griffine 13 étapes (1/13 manquante) |

### 4.3 Écarts réglementaires (Conformité)

| Écart attendu | Code attendu | File:line | Verdict |
|---|---|---|---|
| Trajectoire DT (-40/-50/-60 % vs année référence) | `tertiaire_modulation_service.py` + `dt_progress_service.py` | présent | ✅ |
| Score conformité pondéré (DT × BACS × APER × AUDIT) | `regops/scoring.py` | `backend/regops/scoring.py` (300+ LoC, SoT) | ✅ |
| Solarization gap APER (m² manquante, ROI ombrières) | `aper_service.py` | présent | 🟡 — formule présente, alerte cockpit deadline 01/07/2026 à vérifier |
| Étude TRI BACS (formule officielle `S/(ΣG×C)`) | `bacs_engine.py:tri_exemption()` | présent | ✅ |
| Exemption < 5 % conso (BACS) | logique dédiée | — | ❌ **P1** — BAT-TH-116 fiche CEE non implémentée |
| Modulation Tertiaire (dossier technique avant 30/09/2026) | `tertiaire_modulation_service.py` | présent | 🟡 |
| Audit SMÉ workflow (transmission 2 mois, périodicité 4 ans) | `audit_sme_service.py` | présent | ✅ |
| BEGES 3 ans Décret 2022-982 | `regulatory/rules/beges.py` | présent | ✅ |
| CSRD scope 1+2+3 GHG + taxonomie UE + audit OTI | `regulatory/rules/csrd.py` | — | ❌ **P0** (cf. §1.4) |

### 4.4 Traçabilité (remonter à la source et à la formule)

| Item | Verdict | Détail |
|---|---|---|
| NOR + JORF dans configs YAML | ✅ | `sources_reglementaires.yaml` (470+ lignes), `acronymes_doctrine.yaml`, `operat_valeurs_absolues.yaml` |
| Articles CCH R.175-1 à R.175-5-1 (BACS) | ✅ | `bacs_regulatory_engine.py:142` (R175-3, R175-7, R175-12) |
| Décret 2019-771 (DT) | ✅ | référencé `operat_zones.py`, `regs.yaml` |
| Loi APER 2023-175 + Décret 2024-1023 | ✅ | `doctrine/constants.py:260-275` |
| TURPE 7 délibération CRE 2025-78 | ✅ | `tarifs_reglementaires.yaml` + doc string `purchase_cost_simulation.py` |
| CRE résolutions NEBCO / AOFD | ❌ | **P1** — résolutions non hardcodées |
| Citations infraction UE CEE biométhane (29/04/2026) | ❌ | **P1** — hebdo détectée, pas tracée code |
| Evidence : NOR + date + URL JORF rattachés à chaque action | ✅ | `Evidence` model + `ActionEvent.type=EVIDENCE_ADDED` + 16 event_types ADR-029 |

### Synthèse Auditer

| Item | Verdict | Priorité |
|---|---|---|
| Anomalies factures pipeline wiring (Phase L17) | ⚠️ | **P0 cardinal** |
| Anomalies TURPE 7 (segment / CMDPS / CER / CACNC / FTA / Psous) | ❌ | **P0** (5 règles + bloqué par §3.3) |
| Dérives conso (talon / drift WE / signature / drift saisonnier) | ✅ | — (sauf widget FE drift WE manquant) |
| CUSUM + M&V IPMVP | ❌ | P2 (différenciation) |
| Décomposition 6-sources base load | ❌ | **P1** (Griffine 1/13 manquante) |
| Trajectoire DT + score conformité | ✅ | — |
| CSRD | ❌ | **P0** |
| Traçabilité NOR | ✅ — sauf CRE NEBCO | **P1** |

---

## 5. PILOTER — « pousser au bon moment l'action prioritaire, le scénario chiffré, l'échéance, la fenêtre marché »

### 5.1 Action prioritaire (Centre d'Action)

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| 4 briques alimentent (Compliance / Consumption / Billing / Purchase) | `action_hub_service.build_actions_from_*` | `backend/services/action_hub_service.py:84-263` | ✅ |
| Brique FLEX → Centre d'Action | `build_actions_from_flex()` | — | ❌ **P1** — `flex_opportunity_detector.py` existe mais pas câblé action_hub |
| Brique EMS → Centre d'Action | `build_actions_from_ems()` | — | ❌ **P1** |
| Brique PATRIMOINE (APER ombrières, BACS exemption) → Centre d'Action | `build_actions_from_patrimoine()` | indirect via `patrimoine_impact.py` + `patrimoine_conformite_sync.py` | 🟡 — à formaliser |
| Lifecycle 5 états (OPEN → IN_PROGRESS → ON_HOLD → DONE → CLOSED) | `ActionItem.status` + state machine ADR-028 | présent | ✅ |
| 6 closure_reasons (`merged_duplicate`, `resolved_via_recurrence` etc.) | enum + guards IL5 Q9-B | présent | ✅ |
| Auto-fermeture (source résolue) | `action_hub_service.py:377-398` | présent | ✅ |
| Per-source caps (max actions par brique) | `_capped()` ligne 293 | présent | ✅ |
| Guards IL4 (expired interdit P0/P1) + IL5 (merged_duplicate ≠ resolved) + IL7 (auto-close P0/P1 → preuve) | présent ADR-028 | présent | ✅ |
| Dedup key `(org_id, source_type, source_id, source_key)` | UQ constraint | `models/action_item.py` | ✅ |

### 5.2 Scénario chiffré (impact)

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| `gain_kwh` / `gain_eur` / `co2_avoided_kg` calculés **backend** | `impact_decision_service.py` + `routes/actions.py:_resolve_co2e_kg` | `backend/services/impact_decision_service.py` (100+) | ✅ |
| `realized_gain_eur` + `realized_at` (M&V suivi gains réels) | `models/action_item.py:115` | présent | ✅ |
| Computation priority (severity / gain / deadline) | `action_hub_service.compute_priority()` | `backend/services/action_hub_service.py:57` | ✅ |
| KPI `leviers_mwh_year` (CEE BAT-TH-* par archétype) | `cockpit_facts_service._build_potential_recoverable` + `analytics_engine` | présent | ✅ |
| KPI `trajectory_dt_projection` (3-phase learning ratio) | `routes/cockpit.py:_project_with_action_echeances` | présent | ✅ |
| Calculs CO₂ : Règle d'or zero business logic FE | hook backend uniquement | 7+ violations FE `kwh * useElecCo2Factor()` détectées | ⚠️ **P0** — cf. audit Sol2 P0-3 |
| Calcul tarif unitaire `€/kWh` côté FE | proxy backend | `BillIntelPage.jsx:1322` violation | ⚠️ **P0** — cf. audit Sol2 P0-4 |
| Agrégation risque/coût côté FE | endpoints `/api/.../summary` | `AnomaliesPage.jsx:244-266` + `Cockpit.jsx:307` + `CockpitPilotage.jsx:119` violations | ⚠️ **P0** — cf. audit Sol2 P0-5 |

### 5.3 Échéance

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| `due_date` sur ActionItem | présent | `models/action_item.py` | ✅ |
| Calendrier réglementaire 2026-2050 (`.claude/skills/regulatory_calendar/`) | skill canonique | présent | ✅ |
| Deadline OPERAT 30/09 annuel | `OPERAT_DECLARATION_DEADLINE_MONTH_DAY` | `doctrine/constants.py:179` | ✅ |
| Deadline BACS 01/01/2025 + 01/01/2030 | `doctrine/constants.py:140-158` | présent | ✅ |
| Deadline APER 01/07/2026 + 01/07/2028 | `doctrine/constants.py:260-262` | présent | ✅ — **deadline imminente < 6 semaines** |
| Deadline Audit SMÉ 11/10/2026 | `doctrine/constants.py:317` | présent | ✅ — deadline imminente |
| Deadline e-facture 01/09/2026 | constants | — | ❌ **P0** |
| Deadline capacité RTE centralisée 01/11/2026 | constants + `market_tariffs_2026.yaml:222-236` | notation seulement, **détail calculatoire absent** | 🟡 **P0** — attendre cahier des charges RTE juillet 2026 |
| Deadline thermostat pièce par pièce 2027 | constants | — | ❌ **P1** |
| Trajectoire DT lissée (3-phase model) | `_trajectory_learning_ratio()` | `routes/cockpit.py` | ✅ |

### 5.4 Fenêtre marché (advisory flex)

| Fonctionnalité attendue | Code attendu | File:line | Verdict |
|---|---|---|---|
| NEBCO mise en service 1/9/2025 + seuil 100 kW | `flex_nebco_service.NEBCO_MIN_KW = 100` | `backend/services/flex_nebco_service.py:19` | ✅ — **commentaire date 1/9/2025 manquant** (P0 ergonomie) |
| Agrément RTE (PROMEOS pas agrégateur) | mode advisory M&V only | présent (zéro endpoint dispatch) | ✅ |
| 8 modèles paiement (HP/HC, Tempo, bloc+SPOT, primo-agrégateur LUCIOLE) | `archetype_recommendation.py` | présent | 🟡 — primo-agrégateur statut non discriminé |
| Score Flex-Ready® public/certifié | `FlexAssessment.flex_ready_certified` | `bacs_status` calculé mais **pas de label public** | ❌ **P0** — différenciation marché |
| Signal Tempo (1,2 M clients, ~400 MW, jours rouges 30-40 % HC) | flux EDF temps-réel | mention `flexibility_scoring_engine.mecanismes` | 🟡 — référencé sans intégration flux réel |
| Signal EcoWatt RTE 3-4 niveaux | hook RTE Transparency | `analytics_engine.py` + `orchestration/agents/regulatory.py` + `routes/cascade.py` (mentions) | 🟡 — référencé, **endpoint dédié `/api/flex/ecowatt-signal` absent** |
| Prix SPOT EPEX J-1 + intraday 15 min | `mkt_prices` `MarketType.SPOT_DAY_AHEAD` + intraday granularity | `models/market_models.py` + `routes/market.py:24-74` | 🟡 — daily OK, **intraday 15 min absent** |
| Mécanisme capacité RTE 1/11/2026 | `flex_nebco_service.py:22` (45 €/kW/an) | présent constant | 🟡 — **timeline explicite Nov 2026 manquante en commentaire** |
| ARENH → VNU 1/1/2026 | `tarifs_reglementaires.yaml` + `cost_simulator_2026.py` | seuils 78/110 €/MWh codifiés, VNU dormant 2026 | ✅ |
| Évolution post-ARENH (KB seed) | `demo_seed/orchestrator.py:~L430` | présent | ✅ |
| TURPE 7 HC daytime 2027-2028 | scenario tarifaire | — | ❌ **P1** — ~5 GW conso vers après-midi cible 2030 non modélisé |
| CBAM 1ère valorisation 7/4/2026 (75,36 €/tCO₂) | `tarifs_reglementaires.yaml:527-545` | présent | ✅ |
| Mode advisory strict (zéro auto-dispatch) | source-guard | tous endpoints `/api/flex/*` READ ou métadonnées | ✅ — source-guard confirmé |

### 5.5 Pilotage des usages (taxonomie 12 + familles 6)

| Usage déplaçable | Code | Verdict |
|---|---|---|
| Chauffage / CVC (60 % flex, 2-2,5 h inertie) | `FLEX_BY_USAGE["Chauffage"] / "CVC"` | ✅ |
| ECS (90 % flex, 6 h inertie) | `FLEX_BY_USAGE["ECS"]` | ✅ |
| Recharge VE IRVE | `CONTROLLABILITY_FACTOR["irve"]=0.5` | 🟡 — scoring sans modèle énergétique 15 % Psous |
| Ventilation (40 %, 0,25 h) | `FLEX_BY_USAGE["Ventilation"]` | ✅ |
| Éclairage (30 %, 0 h) | `FLEX_BY_USAGE["Éclairage"]` | ✅ |
| Froid commercial (~25 %, 1,5 h) | `CONTROLLABILITY_FACTOR["cold_storage"]=0.2` | 🟡 — pas de modèle énergétique cold_storage détaillé |
| IT / data center (5 %) | `FLEX_BY_USAGE["IT & Bureautique"]` | 🟡 — sous-estimé GPU farms |
| Process industriel (15 %) | `FLEX_BY_USAGE["Process"]` | 🟡 — pas de spécialisation pharma/chimie/agro |
| Climatisation (55 %, 0,33 h) | `FLEX_BY_USAGE["Climatisation"]` | ✅ |
| Cuisine (10 %) | `FLEX_BY_USAGE["Cuisine"]` | ✅ |
| Recommandations sobriété par usage | `consumption_diagnostic._actions_*()` | présent | ✅ |

### Synthèse Piloter

| Item | Verdict | Priorité |
|---|---|---|
| Centre d'Action 4 briques | ✅ | — |
| Brique FLEX → action_hub | ❌ | **P1** |
| Brique EMS → action_hub | ❌ | **P1** |
| Brique PATRIMOINE quantif (APER/BACS) | 🟡 | P1 |
| Impact `gain_kwh/eur/CO₂` backend | ✅ | — |
| Violations FE zero business logic (CO₂, tarif unitaire, agrégation risque) | ⚠️ | **P0** (cf. audit Sol2) |
| Échéances réglementaires (DT/BACS/APER/SMÉ) | ✅ | — |
| Capacité RTE 1/11/2026 timeline | 🟡 | P0 (post cahier des charges) |
| HC TURPE 7 daytime 2027-2028 | ❌ | **P1** |
| NEBCO advisory | ✅ + métadata commentaire | P0 ergonomie |
| BACS Flex-Ready® label public | ❌ | **P0** différenciation |
| Signal EcoWatt dédié `/api/flex/ecowatt-signal` | 🟡 | **P0** |
| Signal Tempo flux EDF | 🟡 | P1 |
| Intraday SPOT 15 min | 🟡 | P1 |
| 8 modèles LUCIOLE + UX décision | 🟡 | **P1** (primo-agrégateur) |
| Mode advisory strict (zéro auto-dispatch) | ✅ | — |
| Décomposition 6-sources base load | ❌ | **P1** (Griffine) |
| Cold storage / GPU / pharma archétypes | 🟡 | P2 |

---

## Synthèse globale — Gaps cardinaux par verbe

### Tableau récap

| Verbe | Couverture | Gaps P0 (bloquant pilote) | Gaps P1 (crédibilité) | Gaps P2 (différenciation) |
|---|---|---|---|---|
| **Centraliser** | 80 % | e-facture 1/9/2026 · parser PDF contrat · CSRD · APIs SGE V25→V26.2 · CleFIDO2 | Thermostat pièce par pièce 2027 | — (chaleur réseau + vapeur = hors scope court terme) |
| **Fiabiliser** | 80 % | Parser R6X JSON · CleFIDO2 · CACNC + CER facturation · Org-scoping 5 routers · pipeline anomalies wiring L17 | KPI registry FE mirror · 2 unit issues KPI · DJU v2025 · citations CRE NEBCO | — |
| **Comparer** | 70 % | CER HTA + BT>36 source-guard · CACNC bimestriel · C5 grilles détaillées | Comparateur TURPE 6 vs 7 · 8 modèles LUCIOLE primo-agrégateur · HC daytime 2027-2028 · Pointe mobile PP1 RTE | Archétype industrie lourde process |
| **Auditer** | 70 % | 5 règles TURPE 7 anomalies · pipeline anomalies L17 wiring · violations FE zero business logic (CO₂, tarif, agrégation) · CSRD · APER alerte cockpit < 6 semaines | Décomposition 6-sources base load · BAT-TH-116 < 5 % conso · CRE NEBCO traçabilité · règles segment + Psous surdim. + capacité incohérent | CUSUM + M&V IPMVP formel (ISO 50001 / ISO 14064-2) |
| **Piloter** | 75 % | Capacité RTE 1/11/2026 timeline · EcoWatt endpoint dédié · BACS Flex-Ready® label · CO₂ FE → BE · Tarif unitaire FE → BE · Agrégation risque FE → BE · NEBCO commentaire date | Briques FLEX + EMS action_hub · HC daytime 2027-2028 · 8 modèles LUCIOLE UX · Tempo flux EDF · Intraday SPOT 15 min · Décomposition 6-sources | Archétypes cold_storage/GPU/pharma |

### Top 10 P0 priorisés (bloquant pilote payant)

| # | Gap | Verbe(s) | Effort estimé | Source doc |
|---|---|---|---|---|
| 1 | **Pipeline anomalies wiring Phase L17** — confirmer que les 13 règles R19→R31 sont appelées en production | Auditer | 3-5 j | Mémoire `project_phase_L17_pipeline_dead_code_discovery_2026_05_09.md` |
| 2 | **CACNC + CER facturation TURPE 7** (3 composantes manquantes) | Comparer, Auditer | 5-7 j | Brochure TURPE 7 CRE 2025-78 |
| 3 | **APIs SGE V25→V26.2 + Authentification CleFIDO2** + parser R6X JSON | Centraliser, Fiabiliser | 10-14 j | 4 docs SGE Drive (0560, 0561, 0562, 0557) |
| 4 | **CSRD post-Omnibus** (transposition ordonnance 2023-1142) | Centraliser, Auditer | 8-12 j | Analyse experte obligations |
| 5 | **e-facture obligatoire 1/9/2026** (Factur-X / UBL + signature électronique) | Centraliser | 5-8 j | `FRN_20260123 Atelier RéformeFacturationElectronique` |
| 6 | **Parser PDF contrat** | Centraliser | 5-7 j | Sprint P0 repo pitch-ready |
| 7 | **3 violations FE zero business logic** (CO₂ FE → BE, tarif unitaire BE, agrégation risque/coût BE) | Piloter | 7-11 j | Audit Sol2 P0-3 / P0-4 / P0-5 |
| 8 | **APER alerte cockpit deadline 01/07/2026** (< 6 semaines) | Auditer, Piloter | 2-3 j | Loi APER 2023-175 + Décret 2024-1023 |
| 9 | **BACS Flex-Ready® label public** + EcoWatt endpoint dédié `/api/flex/ecowatt-signal` + NEBCO commentaire date | Piloter | 5-7 j | Baromètre flex 2026 |

**Total P0 estimé : ~50–74 j-h** (réduit de 5-7 j-h après reclassement chaleur réseau urbain hors scope court terme).

### Top 10 P1 priorisés (crédibilité scale-up)

| # | Gap | Verbe(s) | Effort |
|---|---|---|---|
| 1 | Briques FLEX + EMS → action_hub (`build_actions_from_flex/ems`) | Piloter | 3-5 j |
| 2 | Comparateur TURPE 6 vs 7 + ranking FTA optimal | Comparer | 5-7 j |
| 3 | Règles détection anomalies TURPE 7 (segment, CMDPS, CER, CACNC, FTA, Psous, capacité) | Auditer | 5-7 j |
| 4 | Décomposition 6-sources base load (Griffine 1/13) | Auditer, Piloter | 3 j |
| 5 | KPI registry FE mirror + source-guard + KPIs gaz / chaleur ajoutés | Fiabiliser | 4-6 j |
| 6 | Traçabilité CRE NEBCO + résolutions hardcodées | Fiabiliser | 2-3 j |
| 7 | TURPE 7 HC daytime 2027-2028 scénario | Comparer | 3-5 j |
| 8 | 8 modèles LUCIOLE explicites (primo-agrégateur statut) + UX décision | Comparer, Piloter | 4-5 j |
| 9 | Signal Tempo flux EDF + Intraday SPOT 15 min | Piloter | 8-12 j |
| 10 | Thermostat pièce par pièce 2027 + DPE tertiaire affichage 2026 | Centraliser | 5-8 j |

**Total P1 estimé : ~42–61 j-h.**

### P2 différenciation world-class (~30-50 j-h)

CUSUM ISO 50001 · M&V IPMVP B/C/D · forecasting probabiliste Monte-Carlo · géo-cartographie PV APER · archétypes industrie (vapeur, cold storage, GPU, pharma) · primo-agrégateur marketplace agrégateurs comparatif · veille réglementaire automatique CRE/RTE/JORF · `CarpetPlot.jsx` promotion MonitoringPage + Site360 + export PDF CFO.

---

## Cross-check inter-sous-agents : contradictions résolues

| Affirmation | Verdict croisé |
|---|---|
| Sub-agent flex : « EcoWatt absent » | ⚠️ Faux complet — 3 fichiers backend mentionnent EcoWatt (`analytics_engine.py`, `orchestration/agents/regulatory.py`, `cascade.py`) mais **aucun endpoint dédié `/api/flex/ecowatt-signal`**. Verdict 🟡 partiel. |
| Sub-agent TURPE 7 : « zéro parser R6X JSON » | ✅ Confirmé — `rg r6x|r64a|r64b|r63a|r63b` retourne 0 parser dédié, seulement mentions dans config et detectors. |
| Sub-agent TURPE 7 : « zéro CleFIDO2 » | ✅ Confirmé — `rg fido2|clefido|gardian` retourne 0 hit backend. |
| Sub-agent veille : « CER, CACNC à jour » | ❌ Faux — `rg cacnc|composante.energie.reactive` retourne 0 hit dans `billing_canonical_service`. Confirmé absent. |
| Sub-agent conformité : « build_actions_from_flex / ems présents ? » | ❌ Confirmé absent — `rg build_actions_from_flex|build_actions_from_ems` = 0 hit. |
| Sub-agent conformité : « CSRD absent » | ✅ Confirmé — seuls hits sont narrative_generator (templates UI), pas de logique métier. |
| Sub-agent multi-énergie : « chaleur réseau enum seulement » | ✅ Confirmé — seul hit `backend/schemas/contract_perimeter.py` (enum), aucun service de parsing facture. **Reclassé hors scope court terme (Mois 6+)** — pas un gap MVP. |

---

## Recommandation méthodologique

1. **Aucune correction de code dans ce rapport** — strict READ-ONLY.
2. Pour chaque P0 : ouvrir une branche `claude/fix-pXX-...` distincte (cf. `feedback_claude_branch_namespace.md`), suivre `docs/dev/methode_audit_avant_fix.md` (Phase 0 → STOP gate → phases → DoD → atomic commit → source-guard test).
3. Workflow pre-merge obligatoire : `/code-review:code-review` + `/simplify` + tests baseline FE ≥ 4 751 + BE ≥ 6 027 + Playwright si UI.
4. Branche cible : `claude/refonte-sol2` (jamais `main` — feedback `feedback_no_main_pollution.md`).
5. Ré-exécuter cet audit READ-ONLY tous les 30 j tant que `refonte-sol2` n'est pas mergée.
6. Croiser systématiquement avec `docs/audits/audit_readonly_promeos_scope_sans_acc_usage_steering.md` et `docs/audits/audit_docs_drive_promeos_sans_acc.md` (les 3 audits sont complémentaires, pas redondants).

---

## Annexes

### A. Docs Drive parcourus (90 jours, fév-mai 2026)

- **TURPE 7 + SGE** : brochure CRE 2025-78, délibérations CRE 2025-40 et 2025-78, plaquette consoprod, Flux F15, Rapport HC C1-C4, APIs SGE 0560/0561/0562/0557, GUI 0372 v1.8, CAR 0549 R6X, ateliers refonte R6X / API fournisseurs / e-facture, présentation changement API 2025-11-14, homologations V25.6 → V26.2 (C5 + C2C4).
- **BACS + Tertiaire + APER** : guide BACS officiel janvier 2026, fiche Alter Watt BACS, NF EN ISO 52120-1 mars 2022, classes GTB, META cours GTB ENDESA mars 2026, CCTP GTB, guide pratique BACS Advizeo 2025, diag BACS v2 Air France CMH, fiche DT Alter Watt, analyse experte multi-énergie.
- **Flex + NEBCO** : baromètre flex avril 2026, Yélé Consulting (Lot 1/3/4/exec summary/kick-off/SimuflexLite V2), Bamboo Energy pour Endesa, LUCIOLE Yele rapport flex.
- **Veille hebdos fév-mai 2026** : ~25 PDFs EE_Flashes / EE_GP / EE-N283 + N285 / GO + 4 Points marchés / Monthly meetings.
- **Multi-énergie + KPI** : Endesa Griffine analyses 9.04, DJU Nucourt, fichier conso EMS2, NAF tarification, Endesa EnergyLab, ECG Endesa Session 1 & 2, AF OMS, Interview CLEEE 13/05/2026, Elec pour KAMs GNV.

### B. Métriques code (HEAD `ade3d0a0`)

| Métrique | Valeur |
|---|---|
| Routers backend | 104 |
| Services backend | ~90 |
| Modèles SQLAlchemy | ~80 (100 % `org_id` ou inférable) |
| Routes frontend | 57 |
| Composants frontend | ~270 |
| Tests backend (fichiers) | 545 |
| Tests frontend (fichiers) | 234 |
| Source-guards V4 | 57 |
| KPI registry | 11 KPI canoniques |

### C. Audits PROMEOS complémentaires

- `docs/audits/audit_readonly_promeos_scope_sans_acc_usage_steering.md` (audit READ-ONLY repo · 22/05/2026)
- `docs/audits/audit_docs_drive_promeos_sans_acc.md` (extraction 6 docs Drive · 22/05/2026)
- `docs/audits/AUDIT_CENTRE_ACTION_2026_05_13.md`
- `docs/audits/AUDIT_REGLEMENTAIRE_CARDINAL_2026_05_07.md`
- `docs/audits/AUDIT_TURPE7_DATES_2026_05_07.md`
- `docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md`
- `docs/audits/AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md`

### D. Doctrine de référence

- `project_promeos_vision_consolidee_v1_3_2026_05_08.md` (5 verbes + 5 questions + 5 règles + pricing 3 tiers)
- `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.3
- ADR Mois 1 (ADR-025 → ADR-029) — architecture V4, lifecycle, evidence
- `docs/dev/L1` → `L11` (audit + plan)

---

**Fin de l'audit gap mapping** — branche `claude/refonte-sol2` @ `ade3d0a0` — 2026-05-23.
**Worktree** : `.claude/worktrees/audit-mapping-sol2/` (à nettoyer après lecture).
**Aucune modification de code n'a été effectuée pendant cet audit hormis ce livrable.**
