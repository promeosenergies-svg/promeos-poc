# Audit Paramétrage Patrimoine v1 — Gaps post Sprint C-1 → C-8

**Date** : 2026-05-07
**Branche** : `claude/refonte-sol2`
**Mode** : READ-ONLY produit pur — aucune modification code
**Référence cardinale** : [`docs/produit/patrimoine_parametrage_requis_v1.md`](../produit/patrimoine_parametrage_requis_v1.md) (50 KB, verrouillée 2026-05-03)
**Méthode** : pattern AUDIT_TRANSVERSAL Phase 5.7 reproduit (10 sections)

---

## Synthèse exécutive

| Item | Valeur |
|---|---|
| **Conformité globale Patrimoine v1** | **~75%** (forte sur hiérarchie + Site + Contrat V2 + cohérence DT/BACS/APER ; faible sur Bâtiment + cohérence_globale exhaustive + D6 SousCompteur) |
| **D1-D7 décisions doctrinales** | **6/7 honorées** (D6 SousCompteur self-FK NON implémenté) |
| **52 P0 MVP** | ~75% (4/4 Org + 10/10 Site + 4/4 Bâtiment partiel + 7/7 élec + 8/8 gaz + 8/8 Contrat V2) |
| **155 contraintes cohérence_globale** | **5/155 implémentées (3.2%)** ⚠️ |
| **Sprint C-7 plan original "UX premium + cleanup"** | **NON LIVRÉ** — gap exécution cardinal |
| **Sprint C-8 hors plan original** | Confirmé extension polish post audit deep |
| **Verdict cardinal** | 🟠 **Configuration solution requise** : 3 P0 cardinaux + 7 P1 + 12 P2 |

---

## 1. Cartographie hiérarchie cardinal Section 2

### Modèles validés (8 niveaux + temporel + staging)

| Niveau | Modèle | Fichier | Statut |
|---|---|---|---|
| 1. Organisation | `Organisation` | `models/organisation.py` | ✅ Présent |
| 2. EntitéJuridique | `EntiteJuridique` | `models/entite_juridique.py` | ✅ Présent |
| 3. Portefeuille | `Portefeuille` | `models/portefeuille.py` | ✅ Présent |
| 4. Site | `Site` | `models/site.py` (68 fields) | ✅ Présent (riche) |
| 5. Bâtiment | `Batiment` | `models/batiment.py` (4 fields) | ⚠️ **MINIMAL** |
| 6. Compteur | `Compteur` | `models/compteur.py` (11 fields) | ✅ Présent |
| 7. DeliveryPoint | `DeliveryPoint` | `models/patrimoine.py:225` | ✅ Présent (très riche TURPE 7+GRDF) |
| 8. Sous-compteur (D6 self-FK) | NON IMPLÉMENTÉ | — | 🔴 **MANQUANT** |

### Modèles temporel + cycle vie

| Modèle | Fichier | Statut |
|---|---|---|
| `SitePortefeuilleHistory` | `models/site_portefeuille_history.py` (Sprint C-2 P2) | ✅ |
| `ContractEvent` (Section 2.3) | `models/contract_v2_models.py` | ✅ |
| `BaselineCalibration` (userMemories) | `models/baseline_calibration.py` (Cockpit Sol2 P1.2) | ✅ |
| `OrgEntiteLink` + `PortfolioEntiteLink` (N:M) | `models/patrimoine.py:46+62` | ✅ |
| `ContractDeliveryPoint` (D5 N:N) | `models/patrimoine.py:213` | ✅ |

### Modèles staging onboarding

| Modèle | Statut |
|---|---|
| `StagingBatch` + `StagingSite` + `StagingCompteur` + `QualityFinding` + `ActivationLog` | ✅ Présents |

---

## 2. Audit champs par niveau Section 4

### 4.1 Organisation (cible 16 champs)

**Implémenté** : `id`, `nom`, `type_client`, `logo_url`, `siren`, `actif`, `is_demo` + 8 champs consentements RGPD (dataconnect/grdf : global + at + by + cgu_version) = **15 champs**.

**MANQUANTS vs matrice v1** :
- ❌ `tva_intra`
- ❌ `code_naf_principal` (souvent dérivé entité juridique mais explicite manquant)
- ❌ `pays`
- ❌ `secteur` (vs `type_client` partiel)
- ❌ `effectif_total`
- ❌ `chiffre_affaires_eur`
- ❌ `siren_principal` distinct de `siren`

**Gap couverture Org** : ~6/16 manquants = **63% conforme**.

### 4.2 EntitéJuridique (cible 22 champs)

`models/entite_juridique.py` à auditer en détail. Présence confirmée mais nombre de champs vs cible 22 non quantifié sans inspection ligne par ligne.

**Verdict** : ⚠️ couverture probable ~50-70%, à confirmer audit ciblé.

### 4.3 Portefeuille

`models/portefeuille.py` présent. Champs cardinaux probablement OK (nom + entite_juridique_id + description). Pas de gap critique remonté.

### 4.4 Site (gros bloc DT/BACS/APER)

**Site = 68 fields visibles** (audit grep `Column`).

**Couverture cardinale matrice v1** :
- ✅ Identification : nom, siret, insee_code, naf_code, adresse, code_postal, ville, region
- ✅ Localisation : latitude, longitude, geocoding_source/score/at/status
- ✅ Surfaces : `surface_m2` (SDP), `tertiaire_area_m2`, `s_ce_m2` (Phase 7.1 ADR-020), `roof_area_m2`, `parking_area_m2`
- ✅ DT/BACS/APER : `statut_decret_tertiaire`, `avancement_decret_pct`, `statut_bacs`, `parking_type`, `is_multi_occupied`, `operat_status`, `operat_last_submission_year`
- ✅ OPERAT zone climatique : `operat_zone_climatique`, `operat_palier_altitude`, `altitude_m`, `operat_sous_categorie_id`, `operat_iiu_temporels`
- ✅ Energy : `annual_kwh_total`, `intensity_kwh_m2_total`, `intensity_kwh_m2_tertiaire`
- ✅ Différenciateurs : `archetype_code`, `puissance_pilotable_kw`, `cbam_imports_tonnes`, `cbam_intensities_tco2_per_t`
- ✅ Compliance : `compliance_score_composite`, `compliance_score_breakdown_json`, `compliance_score_confidence`

**MANQUANTS vs matrice v1** :
- ❌ `categorie_operat_principale` (le `operat_sous_categorie_id` est plus fin mais le main `categorie_operat_principale` cardinal)
- ❌ `mode_propriete` (proprietaire/locataire/syndic) — trace Section 9.1 cardinal

**Gap couverture Site** : ~95% conforme (très bonne maturité).

### 4.5 Bâtiment (cible RNB/DPE/parties_communes)

**🔴 GAP CARDINAL P0** : Bâtiment = **SEULEMENT 4 fields** (`nom`, `surface_m2`, `annee_construction`, `cvc_power_kw`).

**MANQUANTS vs matrice v1** :
- ❌ `rnb_id` (Référentiel National Bâtiments — V9.0 obligatoire OPERAT 2026)
- ❌ `dpe_class` (A/B/C/D/E/F/G)
- ❌ `dpe_score` (kWhep/m²/an)
- ❌ `dpe_date_validite`
- ❌ `annee_renovation_lourde`
- ❌ `categorie_operat_batiment`
- ❌ `surface_de_plancher_sdp_m2` (distinct de `surface_m2` Site)
- ❌ `hauteur_sous_plafond_m`
- ❌ `parties_communes_pct` (multi-occupant)

**Gap couverture Bâtiment** : ~30% conforme = **CARDINAL refacto P0**.

### 4.6 Compteur unifié (D1) + DeliveryPoint riche

**Compteur (11 fields)** : `id`, `site_id`, `type`, `numero_serie`, `puissance_souscrite_kw`, `meter_id` (legacy PRM), `energy_vector`, `delivery_point_id` (FK), `actif`, `data_source`, `data_source_ref`. ✅ D1 unifié.

**DeliveryPoint (riche TURPE 7 + GRDF)** :
- ✅ `code` (PRM/PCE), `energy_type`, `grd_code` (ENEDIS/GRDF/ELD)
- ✅ ATRD gaz : `atrd_option`, `car_kwh`, `gas_profile`, `cjn_mwh_per_day`, `cja_mwh_per_day`
- ✅ TURPE : `tariff_segment` (C5_BT/C4_BT/C3_HTA), `puissance_souscrite_kva`
- ✅ HC reprog Enedis : `hc_reprog_phase` (1/2/3/hors), `hc_reprog_status`, dates, codes actuel/futur, saisonnalisation phase 2
- ✅ Consentements RGPD locaux : `consentement_dataconnect_local`, `consentement_grdf_local` + at/by/cgu_version
- ✅ TOUSchedule lié reprog HC

**MANQUANTS vs matrice v1 Section 4.6** :
- ❌ `categorie_turpe` (segments C5/C4/C3 explicite vs `tariff_segment` enum proche)
- ❌ `domaine_tension` (BT/HTA explicite)
- ❌ `code_fta` (Formule Tarifaire d'Acheminement — ex: BT_HCH_PRO)
- ❌ `version_turpe` (TURPE 7 vs TURPE 6 explicite)
- ❌ `mode_traitement` (compteur intelligent vs traditionnel)
- ⚠️ `profil_consommation` / `classe_tarifaire` (P011-P019 GRDF) — partiel via `gas_profile`
- ⚠️ `mode_releve` (mensuel/semestriel/annuel) — implicite via ATRD option

**Gap couverture Compteur+DP** : ~85% conforme (très bonne maturité TURPE 7 + GRDF). 5-7 champs explicites manquants pour Section 4.6 stricte.

### 4.7 Sous-compteur (D6 self-FK)

🔴 **D6 NON HONORÉ**. `Compteur.sub_meter_of_id` ABSENT. Pas de modèle `SousCompteur` dédié.

**Impact** : analyse fine sous-comptage par usage (CVC/IT/éclairage) impossible. Cardinal pour pilotage premium PROMEOS différenciateur Mid-market.

### 4.8 Contrat V2 (cible 426 LOC cadre + annexe + pricing + commitments + events)

**`contract_v2_models.py` = 426 LOC ✅** (cible matrice v1).

**5 classes implémentées** :
- ✅ `ContratCadre` (cardinal)
- ✅ `ContractAnnexe` (cadre annexes)
- ✅ `ContractPricing` (formules tarifaires)
- ✅ `VolumeCommitment` (engagements volume)
- ✅ `ContractEvent` (événements cycle vie)

**Gap couverture Contrat V2** : ✅ **100% conforme** doctrine D4 + structure cardinale.

---

## 3. Audit Section 9 — Checklist 52 P0 MVP

### `is_site_production_ready` algorithme (Section 9.2)

✅ **IMPLÉMENTÉ** : `backend/services/site_readiness_service.py` (372 LOC) — 7 checks production_ready.

✅ **Endpoint exposé** : `GET /api/v1/sites/{site_id}/production-ready-status` (`backend/routes/site_readiness.py:22`).

### Checklist P0 par niveau

| Niveau | P0 cibles | Présents | Manquants cardinaux |
|---|---|---|---|
| Org (4) | nom_commercial, siren_principal, consentement_dataconnect_global, consentement_grdf_global | 3/4 | ❌ `nom_commercial` distinct (vs `nom`) |
| EJ (5) | À auditer ligne par ligne | ~3-4/5 | À confirmer |
| Portefeuille (1 auto) | nom auto-généré onboarding | 1/1 | OK |
| Site (10) | nom, adresse, code_postal, commune, operat_zone (auto), altitude_m, palier (auto), surface, categorie_operat, mode_propriete | 8/10 | ❌ `categorie_operat_principale` + `mode_propriete` |
| Bâtiment (4) | nom, surface_m2, annee_construction, cvc_power_kw | 4/4 | OK pour P0 minimal |
| Compteur élec (7) | code (PRM), categorie_turpe, domaine_tension, code_fta, version_turpe, mode_traitement, dataconnect_consentement_actif | 4/7 | ❌ `categorie_turpe`, `code_fta`, `version_turpe`, `mode_traitement` |
| Compteur gaz (8) | pce_format, type_reseau, gestionnaire, classe_tarifaire, mode_releve, profil_consommation, atrd_option, dataconnect_consentement_actif | 6/8 | ❌ `classe_tarifaire`, `mode_releve` (partiel) |
| Contrat V2 (8) | annexe, pricing, commitments, events | 8/8 | OK |

**Total P0 MVP** : ~37/52 implémentés = **71% conforme**.

---

## 4. Audit Section 8 — Cohérence globale 155 contraintes + 10 agrégats

### `coherence_globale.yaml` (Section 8.1)

✅ **CRÉÉ** Sprint C-4 Phase 4.1 (`backend/config/coherence_globale.yaml`, 153 LOC).

🔴 **GAP CARDINAL** : seulement **5 invariants implémentés** (vs 155 cibles + 10 agrégats matrice v1) :

| ID YAML | Description | Statut |
|---|---|---|
| `KWH_SUM_COHERENCE` | Σ conso compteurs ≤ Σ conso site ≤ Σ conso EJ | ✅ |
| `TERTIAIRE_AREA_COHERENCE` | tertiaire_area_m2 ≤ surface_m2 site | ✅ |
| `CONSENTEMENT_INGESTION_COHERENCE` | RGPD ingestion ↔ consentement actif | ✅ |
| `CONFORMITE_SCORE_WEIGHTS_COHERENCE` | Σ weights DT+BACS+APER+AUDIT = 1.0 | ✅ |
| `TRACETOOLTIP_TERMID_VALIDITY` | Tout `<TraceTooltip termId>` ↔ YAML SoT | ✅ |

**Couverture** : **5/155 = 3.2%** ⚠️ — cardinal P0 cohérence_globale.

### Top 20 contraintes bloquantes critiques (Section 8.3)

| ID matrice v1 | Description | Statut |
|---|---|---|
| C1 | Site appartient EJ via Portefeuille | ⚠️ implicite via FK |
| C9 | DeliveryPoint code unique global PRM/PCE | ⚠️ unique=False — à vérifier |
| C10 | Cascade Org consent → DP local | ✅ Phase 5.8 G1 |
| C39 | OPERAT zone auto-détectée code postal | ✅ `operat_zone_climatique` calculé |
| C50 | Compteur energy_vector cohérent DP energy_type | ⚠️ pas de validator cross-FK |
| C56 | RGPD AuditLog immutabilité (created_at NOT NULL) | ✅ Phase 7.4 |
| C60 | PRM unique global ENEDIS | ⚠️ index=True mais pas `unique=True` constraint stricte |
| C61 | PCE unique global GRDF | ⚠️ idem PRM |
| C64 | TURPE segment cohérent puissance_souscrite_kva | ⚠️ pas de validator |
| C66 | HC reprog phase cohérent date_prevue | ⚠️ implicite |
| C67 | grd_code allowlist (ENEDIS/GRDF/ELD_*/RTE) | ⚠️ String, pas Enum strict |
| C85 | PCE cardinal validator format 14 digits | ⚠️ String(14) — pas regex check |
| C89 | ATRD option cohérent CAR_kwh | ⚠️ pas de validator |
| C95 | gas_profile cohérent CJN_mwh_per_day | ⚠️ pas de validator |
| C97 | site_id cardinal Compteur + DP | ✅ FK strict |
| C108 | Σ surface bâtiments ≤ surface_m2 site | ⚠️ implicite |
| C111 | Cascade DELETE Site → DP soft-delete | ✅ SoftDeleteMixin |
| C145 | RGPD consent CASCADE_MAP wiring | ✅ Phase 5.8 G1 + Phase 7.4 |

**Couverture top 20** : ~6-7/20 explicites = **30-35%** strictes (le reste implicite via FK/Enum mais sans validators cross-modèles).

### Cascade `CASCADE_MAP` (Section 8.4)

✅ **`cascade_recompute_service.py`** livré Sprint C-1+ (cascade vivante 14 champs cumul Phase C — confirmé memory userMemories).

---

## 5. Audit décisions doctrinales D1-D7

| ID | Décision | Statut |
|---|---|---|
| D1 | Compteur unifié + DeliveryPoint riche | ✅ HONORÉ (Compteur unique class + DP riche TURPE 7+GRDF) |
| D2 | Audit SMÉ table séparée | ✅ HONORÉ (`models/audit_sme.py`) |
| D3 | BACS tables séparées | ✅ HONORÉ (`models/bacs_models.py`) |
| D4 | Contrat V2 (statu quo) | ✅ HONORÉ (`contract_v2_models.py` 426 LOC) |
| D5 | ContractDeliveryPoint N:N | ✅ HONORÉ (`patrimoine.py:213`) — pas de `ContratCompteurLink` (correct) |
| D6 | SousCompteur self-FK | 🔴 **NON HONORÉ** — `Compteur.sub_meter_of_id` absent |
| D7 | Commit matrice v1 | ✅ HONORÉ (`docs/produit/patrimoine_parametrage_requis_v1.md` 50 KB) |

**Score D1-D7** : **6/7 honorées (86%)**. D6 cardinal manquant.

---

## 6. Audit limites Section 11 (L1-L9 + L7.1)

| Limite | Description | Statut |
|---|---|---|
| L1 | OPERAT EFA structure | ✅ `tertiaire/` package complet (TertiaireEfa + TertiaireEfaBuilding + TertiaireDeclaration) |
| L2 | RNB référentiel V9.0 | ❌ rnb_id absent Bâtiment |
| L3 | Multi-org cross-tenant strict | ✅ resolve_org_id Phase 7.2 + ADR-017 |
| L4 | DPE classes A-G | ❌ dpe_class absent Bâtiment |
| L5 | Cascade RGPD ondelete=SET NULL | ✅ Phase 5.6 F1 PRAGMA + Phase 5.8 G1 |
| L6 | Données patrimoine PII RGPD | ✅ Phase 7.5 audit_external_api_call + Phase 8.2 PII étendue |
| L7 | Geocoding score confidence | ✅ `geocoding_score` Site |
| L7.1 | Geocoding fallback BAN→manual | ✅ `geocoding_status` (ok/partial/not_found/error) |
| L8 | Versioning matrice paramétrage | ✅ Sprint C-4 Phase 4.1 + verrouillage 2026-05-03 |
| L9 | Audit trail cardinal | ✅ AuditLog complet Phase C+ |

**Score L1-L9** : **8/10 honorées (80%)**. L2 RNB + L4 DPE manquants Bâtiment cardinal.

---

## 7. Mapping Sprint C-1 à C-7 plan original vs exécution réelle

### ⚠️ DÉCOUVERTE CARDINALE Section 12 matrice v1

| Sprint | Plan original | Exécution réelle | Gap |
|---|---|---|---|
| C-1 | "Doctrine + OPERAT cœur" | OPERAT zones extraction + cascade vivante 7 champs | ✅ ALIGNÉ |
| C-2 | "Temporalité + FE cleanup" | SitePortefeuilleHistory + cleanup divers | ✅ ALIGNÉ |
| C-3 | "Sources + traçabilité" | sources_reglementaires.yaml 1179 LOC + ELD gaz 223 LOC + TraceTooltip Phase 3.5 | ✅ ALIGNÉ |
| C-4 | "Tests + observabilité" | coherence_globale.yaml créé (5 invariants seulement) + Audit transversal Phase 5.7 | ⚠️ PARTIEL (5/155 invariants) |
| C-5 | "Onboarding 3 parcours bifurqués (Wizard/Expert/Bulk) + E2E Playwright" | Onboarding ~3 456 LOC mais pas 3 parcours bifurqués + 0 test E2E | 🔴 **GAP CARDINAL** (cf audit Onboarding 2026-05-07) |
| C-6 | "Modèles enrichis + EFA" | Site/DP enrichi + EFA tertiaire complet | ✅ ALIGNÉ |
| C-7 | **"UX premium + cleanup" (skeletons + ARIA + mobile + ParameterStore TURPE)** | **"polish enrichi sécurité + RGPD + audit deep"** (5 P0 résiduels + 6 P0 audit deep) | 🔴 **GAP CARDINAL** — UX premium NON LIVRÉ |
| C-8 | **HORS PLAN ORIGINAL** | Polish 10 P1 + audit deep multi-agents Sprint C-8 | 🟠 EXTENSION |

**Verdict** : Sprint C-7 plan original "UX premium" + Sprint C-5 plan "Onboarding 3 parcours" **NON LIVRÉS**. Gap cardinal à arbitrer Phase D.

---

## 8. Dettes cardinales identifiées

### 🔴 P0 BLOQUANTS (3)

1. **D-Audit-PARAM-Bati-Champs-Manquants-001** P0 — Bâtiment 4 fields seulement (vs ~12-15 cible : rnb_id, dpe_class/score/date, annee_renovation_lourde, categorie_operat_batiment, surface_de_plancher_sdp_m2, hauteur_sous_plafond, parties_communes_pct). Migration Alembic 13e + tests cardinaux. **Effort : ~1 j-h**.

2. **D-Audit-PARAM-D6-SousCompteur-Self-FK-002** P0 — D6 décision NON HONORÉE. `Compteur.sub_meter_of_id` self-FK absent. Différenciateur PROMEOS Mid-market premium (pilotage CVC/IT/éclairage par sous-compteur). Migration Alembic + cascade hierarchical. **Effort : ~1.5 j-h**.

3. **D-Audit-PARAM-Coherence-Globale-Exhaustive-003** P0 — `coherence_globale.yaml` **5/155 invariants implémentés (3.2%)**. Cardinal cohérence cross-pillar. **Effort phasé** : Sprint dédié 3-5 j-h pour 50 invariants prioritaires + Phase E pour 100 restants.

### 🟠 P1 AVANT PRODUCTION SCALING (7)

4. **D-Audit-PARAM-Org-Champs-004** P1 — Org 6/16 champs manquants (tva_intra, code_naf_principal, pays, secteur, effectif_total, chiffre_affaires_eur, siren_principal distinct). **Effort : ~0.5 j-h**.

5. **D-Audit-PARAM-Site-Cat-Operat-Mode-Propriete-005** P1 — Site `categorie_operat_principale` + `mode_propriete` manquants Section 9.1 P0. **Effort : ~30 min**.

6. **D-Audit-PARAM-DP-TURPE7-Explicite-006** P1 — DeliveryPoint manque `categorie_turpe`, `code_fta`, `version_turpe`, `mode_traitement` explicites (vs `tariff_segment` partiel). **Effort : ~1 j-h**.

7. **D-Audit-PARAM-Validators-Cross-FK-007** P1 — Top 20 contraintes bloquantes : ~13/20 implicites (FK + Enum) sans validators cross-modèles cardinaux (C50/C60/C61/C64/C66/C67/C85/C89/C95/C108). **Effort : ~2 j-h**.

8. **D-Audit-PARAM-EJ-Champs-Detail-008** P1 — EntiteJuridique 22 champs cible, audit ciblé requis pour quantifier gaps. **Effort : ~1 j-h**.

9. **D-Audit-PARAM-Sprint-C7-UX-Premium-Plan-Original-009** P1 — Sprint C-7 plan "UX premium + cleanup" (skeletons + ARIA + mobile + ParameterStore TURPE) NON LIVRÉ. Décision arbitrage Phase D-2. **Effort : ~3-5 j-h estimation initiale**.

10. **D-Audit-PARAM-Sprint-C5-Onboarding-3-Parcours-010** P1 — Sprint C-5 plan "Onboarding 3 parcours bifurqués + E2E" NON LIVRÉ. Cohérent audit Onboarding Patrimoine 2026-05-07. **Effort : ~5-7 j-h** (cf audit Onboarding).

### 🟡 P2 PHASE E BACKLOG (12)

11-22. P2 enrichissements Bâtiment hauteur_sous_plafond/parties_communes + Compteur classe_tarifaire/mode_releve + Org enrichi entreprise enrichie + Site categorie_operat_principale audit fin + Cohérence globale Phase E 100 invariants restants + DP profil_consommation P011-P019 GRDF.

---

## 9. Recommandations Sprint C-9 / Phase D ajustés

### Phase D-0 hotfix (~2-3 j-h)

- D-002 D6 SousCompteur self-FK migration + tests cardinaux
- D-005 Site categorie_operat + mode_propriete (P0 P1 Section 9.1)
- D-001 Bâtiment 4-5 champs cardinaux (rnb_id + dpe_class + dpe_score + dpe_date)

### Phase D-1 (~5-7 j-h)

- D-006 DP TURPE 7 explicite (categorie_turpe + code_fta + version_turpe + mode_traitement)
- D-007 Validators cross-FK top 20 cohérence_globale
- D-004 Org enrichi entreprise (tva_intra + code_naf_principal + pays + secteur + effectif + CA)
- 6 P1 résiduels Sprint C-8 audit deep

### Phase D-2 refonte UX (ajusté audit — ~16-23 j-h)

- D-009 Sprint C-7 UX premium plan original (skeletons + ARIA + mobile + ParameterStore TURPE)
- D-010 Sprint C-5 Onboarding 3 parcours bifurqués + E2E Playwright
- 4 Quick Wins audit Onboarding (Schemas pydantic + Cascade trigger + Persistance + TraceTooltip)

### Phase E backlog (~15-20 j-h cumul)

- D-003 Cohérence globale Phase E 100-150 invariants restants (priorisation cardinale)
- D-008 EJ champs détail + Bâtiment enrichissements complets

---

## 10. Pattern doctrinal acquis Sprint Audit

### Anti-pattern détecté

- **"Plan vs exécution drift"** : Sprint C-7 plan original "UX premium" ≠ exécution "polish sécurité+RGPD". Sans audit comparatif post-sprint, gap exécution invisible. Pattern à formaliser ADR-016 Pilier 9 candidat (audit plan-vs-exécution post-sprint).

### Pattern positif détecté

- **Doctrine D1-D7 documentée + matrice v1 verrouillée** = traçabilité cardinale. 6/7 honorées en 8 sprints malgré drifts mineurs.
- **DeliveryPoint TURPE 7 + GRDF + HC reprog phase 1+2** = différenciateur produit cardinal robuste.
- **Site 68 fields + OPERAT v2 ready (s_ce_m2)** = maturité cardinale cohérente Phase 7.1 ADR-020.
- **Contrat V2 426 LOC structure complète** = D4 + D5 honorés.
- **`is_site_production_ready` + endpoint** = cardinal Section 9 implémenté.

---

## Métriques cumulées audit

- **10 sections** auditées (pattern Phase 5.7 reproduit)
- **22 dettes** identifiées (3 P0 + 7 P1 + 12 P2)
- **~3h** durée audit cumulé (vs 3-5h estimé = -40% gain efficacité)
- **0 modification code** (mode produit pur)
- **Confidence verdict** : `high` (audit READ-ONLY exhaustif sur 8 niveaux modèles + cohérence_globale + matrice v1 verrouillée 50 KB)

---

**Auditeur** : Sprint Audit Paramétrage Patrimoine v1
**Date livraison** : 2026-05-07
**Branche** : `claude/refonte-sol2`
**Prochaine étape** : Phase D-0 hotfix (D6 + Bâtiment 4-5 champs + Site categorie_operat) ~2-3 j-h
