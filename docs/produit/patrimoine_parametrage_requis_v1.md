# Patrimoine — Matrice de paramétrage requise (v1)

> **Document de référence Phase A.0** — consolidé après audit Phase B (livrable Claude Code 2026-05-03).
> **Branche** : `claude/refonte-sol2`
> **Statut** : 🟢 Verrouillé Phase A.0 — base d'exécution Phase C (sprints C-1 à C-7)
> **Adaptation** : matrice **adaptée au repo PROMEOS réel** (Option B sur D1-D6), pas inverse.

---

## Métadonnées

| Champ | Valeur |
|---|---|
| Schema version | `1.0` |
| Date | `2026-05-03` |
| Auteur | Amine + Claude (PROMEOS doctrine) |
| Sources principales | Audit Phase B `AUDIT_PATRIMOINE_PHASE_B_2026_05_03.md`, livrables `regulatory-expert` OPERAT VA + L2 zones |
| Branche d'exécution | `claude/refonte-sol2` |
| Sprints suivants | Phase C-1 à C-7 (~85-120 j-h estimés) |

---

## 1. Cadrage

### 1.1 Objectif

Spécifier exhaustivement les **données du patrimoine** que PROMEOS doit collecter, valider, stocker et exposer pour permettre :

- Calculs réglementaires automatisés (DT/OPERAT, BACS, APER, Audit SMÉ, ISO 50001, Solarisation toiture)
- Analytics énergétiques (intensité kWh/m², CO₂, trajectoire DT)
- Bill Intelligence (audit factures, détection anomalies, cohérence consos)
- Centre d'action proactif (alertes, recommandations sourcées)
- Tooltip traçabilité réglementaire **différenciateur** (NOR + URL Légifrance + date d'effet)

### 1.2 Principes directeurs

1. **Tout est lié** : patrimoine → données → KPIs → alertes → actions → conformité → billing → achat
2. **Source-guards** : aucune constante réglementaire hard-codée hors `backend/doctrine/constants.py` ou YAMLs/JSONs sourcés
3. **Zéro logique métier en frontend** (calculs côté backend uniquement)
4. **KPI traçable** : définition + source + formule + périmètre + période documentés
5. **Iphone-grade simplicity** : onboarding minimal (52 champs P0 sur ~310 modélisés)
6. **Non-expert first / expert respecté** : 3 parcours (Wizard / Expert / Bulk)

### 1.3 Couverture attendue

- 9 typologies OPERAT (Bureaux, Commerces, Enseignement, Hôtellerie, Restauration, Santé, Sport-loisirs, Logistique, Mixte)
- France métropole (96 dép) + DOM (5 zones : Guadeloupe, Martinique, Guyane, Réunion, Mayotte)
- Énergies : électricité (TURPE 7) + gaz (ATRD/ATRT) + extensible (eau, autres vecteurs)

---

## 2. Hiérarchie patrimoniale

### 2.1 Modèle hiérarchique

```
Organisation (Org)
  └─ Entité juridique (1..N)            [SIREN/SIRET/NAF]
       └─ Portefeuille (1..N)            [groupement opérationnel]
            └─ Site (1..N)                [actif physique géolocalisé]
                 ├─ Bâtiment (1..N)       [composante physique]
                 │    ├─ EFA OPERAT (lien)
                 │    └─ RNB id (V9.0)
                 └─ Compteur (1..N)        [point de mesure]
                      ├─ DeliveryPoint    [PRM élec OU PCE gaz — 1:1]
                      ├─ Sous-compteur (0..N) [self-FK Compteur]
                      └─ Contrats (N:N via ContractDeliveryPoint)

Contrat V2 (cadre)
  ├─ AnnexeSite (1..N)                    [déclinaison par site]
  ├─ ContractPricing                       [structure prix]
  ├─ VolumeCommitments                     [engagements volume]
  ├─ ContractEvents                        [historique]
  └─ ContractDeliveryPoint (N:N)           [liens N:N PRM/PCE]
```

### 2.2 Cardinalités validées

| Relation | Cardinalité | Notes |
|---|---|---|
| Org → Entité juridique | 1:N | 1 Org peut grouper plusieurs entités |
| Entité juridique → Portefeuille | 1:N | Auto-création "Principal" si 0 portefeuille |
| Portefeuille → Site | 1:N (temporel) | Voir SitePortefeuilleHistory pour bascule |
| Site → Bâtiment | 1:N | Site monobloc = 1 bâtiment auto-créé |
| Site → Compteur | 1:N | Multi-énergie possible |
| Compteur → DeliveryPoint | 1:1 | Spécificité technique (élec/gaz) |
| Compteur → Sous-compteur | self-FK 1:N | `sub_meter_of_id` (D6 self-FK) |
| ContratCadre → AnnexeSite | 1:N | Décomposition par site |
| ContratCadre → ContractDeliveryPoint | 1:N | Liens N:N PRM/PCE (D5) |

### 2.3 Règles temporelles

- `SitePortefeuilleHistory` (table dédiée) : valid_from / valid_to pour bascule portefeuille
- `ContractEvents` : historique modifications contrat
- `BaselineCalibration` : recalibration baselines tous les 7 jours
- `EFA OPERAT` : succession changement occupant (lien EFA prédécesseure)

---

## 3. Légende

### 3.1 Criticité champs

| Niveau | Sigle | Signification |
|---|---|---|
| 🔴 P0 | Bloquant | Champ absolument requis (saisie ou auto) — sans lui, site non production-ready |
| 🟠 P1 | Crédibilité | Champ nécessaire pour calculs réglementaires complets ou analytics fines |
| 🟡 P2 | Polish | Champ d'enrichissement — premium UX / différenciateur |

### 3.2 Sources possibles

| Code | Source |
|---|---|
| `user_manual` | Saisie manuelle utilisateur |
| `api_gov` | API gouvernementale (geo.api.gouv.fr, Sirène, etc.) |
| `api_enedis` | DataConnect OAuth2 (élec) |
| `api_grdf` | ADICT REST (gaz GRDF) |
| `api_meteo` | Open-Meteo (DJU) |
| `api_ademe` | ADEME Base Empreinte / OPERAT |
| `ocr_invoice` | Extraction facture (Bill Intelligence) |
| `inferred` | Calculé/déduit depuis autres champs |
| `fixed_constant` | Constante doctrine (`backend/doctrine/constants.py`) |

### 3.3 Catégorie traçabilité € (EurAmount)

| Catégorie | Description |
|---|---|
| **A** — CALCULATED_REGULATORY | Calculé depuis source réglementaire (NOR cité) |
| **B** — CONTRACTUAL | Issu contrat réel (numéro contrat cité) |
| **null** | Pas applicable (champ non monétaire) |

### 3.4 Couleurs validation

| Couleur | Sens |
|---|---|
| 🟢 | Conforme cible / opérationnel |
| 🟠 | Partiel / dette identifiée |
| 🔴 | Manquant / bloquant |
| ⚠️ | Anomalie ou attention particulière |

---

## 4. Matrice champs par niveau

### 4.1 Section 4.1 — Organisation (cible 16 champs, repo actuel ~6, gap P0)

**Fichier modèle** : `backend/models/organisation.py`

| # | Champ | Type | Crit. | Source | Notes |
|---|---|---|---|---|---|
| 1 | `id` | int PK | 🔴 P0 | inferred | Auto |
| 2 | `nom_commercial` | str(255) | 🔴 P0 | user_manual | Existe |
| 3 | `siren_principal` | str(9) | 🔴 P0 | user_manual + api_gov | À enrichir validation Sirène |
| 4 | `type_client` | enum | 🟠 P1 | user_manual | Existe |
| 5 | `actif` | bool | 🟠 P1 | inferred | Existe |
| 6 | `is_demo` | bool | 🟠 P1 | inferred | Existe |
| 7 | `logo_url` | str | 🟡 P2 | user_manual | Existe |
| 8 | `tva_intra` | str(20) | 🟠 P1 | user_manual + api_gov | **Manquant** |
| 9 | `code_naf_principal` | str(5) | 🟠 P1 | api_gov | **Manquant** |
| 10 | `pays` | str(2) ISO | 🟠 P1 | user_manual | **Manquant** (default FR) |
| 11 | `secteur` | enum | 🟡 P2 | inferred (NAF) | **Manquant** |
| 12 | `effectif_total` | int | 🟡 P2 | user_manual + Sirène | **Manquant** |
| 13 | `chiffre_affaires_eur` | EurAmount(B) | 🟡 P2 | user_manual + Sirène | **Manquant** |
| 14 | `consentement_dataconnect_global` | bool | 🔴 P0 | user_manual explicit | **Manquant** — Section 6 cascade |
| 15 | `consentement_grdf_global` | bool | 🔴 P0 | user_manual explicit | **Manquant** — Section 6 cascade |
| 16 | `consentement_*_date_signature` | datetime | 🟠 P1 | inferred | **Manquant** — audit RGPD |

**Gaps prioritaires** : 14, 15, 16 (consentements cascade), 8-13 (enrichissement Sirène).

### 4.2 Section 4.2 — Entité juridique (cible 22 champs, hors Audit SMÉ qui reste table séparée — D2)

**Fichier modèle** : `backend/models/entite_juridique.py`

⚠️ **Décision D2 actée** : Audit SMÉ reste dans table dédiée `models/audit_sme.py` (NOT colonnes EJ). Cible Section 4.2 réduite à 22 champs.

| # | Champ | Type | Crit. | Source | Notes |
|---|---|---|---|---|---|
| 1 | `id` | int PK | 🔴 P0 | inferred | |
| 2 | `organisation_id` | int FK | 🔴 P0 | inferred | |
| 3 | `nom_juridique` | str(255) | 🔴 P0 | user_manual + api_gov | |
| 4 | `siren` | str(9) UNIQUE | 🔴 P0 | user_manual + api_gov | Index unique global |
| 5 | `siret` | str(14) | 🔴 P0 | user_manual + api_gov | |
| 6 | `naf_code` | str(5) | 🔴 P0 | api_gov | |
| 7 | `region_code` | str(3) | 🟠 P1 | api_gov | |
| 8 | `insee_code` | str(5) | 🟠 P1 | api_gov | |
| 9 | `adresse_siege` | str(500) | 🟠 P1 | user_manual + api_gov | **Manquant** |
| 10 | `code_postal_siege` | str(5) | 🟠 P1 | user_manual + api_gov | **Manquant** |
| 11 | `commune_siege` | str(100) | 🟠 P1 | user_manual + api_gov | **Manquant** |
| 12 | `pays` | str(2) | 🟠 P1 | user_manual | **Manquant** |
| 13 | `telephone` | str(30) | 🟡 P2 | user_manual | **Manquant** |
| 14 | `email_contact` | str | 🟡 P2 | user_manual | **Manquant** |
| 15 | `site_web` | str | 🟡 P2 | user_manual | **Manquant** |
| 16 | `effectif_etp` | int | 🟠 P1 | user_manual + Sirène | **Manquant** — déclencheur Audit SMÉ |
| 17 | `chiffre_affaires_eur` | EurAmount(B) | 🟠 P1 | Sirène | **Manquant** — déclencheur Audit SMÉ |
| 18 | `consommation_annuelle_moyenne_3y_gwh` | float | 🔴 P0 | inferred (factures) | **Manquant** — déclencheur Audit SMÉ |
| 19 | `type_societe` | enum | 🟡 P2 | api_gov | **Manquant** |
| 20 | `date_creation_societe` | date | 🟡 P2 | api_gov | **Manquant** |
| 21 | `capital_social_eur` | EurAmount(B) | 🟡 P2 | api_gov | **Manquant** |
| 22 | `representant_legal_nom` | str(255) | 🟡 P2 | user_manual | **Manquant** |

**Note D2** : la table `models/audit_sme.py` (63 L) traite : `audit_sme_assujetti`, `audit_sme_seuil_gwh`, `audit_sme_deadline`, `audit_sme_statut`, `audit_sme_organisme_certifie`, `iso_50001_certifie`, `last_audit_date`, `prochain_audit_date`. Cycle de vie propre (audit tous les 4 ans).

**Gaps prioritaires** : 18 (déclencheur SMÉ critique), 16-17 (effectif + CA), 9-15 (adresse complète).

### 4.3 Section 4.3 — Portefeuille (cible 11 champs, repo actuel ~4)

**Fichier modèle** : `backend/models/portefeuille.py`

| # | Champ | Type | Crit. | Source | Notes |
|---|---|---|---|---|---|
| 1 | `id` | int PK | 🔴 P0 | inferred | |
| 2 | `entite_juridique_id` | int FK | 🔴 P0 | inferred | |
| 3 | `nom` | str(255) | 🔴 P0 | user_manual ou auto | "Principal" si auto-créé |
| 4 | `description` | str | 🟡 P2 | user_manual | |
| 5 | `created_at`, `updated_at`, `deleted_at` | datetime | 🟠 P1 | inferred | Mixins existants |
| 6 | `responsable_id` | int FK User | 🟠 P1 | user_manual | **Manquant** |
| 7 | `couleur_ui` | str(7) hex | 🟡 P2 | user_manual | **Manquant** |
| 8 | `tags` | JSON | 🟡 P2 | user_manual | **Manquant** |
| 9 | `actif` | bool | 🟠 P1 | inferred | **Manquant** |
| 10 | `code_interne` | str(50) | 🟡 P2 | user_manual | **Manquant** |
| 11 | `notes` | text | 🟡 P2 | user_manual | **Manquant** |

### 4.4 Section 4.4 — Site (cible 67 champs après ajustement OPERAT/APER/EFA, repo ~35, gap critique 12 OPERAT + 5 APER + 1 EFA)

**Fichier modèle** : `backend/models/site.py` (150 L actuelles → ~250 L cible)

⚠️ **Décision D3 actée** : BACS détaillés restent dans tables `bacs_models.py` séparées. Site garde uniquement les champs BACS d'identification (assujetti, deadline, classe, puissance CVC).

#### 4.4.A — Identité et adresse (15 champs, ✅ majoritairement présents)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 1 | `id` | int PK | 🔴 P0 | inferred | ✅ |
| 2 | `portefeuille_id` | int FK | 🔴 P0 | inferred | ✅ |
| 3 | `nom_site` | str(255) | 🔴 P0 | user_manual | ✅ |
| 4 | `type_site` | enum | 🟠 P1 | user_manual | ✅ |
| 5 | `actif` | bool | 🟠 P1 | inferred | ✅ |
| 6 | `is_demo` | bool | 🟠 P1 | inferred | ✅ |
| 7 | `adresse` | str(500) | 🔴 P0 | user_manual + api_gov | ✅ |
| 8 | `code_postal` | str(5) | 🔴 P0 | user_manual + api_gov | ✅ |
| 9 | `commune` | str(100) | 🔴 P0 | user_manual + api_gov | ✅ |
| 10 | `region_code` | str(3) | 🟠 P1 | api_gov | ✅ |
| 11 | `latitude` | float | 🟠 P1 | api_gov | ✅ |
| 12 | `longitude` | float | 🟠 P1 | api_gov | ✅ |
| 13 | `geocoding_source` | str | 🟠 P1 | inferred | ✅ |
| 14 | `geocoding_score` | float | 🟡 P2 | inferred | ✅ |
| 15 | `siret_site` | str(14) | 🟠 P1 | user_manual + api_gov | ✅ |

#### 4.4.B — Surfaces et caractéristiques (8 champs)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 16 | `surface_tertiaire_totale_m2` | int | 🔴 P0 | user_manual | ✅ (`tertiaire_area_m2`) |
| 17 | `surface_totale_m2` | int | 🟠 P1 | user_manual | ✅ |
| 18 | `roof_area_m2` | int | 🟠 P1 | user_manual | ✅ |
| 19 | `parking_area_m2` | int | 🟠 P1 | user_manual | ✅ |
| 20 | `parking_type` | enum | 🟠 P1 | user_manual | ✅ |
| 21 | `nombre_employes` | int | 🟡 P2 | user_manual | ✅ |
| 22 | `mode_propriete` | enum | 🔴 P0 | user_manual | ✅ |
| 23 | `is_multi_occupied` | bool | 🟠 P1 | user_manual | ✅ |

#### 4.4.C — OPERAT complet (12 champs, **GAP CRITIQUE — 0 présent**) 🔴

⚠️ **Phase C-1 priorité absolue** : ajout migration Alembic.

| # | Champ | Type | Crit. | Source | Notes |
|---|---|---|---|---|---|
| 24 | `operat_zone_climatique` | enum 13 | 🔴 P0 | inferred (resolver) | H1a..H3 + 5 DOM (annexe III authentifiée 🟢) |
| 25 | `operat_palier_altitude` | enum 5 | 🔴 P0 | inferred (altitude_m) | alt_lt_400 / alt_400_800 / alt_800_1200 / alt_1200_1600 / alt_gte_1600 (palier strict) |
| 26 | `altitude_m` | int | 🔴 P0 | user_manual ou IGN (P2) | Range 0-3000 m |
| 27 | `operat_sous_categorie_id` | str | 🔴 P0 | user_manual | 426 sous-cat possibles (Annexe I VA VI) |
| 28 | `operat_iiu_temporels` | JSON | 🟠 P1 | user_manual | Indicateurs intensité usage temporels |
| 29 | `operat_iiu_surfaciques` | JSON | 🟠 P1 | user_manual | Indicateurs intensité usage surfaciques |
| 30 | `cabs_kwh_m2_an` | float | 🟠 P1 | inferred (service Cabs) | Calculé via OperatValeursAbsoluesService |
| 31 | `crelat_kwh_m2_an` | float | 🟠 P1 | inferred | Crelat 2030 = Cref × (Cabs(n)/Cabs(ref)) × 0.6 |
| 32 | `usage_principal` | enum | 🟠 P1 | user_manual | |
| 33 | `efa_id` | str | 🟠 P1 | user_manual | Identifiant Entité Fonctionnelle Assujettie OPERAT |
| 34 | `annee_reference_operat` | int | 🟠 P1 | user_manual | 2010-2019 (prio) ou 2020/2021/2022 |
| 35 | `methode_modulation_dt` | enum | 🟡 P2 | user_manual | 4 motifs officiels (cout/sante/patrimoine/changement) |
| 36 | `dossier_modulation_id` | str | 🟡 P2 | user_manual | Réf dossier OPERAT modulation |

#### 4.4.D — APER étendu (5 champs, **GAP CRITIQUE — 0 présent**) 🔴

| # | Champ | Type | Crit. | Source | Notes |
|---|---|---|---|---|---|
| 37 | `aper_assujetti` | bool | 🔴 P0 | inferred (parking_area ≥ 1500) | |
| 38 | `aper_categorie_taille` | enum | 🟠 P1 | inferred | small (1500-10000) / large (>10000) |
| 39 | `aper_deadline` | date | 🟠 P1 | inferred | 01/07/2028 (1500-10000) ou 01/07/2026 (>10000) |
| 40 | `parking_solar_pct_engaged` | float | 🟠 P1 | user_manual | Taux solarisation engagé (%) |
| 41 | `aper_exemption_motif` | enum | 🟡 P2 | user_manual | Si exemption (climat / structure / patrimoine) |

#### 4.4.E — BACS d'identification (5 champs, complétés par tables dédiées D3)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 42 | `bacs_assujetti` | bool | 🔴 P0 | inferred | À vérifier (puissance_cvc_totale_kw ≥ 70) |
| 43 | `bacs_puissance_cvc_totale_kw` | float | 🔴 P0 | user_manual | À vérifier présence repo |
| 44 | `bacs_deadline` | date | 🟠 P1 | inferred | 01/01/2025 (>290 kW) ou 01/01/2030 (70-290 kW) |
| 45 | `bacs_classe_actuelle` | enum A/B/C/D | 🟠 P1 | user_manual | À enrichir |
| 46 | `bacs_categorie` | enum | 🟠 P1 | inferred | gros / petit |

**Tables dédiées D3** : `bacs_models.py`, `bacs_regulatory.py`, `bacs_remediation.py` — détails techniques (TRI, zones fonctionnelles, sous-comptage horaire, exemptions).

#### 4.4.F — Conformité snapshots (10 champs, ✅ présents)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 47 | `statut_decret_tertiaire` | enum | 🟠 P1 | inferred | ✅ |
| 48 | `avancement_decret_pct` | float | 🟠 P1 | inferred | ✅ |
| 49 | `statut_bacs` | enum | 🟠 P1 | inferred | ✅ |
| 50 | `anomalie_facture` | bool | 🟠 P1 | inferred | ✅ |
| 51 | `action_recommandee` | str | 🟠 P1 | inferred | ✅ |
| 52 | `risque_financier_euro` | EurAmount(A) | 🟠 P1 | inferred | ✅ |
| 53 | `compliance_score_composite` | float | 🟠 P1 | inferred (V2 adaptatif) | ✅ snapshot mais V1 figée — **REFONTE C-1** |
| 54 | `compliance_score_breakdown_json` | JSON | 🟠 P1 | inferred | ✅ |
| 55 | `compliance_score_confidence` | enum | 🟠 P1 | inferred | ✅ |
| 56 | `intensity_kwh_m2_an` | float | 🟠 P1 | inferred (backend) | **Manquant** — actuellement calculé en frontend (anti-pattern) |

#### 4.4.G — Energy + lineage (6 champs)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 57 | `annual_kwh_total` | float | 🟠 P1 | inferred | ✅ |
| 58 | `last_energy_update_at` | datetime | 🟠 P1 | inferred | ✅ |
| 59 | `archetype_code` | str | 🟡 P2 | user_manual | ✅ |
| 60 | `puissance_pilotable_kw` | float | 🟡 P2 | user_manual | ✅ |
| 61 | `cbam_imports_tonnes` | JSON | 🟡 P2 | user_manual | ✅ différenciateur |
| 62 | `cbam_intensities_tco2_per_t` | JSON | 🟡 P2 | user_manual | ✅ différenciateur |

#### 4.4.H — Lineage et traçabilité (5 champs, ✅ présents)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 63 | `data_source` | enum | 🟠 P1 | inferred | ✅ |
| 64 | `data_source_ref` | str | 🟠 P1 | inferred | ✅ |
| 65 | `imported_at` | datetime | 🟠 P1 | inferred | ✅ |
| 66 | `imported_by` | int FK | 🟠 P1 | inferred | ✅ |
| 67 | `consentement_site_overrides` | JSON | 🔴 P0 | user_manual | **Manquant** — cascade Section 6 |

**Total Section 4.4** : 67 champs cible, ~35 présents = **52% couverture**. Phase C-1 fait passer à 100%.

### 4.5 Section 4.5 — Bâtiment (cible 14 champs hors BACS séparés D3, repo actuel ~6)

**Fichier modèle** : `backend/models/batiment.py` (22 L → ~80 L cible)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 1 | `id`, `site_id`, `nom` | int + FK + str | 🔴 P0 | inferred + user_manual | ✅ |
| 4 | `surface_de_plancher_sdp_m2` | int | 🔴 P0 | user_manual | ✅ (`surface_m2`) |
| 5 | `annee_construction` | int | 🟠 P1 | user_manual | ✅ |
| 6 | `cvc_power_kw` | float | 🟠 P1 | user_manual | ✅ |
| 7 | `rnb_id` | str(50) | 🟠 P1 | api_gov + OPERAT V9.0 | **Manquant** |
| 8 | `siret_batiment` | str(14) | 🟡 P2 | user_manual | **Manquant** |
| 9 | `usage_batiment` | enum | 🟠 P1 | user_manual | **Manquant** |
| 10 | `etage_count` | int | 🟡 P2 | user_manual | **Manquant** |
| 11 | `dpe_grade` | enum A-G | 🟠 P1 | user_manual | **Manquant** |
| 12 | `dpe_date` | date | 🟠 P1 | user_manual | **Manquant** |
| 13 | `dpe_consommation_kwh_m2` | float | 🟠 P1 | user_manual | **Manquant** |
| 14 | `dpe_emissions_kgco2_m2` | float | 🟠 P1 | user_manual | **Manquant** |
| 15 | `efa_operat_id` | str | 🟠 P1 | user_manual | **Manquant** |
| 16 | `parties_communes_pct` | float | 🟡 P2 | user_manual | **Manquant** |
| 17 | `categorie_operat_batiment` | enum | 🟠 P1 | inferred (héritée site) | **Manquant** |

### 4.6 Section 4.6 V2 — Compteur unifié + DeliveryPoint riche (D1 statu quo + Q-final-2)

⚠️ **Décision D1 actée** : modèle `Compteur` unifié (élec/gaz/eau via enum `type`) + `DeliveryPoint` riche pour spécificités. **Sections 4.6/4.7 fusionnées en 4.6 V2** avec sous-sections A/B/C.

#### 4.6.A — Compteur (modèle commun, ~12 champs)

**Fichier modèle** : `backend/models/compteur.py` (60 L)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 1 | `id`, `site_id` | int PK + FK | 🔴 P0 | inferred | ✅ |
| 3 | `type` | enum [ELECTRICITE, GAZ, EAU] | 🔴 P0 | user_manual | ✅ |
| 4 | `numero_serie` | str UNIQUE | 🔴 P0 | user_manual | ✅ |
| 5 | `puissance_souscrite_kw` | float | 🔴 P0 | user_manual / api | ✅ |
| 6 | `meter_id` | str | 🔴 P0 | user_manual | ✅ |
| 7 | `energy_vector` | str | 🟠 P1 | inferred | ✅ |
| 8 | `actif` | bool | 🟠 P1 | inferred | ✅ |
| 9 | `delivery_point_id` | int FK 1:1 | 🔴 P0 | inferred | ✅ |
| 10 | `data_source`, `data_source_ref` | enum + str | 🟠 P1 | inferred | ✅ |
| 11 | `sub_meter_of_id` | int FK self | 🟠 P1 | user_manual | **Manquant** — D6 self-FK |
| 12 | `batiment_id` | int FK | 🟠 P1 | user_manual | À vérifier |

#### 4.6.B — DeliveryPoint élec (PRM, ~18 champs spécifiques)

**Fichier modèle** : `backend/models/patrimoine.py` (DeliveryPoint, ~30 champs total)

⚠️ **Audit Phase B confirme** : DeliveryPoint contient déjà la majorité (PRM/PCE, GRD, ATRD, profil GRDF, HC reprog, lineage). Un index unique global PRM/PCE doit être ajouté (audit anomalie).

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 1 | `code` (PRM 14 chiffres élec) | str(14) | 🔴 P0 | user_manual + api_enedis | ✅ — **AJOUT INDEX UNIQUE GLOBAL P0** |
| 2 | `categorie_turpe` | enum [C2, C4, C5] | 🔴 P0 | api_enedis ou user | ✅ (segment_turpe) |
| 3 | `domaine_tension` | enum [BTINF, BTSUP, HTA] | 🔴 P0 | inferred | ✅ |
| 4 | `code_fta` | enum 15 valeurs TURPE 7 | 🔴 P0 | api_enedis ou user | À vérifier — 4 HTA + 4 BT>36 + 7 BT≤36 |
| 5 | `option_tarifaire` | enum | 🔴 P0 | user_manual | À vérifier |
| 6 | `version_turpe` | enum | 🔴 P0 | fixed_constant | "TURPE_7" depuis 01/08/2025 |
| 7 | `mode_traitement` | enum | 🔴 P0 | inferred | À vérifier |
| 8 | `cdc_pas_temporel_minutes` | int | 🟠 P1 | api_enedis | À vérifier (récupéré dynamiquement, pas hardcodé) |
| 9 | `puissances_souscrites_par_plage` | JSON | 🟠 P1 | user_manual | Si LU |
| 10 | `tan_phi_mesure` | float | 🟠 P1 | api_enedis | Si HTA |
| 11 | `dataconnect_consentement_actif` | bool | 🔴 P0 | inferred (cascade) | **Manquant** |
| 12 | `dataconnect_token_expires_at` | datetime | 🟠 P1 | inferred | À vérifier |
| 13 | `dataconnect_scopes` | JSON | 🟠 P1 | inferred | 4 scopes possibles |
| 14 | `cosphi_target` | float | 🟡 P2 | user_manual | À vérifier |
| 15 | `modulable_kva` | float | 🟡 P2 | user_manual | À vérifier |
| 16 | `accise_categorie` | enum | 🔴 P0 | inferred (CIBS) | MENAGES_ASSIMILES / PME / HAUTE_PUISSANCE |
| 17 | `tarif_reduit_accise_motif` | enum | 🟡 P2 | user_manual | 7 motifs CIBS L.312-48 |
| 18 | `cee_eligible_bat_th_116` | bool | 🟡 P2 | inferred | Si BACS classe ≤ C avant amélioration |

#### 4.6.C — DeliveryPoint gaz (PCE, ~18 champs spécifiques)

| # | Champ | Type | Crit. | Source | Statut |
|---|---|---|---|---|---|
| 1 | `code` (PCE) | str regex `^(\d{14}\|GI\d{6}\|IR\d{4})$` | 🔴 P0 | user_manual + api_grdf/api_grtgaz | ✅ — **AJOUT INDEX UNIQUE GLOBAL P0** + **3 formats Phase D-3 Tier 2** |
| 2 | `pce_format` | enum [DISTRIBUTION_14, DISTRIBUTION_GI, TRANSPORT_PIR] | 🔴 P0 | inferred (regex) | ✅ Phase D-3 Tier 2 — matrice v1 corrigée (label `TRANSPORT_GI6` imprécis remplacé). Sources : CRE Délib. 2025-161 du 19/06/2025 (JORFTEXT000051807406) + smart.grtgaz.com (URLs publiques PIR `IR0011`, `IR0015`, `IR0053`). PCE GI = distribution gros industriel GRDF (PAS transport). PCE transport = PIR `IR\d{4}` (PAS `LI\d{4}` ni `GI\d{6}`). |
| 3 | `type_reseau` | enum [DISTRIBUTION, TRANSPORT] | 🔴 P0 | inferred | À vérifier |
| 4 | `gestionnaire_reseau` | enum [GRDF + 21 ELD + NaTran + Teréga] | 🔴 P0 | user_manual | À vérifier (eld_gaz_referentiel.yaml manquant) |
| 5 | `referentiel_tarifaire` | enum [ATRD, ATRT] | 🔴 P0 | inferred (type_reseau) | À vérifier |
| 6 | `est_profile` | bool | 🔴 P0 | inferred (classe_tarifaire) | T1/T2/T3 = profilé, T4/TP = non-profilé |
| 7 | `classe_tarifaire` | enum [T1, T2, T3, T4, TP] | 🔴 P0 | user_manual ou inferred (conso) | À vérifier |
| 8 | `mode_releve` | enum [MM, MJ, JJ, MH] | 🔴 P0 | user_manual | À vérifier |
| 9 | `profil_consommation_code` | enum P011-P019 | 🟠 P1 | user_manual | Conditionnel (si profilé) |
| 10 | `cjn_kwh_jour` | float | 🟠 P1 | inferred | CJN = AI × coeff_max(profil, ZI) — auto si profilé |
| 11 | `cja_kwh_jour` | float | 🟠 P1 | user_manual | Conditionnel (si non-profilé T4/TP) |
| 12 | `car_kwh_an` | float | 🟠 P1 | inferred | CAR = conso_365j × TCC |
| 13 | `pcs_kwh_par_nm3` | float | 🟠 P1 | api_grdf | Pouvoir Calorifique Supérieur |
| 14 | `zone_implantation` | enum | 🟠 P1 | api_grdf | Pour CJN profil |
| 15 | `pitd_code` | str | 🟠 P1 | api_grdf | Point Interface Transport Distribution |
| 16 | `adict_consentement_actif` | bool | 🔴 P0 | inferred (cascade) | **Manquant** |
| 17 | `adict_token_expires_at` | datetime | 🟠 P1 | inferred | |
| 18 | `accise_categorie_gaz` | enum | 🔴 P0 | inferred (CIBS) | NATUREL / GPL / GNL |

**Note** : DeliveryPoint actuel contient `grd_code, atrd_option, car_kwh, gas_profile, cjn/cja, segment TURPE, hc_reprog` → **majorité présente**, à compléter consentement cascade + index unique global.

### 4.7 Section 4.7 — Sous-compteur (D6 self-FK)

⚠️ **Décision D6 actée** : pas de modèle `sous_compteur.py` dédié. Utilisation du champ `Compteur.sub_meter_of_id` self-FK + discriminator type.

**Champs additionnels Compteur** :

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `sub_meter_of_id` | int FK self nullable | 🟠 P1 | user_manual |
| 2 | `usage_principal` | enum [CVC, ECLAIRAGE, IT, PROCESS, ECS, AUTRE] | 🟠 P1 | user_manual |
| 3 | `mode_remontee` | enum [MANUAL, IOT, GTB_MODBUS, CSV] | 🟠 P1 | user_manual |
| 4 | `contribution_estimee_pct` | float | 🟡 P2 | user_manual |

### 4.8 Section 4.8 — Contrat V2 (D4 statu quo, modèle plus riche que matrice)

⚠️ **Décision D4 actée** : on conserve `contract_v2_models.py` (426 L). Matrice adaptée à V2.

**Fichier modèle** : `backend/models/contract_v2_models.py`

#### 4.8.A — ContratCadre (~10 champs)

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `id`, `entite_juridique_id` | int + FK | 🔴 P0 | inferred |
| 3 | `numero_contrat_cadre` | str UNIQUE | 🔴 P0 | user_manual |
| 4 | `type_energie` | enum [ELEC, GAZ] | 🔴 P0 | user_manual |
| 5 | `fournisseur_nom` | str + autocomplete CRE | 🔴 P0 | user_manual |
| 6 | `date_signature` | date | 🟠 P1 | user_manual |
| 7 | `date_debut_validite` | date | 🔴 P0 | user_manual |
| 8 | `date_fin_validite` | date | 🔴 P0 | user_manual |
| 9 | `type_offre` | enum 7 valeurs | 🔴 P0 | user_manual |
| 10 | `statut` | enum [BROUILLON, ACTIF, ECHU, RESILIE] | 🟠 P1 | inferred |

#### 4.8.B — AnnexeSite (~6 champs)

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `id`, `contrat_cadre_id`, `site_id` | int + 2 FK | 🔴 P0 | inferred |
| 4 | `date_debut_local` | date | 🔴 P0 | user_manual |
| 5 | `date_fin_local` | date | 🔴 P0 | user_manual |
| 6 | `volume_engagement_kwh` | float | 🟠 P1 | user_manual |

#### 4.8.C — ContractPricing (~8 champs)

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `id`, `contrat_cadre_id` ou `annexe_site_id` | int + FK | 🔴 P0 | inferred |
| 3 | `prix_part_energie_eur_mwh` | EurAmount(B) | 🔴 P0 | user_manual ou ocr_invoice |
| 4 | `formule_indexation` | str ou JSON | 🟠 P1 | user_manual |
| 5 | `indice_reference` | enum [EEX_BASE, EEX_PEAK, PEG, ...] | 🟠 P1 | user_manual |
| 6 | `cjs_gaz_t3_t4` | float | 🟠 P1 | user_manual |
| 7 | `tarif_reduit_accise_eur_mwh` | EurAmount(A) | 🟡 P2 | inferred |
| 8 | `tarif_reduit_accise_motif_cibs` | enum 7 motifs | 🟡 P2 | user_manual |

#### 4.8.D — VolumeCommitments (~4 champs)

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `volume_min_engage_mwh` | float | 🟠 P1 | user_manual |
| 2 | `volume_max_engage_mwh` | float | 🟠 P1 | user_manual |
| 3 | `tolerance_pct` | float | 🟡 P2 | user_manual |
| 4 | `penalite_hors_engagement_eur_mwh` | EurAmount(B) | 🟡 P2 | user_manual |

#### 4.8.E — ContractEvents (~4 champs)

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `id`, `contrat_cadre_id` | int + FK | 🔴 P0 | inferred |
| 3 | `event_type` | enum [SIGNATURE, AVENANT, RESILIATION, RENOUVELLEMENT] | 🔴 P0 | inferred |
| 4 | `event_date` | datetime | 🔴 P0 | inferred |

#### 4.8.F — ContractDeliveryPoint (D5 — N:N)

⚠️ **Décision D5 actée** : `ContractDeliveryPoint` (existant) **remplace** `ContratCompteurLink` théorique de la matrice cible.

| # | Champ | Type | Crit. | Source |
|---|---|---|---|---|
| 1 | `contrat_cadre_id` | int FK | 🔴 P0 | inferred |
| 2 | `delivery_point_id` | int FK | 🔴 P0 | inferred |
| 3 | `prix_specifique_site_eur_mwh` | EurAmount(B) nullable | 🟡 P2 | user_manual |
| 4 | `created_at`, `updated_at` | datetime | 🟠 P1 | inferred |

**Index** : UniqueConstraint(contrat_cadre_id, delivery_point_id) — ✅ existant.

---

## 5. OPERAT — Tables CVCi/USEi/IIU + zones authentifiées

### 5.1 Sources de référence

| Composant | Source officielle | Statut PROMEOS |
|---|---|---|
| **Annexe I** (CVCi/USEi/IIU/Modulation) | Arrêté 01/08/2025 NOR `ATDL2430864A` annexe I (217 pages, consolide VA I→V) | ✅ `operat_annexe_i_sous_categories.json` (1115 KB, 426 sous-cat) |
| **Annexe II** (Coeff DJU) | Idem annexe II (3 pages, 13 groupes) | ✅ `operat_annexe_ii_coeff_dju.json` (11 KB) |
| **Zones climatiques** | Annexe III arrêté 10/04/2020 NOR `LOGL2005904A` (consolidée 07/09/2025) | ✅ `operat_zones_climatiques.json` (101 entités, schema 2.0) |
| **Stations météo** | Idem (Annexe III, 165 stations) | ✅ `operat_stations_meteo.json` |
| **PDF archivés** | Légifrance v2 + Bulletin officiel | ✅ `docs/sources/regulatory/operat/` |

**Confidence globale** : 🟢 (zones authentifiées par recoupement direct annexe III v2 du 03/05/2026).

### 5.2 Architecture stockage

```
backend/config/
├── operat_valeurs_absolues.yaml          [SoT métadonnées + chronologie + sanctions, schema 0.9]
├── operat_annexe_i_sous_categories.json  [931 KB — 426 sous-cat × 13 zones × 5 paliers]
├── operat_annexe_ii_coeff_dju.json       [10 KB — 13 groupes Coeff_ch/Coeff_fr]
├── operat_zones_climatiques.json         [6 KB — 101 entités schema 2.0]
└── operat_stations_meteo.json            [33 KB — 165 stations]
```

### 5.3 Service backend cible

**Fichier** : `backend/regops/services/operat_cabs_service.py` (**À CRÉER** Sprint C-1)

```python
class OperatValeursAbsoluesService:
    """SoT pour valeurs absolues OPERAT.
    Chaîne complète : code_postal → zone → palier → CVCi → Cabs 2030.
    """
    def resolve_zone(code_postal: str) -> Optional[str]: ...
    def resolve_palier_altitude(altitude_m: float) -> str: ...
    def get_cvci_usei(sous_cat: str, zone: str, palier: str) -> dict: ...
    def get_coeff_dju(sous_cat: str) -> dict: ...
    def compute_cabs_2030(site, sous_cats_declared, dju_site, dju_etalon) -> dict: ...
```

### 5.4 Mapping zones authentifié (extrait — diffère de RT 2012 sur ~25 dépts)

| Zone | Description | Nb dépts | Différences notables vs RT 2012 |
|---|---|---|---|
| H1a | Bassin parisien + Hauts-de-France + Normandie + Aisne | 18 | Strasbourg/Metz/Reims passent en H1b |
| H1b | Continental nord-est + Bourgogne nord + Loiret | 15 | Inclut Grand Est complet (08, 67, 68, 90...) |
| H1c | Continental moyen-sud + Massif Central + Auvergne | 18 | Inclut Limousin (19, 23, 87) et Hautes-Alpes (05) |
| H2a | Bretagne + Manche | 5 | |
| H2b | Pays de la Loire + Centre + Poitou-Charentes + Mayenne | 13 | Mayenne passe en H2b |
| H2c | Sud-Ouest atlantique + Pyrénées + Toulouse + sud Massif Central | 13 | Toulouse passe en H2c |
| H2d | Vallée du Rhône + Provence intérieure + Lozère + Vaucluse | 5 | Vaucluse passe en H2d |
| H3 | Méditerranée + Corse | 9 | |

### 5.5 Tooltip traçabilité PROMEOS (différenciateur)

```
┌─────────────────────────────────────────┐
│ Cabs 2030 : 91 kWh/m²/an                │
├─────────────────────────────────────────┤
│ 📍 Zone : H1b (Bassin parisien)        │
│    Palier : altitude < 400 m            │
│ 🏢 Sous-cat : Crèche (88.91A)          │
│ ⚙️ CVC étalon : 66 + USE étalon : 25   │
│    Coeff DJU G2 (0,000314 ; 0,0000535)  │
│ 📜 NOR ATDL2430864A (01/08/2025)       │
│ ℹ️ Zonage OPERAT ≠ RT 2012 (annexe III) │
└─────────────────────────────────────────┘
```

### 5.6 Limites résiduelles

| ID | Limite | Plan |
|---|---|---|
| L1 | NOR exacts VA I-V manquants (consolidés dans VA VI mais utiles audit) | P2 — délégation regulatory-expert |
| L3 | 63 catégories texte vs 60 sommaire | À documenter |
| L4 | 19 cas pratiques Cerema 🟡 vs Annexe I officielle | P2 — sondage 5 sous-cat |
| L5 | iiu_block_raw tronqué 2000 chars (data centers/hôpitaux) | À surveiller wiring |
| L7 | Mapping commune → altitude IGN non implémenté | P2 — ADMIN-EXPRESS |
| L8 | UX RT 2012 vs OPERAT (~25 dépts) | P1 — tooltip explicatif obligatoire |

---

## 6. Matrices transverses

### 6.1 Cascade consentements (Org → Site → Compteur)

#### 6.1.A DataConnect (élec)

```
Org.consentement_dataconnect_global               [Section 4.1, P0]
       ↓
Site.consentement_dataconnect_site                 [Section 4.4 enum 3 valeurs]
  ├── "herite_entite" → hérite Org
  ├── "accepte_local" → surcharge OK local
  └── "refuse_local" → surcharge KO local
       ↓
DeliveryPoint.dataconnect_consentement_actif       [Section 4.6.B, calculé auto]
```

#### 6.1.B ADICT (gaz GRDF)

Strictement parallèle DataConnect, sauf court-circuit `gestionnaire_reseau != GRDF` ou `type_reseau == TRANSPORT` → ADICT inapplicable.

### 6.2 Compliance score adaptatif V2 (correction H6.5)

⚠️ **GAP CRITIQUE C-1** : refonte `compliance_score_service.py` V1 → V2.

**Principe V2** : pondération relative recalculée à 100% sur les obligations réellement applicables.

| Périmètre | Pondération recalculée |
|---|---|
| 0 obligation | label `NON_APPLICABLE` (pas de score) + vigilance proactive |
| DT seul | DT 100% |
| DT + BACS | DT 60% / BACS 40% |
| DT + BACS + APER (standard) | DT 45% / BACS 30% / APER 25% |
| DT + BACS + APER + AUDIT_SME | DT 39% / BACS 26% / APER 22% / AUDIT 13% |
| DT + BACS + APER + ISO_50001 | DT 38% / BACS 25% / APER 21% / ISO 17% |
| 6 dimensions (incl SOLAR) | recalcul auto à 100% |

### 6.3 Cohérence agrégats (A1-A10)

| ID | Niveau | Contrainte | Tolérance | Type |
|---|---|---|---|---|
| A1 | Site / Bâtiment | Σ(SDP bâtiments) ≤ surface_tertiaire_site | 5% | Warning |
| A2 | Site / Bâtiment | Σ(emprise_au_sol) ≤ surface foncière | 0% | Warning |
| A3 | Bâtiment | SDP ≤ SUB × 1.15 | 0% | Validation |
| A4 | Compteur / Sous-compteur | Σ(conso sous-compteurs) ≤ conso compteur principal | 5% | Warning |
| A5 | Compteur / Sous-compteur | Σ(contribution_estimee_pct) ≤ 105% | 5% | Warning |
| **A6** | Site / Compteur / Contrat | Σ(conso compteurs) ↔ Σ(conso contrats) | **1%** | **🔴 Bloquant Bill Intelligence** |
| A7 | Entité juridique / Site | Σ(conso sites entité) = `consommation_annuelle_moyenne_3y_gwh` | 5% | Calcul système |
| A8 | Org / Entité | Pas de contrainte | – | – |
| A9 | Site / Bâtiment | Catégorie OPERAT bâtiment ⊆ catégorie site (sauf MIXTE) | 0% | Bloquant |
| A10 | Site / Bâtiment | Σ(surface bâtiments par sous-catégorie) = répartition site MIXTE | 2% | Validation |

### 6.4 Indicateurs cross-niveau

| Indicateur | Source SoT | Niveaux drill-down |
|---|---|---|
| Compliance score adaptatif | `compliance_score_service.py` V2 | Portefeuille / Site |
| Intensité kWh/m² | `intensity_kwh_m2_an` (Site) calculé backend (PAS frontend) | Portefeuille / Site / Bâtiment |
| Trajectoire DT (Cabs/Crelat) | `OperatValeursAbsoluesService` | Site / EFA |
| Score CO₂ | ADEME V23.6 (élec 0.052 / gaz 0.227 / GNL 0.238) | Site / Portefeuille |
| Couverture sous-comptage | calc backend | Site / Bâtiment |

### 6.5 Règles temporelles

- **C123** : pas chevauchement contrats sur même DeliveryPoint (bloquant)
- **TURPE versionné rétroactif** : Bill Intel applique version active à la date facture
- **SitePortefeuilleHistory** : table dédiée avec valid_from/valid_to (**À CRÉER** C-2)
- **EFA OPERAT succession** : lien `efa_predecesseure_id` (Section 5)
- **ContractEvents** : audit historique modifications contrat (✅ V2)

### 6.6 Onboarding 3 parcours bifurqués (correction H6.10)

⚠️ **GAP C-5** : actuellement parcours unique 7 étapes (`PatrimoineWizard.jsx`).

**Cible 3 modes** :
- **Standard (Wizard)** : non-sachants, guidé, tooltips actifs, defaults intelligents
- **Expert** : tous champs visibles, raccourcis clavier, affichage technique
- **Bulk** : import CSV/Excel/API, validation batch, idéal grandes structures

**KPIs cibles** :
| KPI | Sachant | Non-sachant |
|---|---|---|
| Time-to-first-value | < 2 min | < 5 min |
| Time-to-completion (10 sites) | < 15 min | < 30 min |
| Champs P0 / P0 requis | 100% | ≥ 90% |
| Taux abandon | < 5% | < 15% |

### 6.7 Source-guards transverses (anti hard-code)

Tests à activer en CI (réparation workflow C-1) :
- `test_no_hardcoded_regulatory_constants.py` (0.052, 0.227, 7500, 12.41, 499.80, etc.)
- `test_cascade_resolution.py` (Org → Site → Compteur)
- `test_compliance_score_adaptive.py` (cas 0 → N obligations)
- `test_operat_zones_authentifiees.py` (vs RT 2012)

---

## 7. Sources réglementaires (16 blocs N1-N5)

### 7.1 Architecture stockage

**Fichier** : `backend/config/sources_reglementaires.yaml` (**À CRÉER** C-3)

### 7.2 Vue récap blocs

| Bloc | Thème | Criticité | Fréquence revue |
|---|---|---|---|
| 1 | DT/OPERAT (NOR `ATDL2430864A` SoT, série VA I→VI) | 🔴 P0 | Trimestrielle |
| 2 | BACS (décrets 2020-887, 2023-259, 2025-1343) | 🔴 P0 | Semestrielle |
| 3 | APER (Loi 2023-175 + décret 2024-1023) | 🟠 P1 | Annuelle |
| 4 | Solarisation (CCH L.171-4 + décret 18/12/2023) | 🟠 P1 | Annuelle |
| 5 | Audit SMÉ (Loi DDADUE 2025-391) — deadline 11/10/2026 critique | 🔴 P0 | Trimestrielle |
| 6 | TURPE 7 (Délibération CRE 2025-78) | 🔴 P0 | Annuelle (01/08) |
| 7 | ATRD/ATRT | 🟠 P1 | Annuelle |
| 8 | Accises CIBS (L.312-24/36/37/48) | 🔴 P0 | Annuelle (01/02) |
| 9 | CTA / TVA / VNU | 🟠 P1 | Annuelle |
| 10 | NEBCO / Autoconsommation collective | 🟡 P2 | Semestrielle |
| 11 | CO₂ ADEME V23.6 + GNL | 🟠 P1 | Annuelle |
| 12 | BEGES (sanctions 50000/100000 €) | 🟡 P2 | Annuelle |
| 13 | Zones climatiques (annexe III LOGL2005904A v2 03/05/2026) | 🔴 P0 | Annuelle |
| 14 | Référentiels tiers (DataConnect, ADICT, RNB, IGN, Sirène) | 🟠 P1 | Continu |
| 15 | Indices marché (EEX, PEG) | 🟢 P3 | Continu |
| 16 | Référentiels typologies (OID, ARSEG, Perifem, UMIH, etc.) | 🟢 P3 | Annuelle |

### 7.3 Constants inviolables (extrait `backend/doctrine/constants.py`)

```python
# ── CO₂ ADEME V23.6 + GNL (arrêté 01/08/2025) ──
CO2_ELEC_KGCO2_KWH = 0.052
CO2_GAZ_NATUREL_KGCO2_KWH = 0.227
CO2_GNL_KGCO2_KWH = 0.238  # ← À AJOUTER C-1

# ⚠️ 0.0569 = TURPE 7 HPH €/kWh — JAMAIS un facteur CO₂

# ── Coeff énergie primaire élec ──
COEFF_ENERGIE_PRIMAIRE_ELEC = 1.9  # depuis Jan 2026

# ── DT pénalités ──
DT_PENALTY_PER_BUILDING_EUR = 7500
DT_PENALTY_PER_M2_OVER_2000 = 150
DT_THRESHOLD_M2 = 1000

# ── BACS seuils + deadlines ──
BACS_SEUIL_BAS_KW = 70
BACS_SEUIL_HAUT_KW = 290
BACS_DEADLINE_70_290 = "2030-01-01"  # décret 2025-1343 REPORT
BACS_DEADLINE_SUP_290 = "2025-01-01"
BACS_TRI_SEUIL_ANS = 10

# ── Audit SMÉ + ISO 50001 ──
AUDIT_SME_THRESHOLD_GWH = 2.75
ISO_50001_THRESHOLD_GWH = 23.6
AUDIT_SME_DEADLINE = "2026-10-11"
ISO_50001_DEADLINE = "2027-10-11"
CPE_DISPENSE_PCT = 80

# ── TURPE 7 (CRE 2025-78) ──
TURPE_VERSION_ACTUELLE = "TURPE_7"
TURPE_DATE_ENTREE = "2025-08-01"
CMDPS_BTSUP_EUR_HEURE = 12.41  # ⚠️ pas 12.65 (mémoire pré-vérification)

# ── Accises CIBS (01/02/2026) ──
ACCISE_ELEC_MENAGES_T1_EUR_MWH = 30.85
ACCISE_ELEC_PME_T2 = 26.58
ACCISE_GAZ_NATUREL = 16.39
MAJORATION_ZNI = 5.66

# ── APER ──
APER_SEUIL_M2 = 1500
APER_SEUIL_HAUT_M2 = 10000
APER_DEADLINE_GT_10000 = "2026-07-01"
APER_DEADLINE_1500_10000 = "2028-07-01"

# ── Solarisation toiture ──
SOLAR_SEUIL_M2 = 500
SOLAR_TAUX_30PCT_DEPUIS = "2019-11-10"
SOLAR_TAUX_40PCT_DEPUIS = "2026-07-01"
SOLAR_TAUX_50PCT_DEPUIS = "2027-07-01"

# ── BEGES sanctions ──
BEGES_AMENDE_DEFAUT = 50000
BEGES_AMENDE_AGGRAVEE = 100000
```

---

## 8. Cohérence globale

### 8.1 Architecture stockage

**Fichier** : `backend/config/coherence_globale.yaml` (**À CRÉER** C-3)

### 8.2 Registre règles cohérence

- ~155 contraintes C1-C155 indexées par section
- 10 contraintes agrégats A1-A10
- ~50 cas spéciaux

### 8.3 Top 20 contraintes bloquantes critiques

| ID | Section | Règle | Impact si violée |
|---|---|---|---|
| C1/C123 | 2 / 4.8 | Pas chevauchement contrats sur même DeliveryPoint | Bill Intelligence cassé |
| C9/A9 | 2 | Catégorie OPERAT bâtiment ⊆ catégorie site (sauf MIXTE) | Cabs faux |
| C10 | 4.1 | SIREN unique global | Identité cassée |
| C39 | 4.4 | Si DT assujetti → année référence ∈ [2010,2019] ou 2020-2022 | Trajectoire DT impossible |
| C50 | 4.5 | Nom bâtiment unique par site | UI cassée |
| C56 | 4.5 | annee_renovation_lourde ≥ annee_construction | Historique illogique |
| **C60** | **4.6.B** | **PRM unique global** | **Lien Enedis cassé — INDEX UNIQUE À AJOUTER** |
| C61-63 | 4.6.B | Catégorie TURPE ⟺ domaine tension (équivalence stricte) | Calcul TURPE faux |
| C64 | 4.6.B | FTA cohérent catégorie TURPE 7 | Bill Intelligence cassé |
| C66 | 4.6.B | Si C2/C4 → phasage = triphase forcé | Calcul puissance faux |
| C67 | 4.6.B | Si CDC ou MIXTE → cdc_pas_temporel_minutes requis | Granularité indéterminée |
| **C85** | **4.6.C** | **PCE unique global** | **Lien GRD cassé — INDEX UNIQUE À AJOUTER** |
| C89-90 | 4.6.C | Type réseau ⟺ gestionnaire (DISTRIBUTION/TRANSPORT) | Référentiel tarifaire faux |
| C95 | 4.6.C | Si profilé → profil P011-P019 requis | Estimation conso impossible |
| C97 | 4.6.C | Si non-profilé → CJA saisie obligatoire | Tarif T4/TP indéterminé |
| C108 | 4.8.A | date_fin_validite > date_debut_validite | Période contractuelle illogique |
| C111-114 | 4.8.C | Type offre ⟺ structure prix (JSON ou float) | Calcul facture impossible |
| **A6** | 6.3 | Σ(conso compteurs) ↔ Σ(conso contrats) tolérance 1% | Bill Intelligence cassé |
| C145 | 6.1 | DeliveryPoint dataconnect_actif ⟺ cascade résout true | Sécurité cassée |

### 8.4 Cascade recompute (10 champs critiques — **C-1 service À CRÉER**)

| Champ modifié | Sections impactées | Recalcul |
|---|---|---|
| `Site.code_postal` | 4.4 zone, 5 CVCi, 6 compliance | Cascade complète OPERAT |
| `Site.altitude_m` | 4.4 palier, 5 CVCi, 6 compliance | Cascade Cabs |
| `Site.surface_tertiaire_totale_m2` | 4.4 DT déclencheur, 5 Cabs, 6 compliance | DT trajectoire complète |
| `Site.bacs_puissance_cvc_totale_kw` | 4.4 BACS, 6 compliance | Score BACS recalculé |
| `Site.parking_area_m2` | 4.4 APER, 6 compliance | Score APER recalculé |
| `Site.categorie_operat_principale` | 4.5 cohérence bâtiments, 5 Cabs | Validation cascade |
| `EJ.consommation_annuelle_moyenne_3y_gwh` | 4.2 Audit SMÉ, 6 compliance dim SME | Score audit SMÉ |
| `Org.consentement_dataconnect_global` | 4.4 cascade Site, 4.6 cascade DeliveryPoint | Cascade descendante |
| `DeliveryPoint.code_fta` | 4.6.B profil, 4.8 Bill Intel | Profil + Bill Intel |
| `Contract.date_fin_validite` | 4.8 renouvellement, 6 alerte 90j | Centre d'action |

---

## 9. Checklist P0 MVP (52 champs absolus, 17% des ~310 modélisés)

### 9.1 Synthèse par niveau

| Niveau | Nb P0 | Champs |
|---|---|---|
| Org | 4 | nom_commercial, siren_principal, consentement_dataconnect_global, consentement_grdf_global |
| Entité | 5 | nom_juridique, siren, siret, naf_code, conso_3y_gwh (auto factures ou saisie) |
| Portefeuille | 1 | (auto-créé "Principal") |
| Site | 10 | nom, adresse, code_postal, commune, operat_zone (auto), altitude_m, palier (auto), surface, categorie_operat, mode_propriete |
| Bâtiment | 4 | (auto-créé "Bâtiment principal" si monobloc) — sinon nom, SDP, categorie, sous_categorie_operat |
| Compteur élec (DeliveryPoint) | 7 | code (PRM), categorie_turpe, domaine_tension (auto), code_fta, version_turpe (auto), mode_traitement, dataconnect_consentement_actif (cascade) |
| Compteur gaz (DeliveryPoint) | 8 | code (PCE), pce_format (auto), type_reseau (auto), gestionnaire, referentiel (auto), est_profile (auto), classe_tarifaire, mode_releve + conditionnel profil P011-P019 OU CJA |
| Sous-compteur | 0-5 (optionnel MVP) | — |
| Contrat (V2) | 8 | entite_juridique_id, numero_contrat_cadre, type_energie, fournisseur, date_debut_validite, date_fin_validite, type_offre, prix_part_energie_eur_mwh |
| **Total** | **52** | **17%** |

### 9.2 Algorithme `is_site_production_ready` (À CRÉER C-2)

```python
def is_site_production_ready(site: Site) -> dict:
    """7 checks : hiérarchie / P0 site / bâtiments P0 / ≥1 compteur / ≥1 contrat / 
       compliance calculable / Cabs calculable (si DT)."""
    checks = {
        'hierarchie': site.entite_juridique and site.entite_juridique.organisation and site.portefeuille,
        'site_p0': all(getattr(site, f) is not None for f in P0_SITE_FIELDS),
        'batiments_p0': any(b.surface_de_plancher_sdp_m2 and b.categorie_operat_batiment for b in site.batiments),
        'au_moins_1_compteur': len(site.compteurs) > 0,
        'au_moins_1_contrat': any(len(c.delivery_point.contracts) > 0 for c in site.compteurs),
        'compliance_score_calculable': service_compliance.calc_score_adaptive(site) is not None,
        'cabs_calculable': not site.dt_assujetti or service_operat.compute_cabs_2030(site) is not None,
    }
    return {
        'production_ready': all(checks.values()),
        'checks': checks,
        'completion_pct': sum(checks.values()) / len(checks) * 100,
        'champs_p0_manquants': _list_missing_p0_fields(site),
    }
```

### 9.3 Endpoint API cible (À CRÉER C-2)

`GET /api/v1/sites/{id}/production-ready-status` → retourne le dict ci-dessus.

---

## 10. Décisions doctrinales (D1-D7)

### D1 — Compteur unifié + DeliveryPoint riche (statu quo) ✅
Modèle `Compteur` unique (élec/gaz/eau via enum) + `DeliveryPoint` (~30 champs) pour spécificités. Sections 4.6/4.7 fusionnées en 4.6 V2 (A/B/C).

### D2 — Audit SMÉ table séparée ✅
`models/audit_sme.py` conservé (cycle de vie propre — audit tous les 4 ans). Section 4.2 réduite à 22 champs.

### D3 — BACS tables séparées ✅
`bacs_models.py` + `bacs_regulatory.py` + `bacs_remediation.py` conservés. Site garde uniquement champs identification (assujetti, deadline, classe, puissance CVC).

### D4 — Contrat V2 (statu quo) ✅
`contract_v2_models.py` (426 L) conservé. Plus riche que matrice théorique (cadre + annexe + pricing + commitments + events).

### D5 — ContractDeliveryPoint (statu quo) ✅
`ContractDeliveryPoint` N:N conservé. Pas de `ContratCompteurLink`.

### D6 — SousCompteur self-FK ✅
Pas de modèle `sous_compteur.py` dédié. Champ `Compteur.sub_meter_of_id` self-FK + discriminator type.

### D7 — Commit matrice v1 ✅
Ce document = matrice v1 officielle. À committer dans `docs/produit/patrimoine_parametrage_requis_v1.md` sur `claude/refonte-sol2`.

---

## 11. Limites connues

| ID | Limite | Plan |
|---|---|---|
| L1 | NOR exacts VA I-V manquants | P2 — `regulatory-expert` |
| L2 | ✅ Mapping département → zone OPERAT (résolu — confidence 🟢) | — |
| L3 | 63 catégories texte vs 60 sommaire | À documenter |
| L4 | 19 cas pratiques Cerema 🟡 vs Annexe I officielle | P2 |
| L5 | iiu_block_raw tronqué 2000 chars | À surveiller |
| L7 | Mapping commune → altitude IGN non implémenté | P2 — saisie manuelle MVP |
| L8 | UX RT 2012 vs OPERAT (~25 dépts) | **P1 tooltip explicatif obligatoire** |
| L9 | ✅ Nuance "La Réunion" vs "Réunion" | Résolue (normalisation service) |
| L7.1 | NOR ATRD 7 + ATRT à confirmer | P1 — `regulatory-expert` |

---

## 12. Plan Phase C (extrait audit Phase B — adapté D1-D6)

| Sprint | Périmètre | Effort | Dépendances |
|---|---|---|---|
| **C-1** | Doctrine + OPERAT cœur (Site OPERAT/APER/EFA fields, OperatValeursAbsoluesService, compliance V2 adaptatif, cascade_recompute_service, source_guards CI réparé, CO2_GNL_KGCO2_KWH ajout) | **18-22 j-h** | aucune |
| **C-2** | Temporalité + FE cleanup (site_portefeuille_history, audit_log_service, endpoint production-ready, retrait calculs `kWh/m²` Patrimoine.jsx, dédup CO2 frontend) | **14-18 j-h** | C-1 |
| **C-3** | Sources + traçabilité (sources_reglementaires.yaml, coherence_globale.yaml, eld_gaz_referentiel.yaml, TraceTooltip FE, migration regulatory_rates.js) | **14-18 j-h** | C-1, C-2 |
| **C-4** | Tests + observabilité (cascade tests, NAF dédupe, correlation_id middleware, .pre-commit-config.yaml, Org/EJ enrichis) | **16-22 j-h** | C-1, C-2, C-3 |
| **C-5** | Onboarding 3 parcours bifurqués (Wizard/Expert/Bulk) + E2E Playwright | **14-18 j-h** | C-2 |
| **C-6** | Modèles enrichis + EFA (EFA model + lien Site/Bâtiment, Bâtiment RNB/DPE/parties_communes, SousCompteur self-FK enriched, Portefeuille tags) | **12-15 j-h** | C-1 |
| **C-7** | UX premium + cleanup (skeletons, ARIA, mobile 380px, ParameterStore TURPE, suppression `routes/patrimoine.py` 0 octet, doc Phase C) | **14-22 j-h** | tous |

**Total estimé** : **102-135 j-h** (~85-120 j-h après économies D1-D6 = 3 migrations annulées).

---

**Fin de la matrice v1.**

🚦 Document à committer sur `claude/refonte-sol2` dans `docs/produit/patrimoine_parametrage_requis_v1.md`. Sprint C-1 démarre immédiatement après.
