# Audit écarts matrice v1 patrimoine paramétrage vs repo (post Phase D-3 Tier 2)

**Date** : 2026-05-07 (livré 2026-05-08 post Phase D-3 Tier 2 commit `042b4f27`)
**Branche** : `claude/refonte-sol2`
**Méthode** : audit READ-ONLY `architect-helios` SDK (Pilier 6 ADR-016 — 6e cycle stable)
**Confidence globale** : HIGH (lecture directe 9 fichiers models cardinaux + matrice v1 951 lignes)
**Verdict global** : 🟢 **80% couverture** matrice v1 (171/212 champs) — 10 P0 + 29 P1 résiduels documentés

---

## 1. Synthèse exécutive

### Résultats cardinaux

- **Couverture globale** : 171/212 champs = **~80%** matrice v1
- **10 P0 résiduels** BLOCK pilote externe complet (~8-12 j-h Phase D-4 Tier 1)
- **29 P1 résiduels** avant pilote externe complet (Tier 2+3)
- **7/7 décisions D1-D7** honorées intégralement post Phase D-3 Tier 2
- **6 imprécisions matrice v1** détectées (au-delà PCE Phase D-3 corrigée)
- **4 bonus repo** non documentés matrice (Site.s_ce_m2, TOUSchedule FK, ContratCadre CEE+capacité+GO, RGPD audit étendu)

### Verdict pilote

| Pilote | Statut |
| --- | --- |
| Interne | ✅ READY (cumul Phase D livré stable) |
| **Investisseur démo** | ✅ **READY consolidé** (80% couverture matrice v1) |
| **Externe complet** | 🟠 **BLOCK Phase D-4 Tier 1** (10 P0 résiduels, ~8-12 j-h) |

---

## 2. Tableau couverture par section

| Section | Cible | Présent | Couverture | P0 résiduels | P1 résiduels |
| --- | --- | --- | --- | --- | --- |
| §4.1 Org | 16 | 16 (+4 RGPD bonus) | **100% ✅** | 0 | 0 |
| §4.2 EntiteJuridique | 22 | 7 | **32% 🔴** | **1** | 6 |
| §4.3 Portefeuille | 11 | 4 | **36% 🟠** | 0 | 2 |
| §4.4 Site | 67 | 60 | **88% 🟢** | **3** | 4 |
| §4.5 Bâtiment | 14 | 9 | **64% 🟠** | 0 | 4 |
| §4.6.A Compteur | 12 | 13 | **108% ✅** | 0 | 1 |
| §4.6.B DP élec | 18 | 14 | **78% 🟢** | **1** | 5 |
| §4.6.C DP gaz | 18 | 9 | **50% 🔴** | **5** | 4 |
| §4.7 Sous-compteur | 4 | 2 | **50%** | 0 | 0 |
| §4.8 Contrat V2 | 30 | 37 | **123% ✅** | 0 | 3 |
| **Total** | **~212** | **~171** | **~80%** | **10** | **29** |

**Hot spots** :
- 🔴 §4.2 EntiteJuridique 32% — déclencheur Audit SMÉ + Sirène round-trip
- 🔴 §4.6.C DP gaz 50% — billing CIBS + routage ATRD/ATRT

---

## 3. Top 10 P0 résiduels cardinaux détaillés

### 🔴 P0-MATV1-001 — `EntiteJuridique.consommation_annuelle_moyenne_3y_gwh`

- **Section** : §4.2#18
- **Type** : float (déductible factures)
- **Justification** : déclencheur **Audit SMÉ deadline 11/10/2026** (sanction 5% CA HT)
- **Cardinal** : sans ce champ, le scoring d'assujettissement Audit SMÉ ne peut pas s'effectuer automatiquement
- **Source** : Loi DDADUE 2025-391 + Décret 2024-1304 + KB confirmé seuils 2.75/23.6 GWh
- **Fichier impact** : `backend/models/entite_juridique.py`

### 🔴 P0-MATV1-002 — `DeliveryPoint.accise_categorie_gaz`

- **Section** : §4.6.C#18
- **Type** : Enum [NATUREL, GPL, GNL]
- **Justification** : bloque **billing gaz CIBS** correctement (taux différents selon catégorie)
- **Cardinal** : actuellement, l'accise gaz 10.73 €/MWh s'applique uniformément sans tenir compte de la catégorie
- **Source** : CIBS L.312-24 + arrêté 27/01/2026 (JORFTEXT000053407616)
- **Fichier impact** : `backend/models/patrimoine.py:DeliveryPoint`

### 🔴 P0-MATV1-003 — `DeliveryPoint.accise_categorie` (élec)

- **Section** : §4.6.B#16
- **Type** : Enum [MENAGES_ASSIMILES, PME, HAUTE_PUISSANCE]
- **Justification** : bloque **billing élec CIBS** (T1=30.85 / T2=26.58 / HP=5.71 selon catégorie)
- **Cardinal** : différentiel ~5-15% sur facture selon catégorie correctement déterminée
- **Source** : CIBS L.312-36/37/48 + arrêté 27/01/2026
- **Fichier impact** : `backend/models/patrimoine.py:DeliveryPoint`

### 🔴 P0-MATV1-004 — `Site.consentement_site_overrides`

- **Section** : §4.4.H#67
- **Type** : JSON
- **Justification** : cascade RGPD §6.1 incomplète — surcharge locale Org → Site (3 valeurs : herite_entite/accepte_local/refuse_local)
- **Cardinal** : actuellement cascade Org → DeliveryPoint directe sans niveau Site intermédiaire
- **Fichier impact** : `backend/models/site.py:Site`

### 🔴 P0-MATV1-005 — `Site.bacs_assujetti` + `bacs_puissance_cvc_totale_kw`

- **Section** : §4.4.E#42-43
- **Type** : bool + float
- **Justification** : score BACS recalcul cascade §8.4 — agrégation Site nécessaire (Σ Bâtiments cvc_power_kw vs seuils 70/290 kW)
- **Cardinal** : actuellement seul `Batiment.cvc_power_kw` existe, pas d'agrégation Site
- **Fichier impact** : `backend/models/site.py:Site`

### 🔴 P0-MATV1-006 — `DeliveryPoint.pce_format` (Enum matérialisé)

- **Section** : §4.6.C#2
- **Type** : Enum [DISTRIBUTION_14, DISTRIBUTION_GI, TRANSPORT_PIR]
- **Justification** : bien que validator regex 3 formats existe Phase D-3 Tier 2, colonne explicite requise audit traçabilité + perf query
- **Décision** : ADR-D-02 candidat (matérialiser vs dériver runtime)
- **Fichier impact** : `backend/models/patrimoine.py:DeliveryPoint`

### 🔴 P0-MATV1-007 — `DeliveryPoint.type_reseau` + `referentiel_tarifaire`

- **Section** : §4.6.C#3 + #5
- **Type** : Enum [DISTRIBUTION/TRANSPORT] + Enum [ATRD/ATRT]
- **Justification** : bloque routage référentiel tarifaire ATRD vs ATRT (déductible via grd_code mais pas matérialisé)
- **Cardinal** : actuellement billing gaz route via heuristique grd_code, pas via champ explicite
- **Fichier impact** : `backend/models/patrimoine.py:DeliveryPoint`

### 🔴 P0-MATV1-008 — `DeliveryPoint.est_profile` + `mode_releve`

- **Section** : §4.6.C#6 + #8
- **Type** : bool + Enum [MM/MJ/JJ/MH]
- **Justification** : `est_profile` détermine sélection algorithme CJN profilé vs T4/TP. `mode_releve` détermine ingestion CDC granularité.
- **Cardinal** : actuellement déductible de `atrd_option` mais pas explicite (T1/T2/T3 = profilé, T4/TP = non-profilé)
- **Fichier impact** : `backend/models/patrimoine.py:DeliveryPoint`

### 🔴 P0-MATV1-009 — `Batiment.categorie_operat_batiment`

- **Section** : §4.5#17
- **Type** : Enum (héritée site avec override possible)
- **Justification** : contrainte agrégat A9 cardinale — catégorie OPERAT bâtiment ⊆ catégorie site (sauf MIXTE)
- **Cardinal** : Cabs faux pour Site MIXTE multi-bâtiments si pas matérialisé
- **Fichier impact** : `backend/models/batiment.py:Batiment`

### 🔴 P0-MATV1-010 — `Compteur.batiment_id` (FK)

- **Section** : §4.6.A#12
- **Type** : Integer FK Batiment.id (nullable)
- **Justification** : bloque agrégation conso par bâtiment (différenciateur PROMEOS pour BACS classe + APER zoning)
- **Décision** : ADR-D-03 candidat (FK ajout cascade analytics)
- **Fichier impact** : `backend/models/compteur.py:Compteur`

---

## 4. 29 P1 résiduels par section

### §4.2 EntiteJuridique (6 P1)

- **P1-MATV1-011** `adresse_siege` (#9 str(500)) — Sirène round-trip
- **P1-MATV1-012** `code_postal_siege` (#10 str(5))
- **P1-MATV1-013** `commune_siege` (#11 str(100))
- **P1-MATV1-014** `pays` (#12 str(2) ISO)
- **P1-MATV1-015** `effectif_etp` (#16 int) — co-déclencheur Audit SMÉ
- **P1-MATV1-016** `chiffre_affaires_eur` (#17 EurAmount(B)) — co-déclencheur Audit SMÉ

### §4.3 Portefeuille (2 P1)

- **P1-MATV1-017** `responsable_id` (#6 FK User)
- **P1-MATV1-018** `actif` (#9 bool)

### §4.4 Site (4 P1)

- **P1-MATV1-019** `bacs_deadline` (§4.4.E#44 date — 01/01/2025 ou 01/01/2030)
- **P1-MATV1-020** `bacs_classe_actuelle` (§4.4.E#45 enum A/B/C/D)
- **P1-MATV1-021** `bacs_categorie` (§4.4.E#46 enum gros/petit)
- **P1-MATV1-022** `intensity_kwh_m2_an` (§4.4.F#56) — ✅ déjà résolu Sprint C-2 (matrice obsolète sur ce point)

### §4.5 Bâtiment (4 P1)

- **P1-MATV1-023** `usage_batiment` (#9 enum)
- **P1-MATV1-024** `dpe_emissions_kgco2_m2` (#14 float) — double étiquette DPE incomplète
- **P1-MATV1-025** `efa_operat_id` (#15 str) — multi-bâtiments multi-EFA
- **P1-MATV1-026** `parties_communes_pct` (#16 float)

### §4.6.A Compteur (1 P1)

- **P1-MATV1-027** `batiment_id` FK (couvert par P0-010 cardinal)

### §4.6.B DP élec (5 P1)

- **P1-MATV1-028** `cdc_pas_temporel_minutes` (#8 int) — bloque CUSUM/forecasting
- **P1-MATV1-029** `puissances_souscrites_par_plage` (#9 JSON pour LU)
- **P1-MATV1-030** `tan_phi_mesure` (#10 float pour HTA)
- **P1-MATV1-031** `dataconnect_token_expires_at` (#12 datetime)
- **P1-MATV1-032** `dataconnect_scopes` (#13 JSON 4 scopes)

### §4.6.C DP gaz (4 P1)

- **P1-MATV1-033** `pcs_kwh_par_nm3` (#13 float api_grdf)
- **P1-MATV1-034** `zone_implantation` (#14 enum)
- **P1-MATV1-035** `pitd_code` (#15 str)
- **P1-MATV1-036** `adict_token_expires_at` (#17 datetime)

### §4.8 Contrat V2 (3 P1)

- **P1-MATV1-037** `formule_indexation` (§4.8.C#4 JSON)
- **P1-MATV1-038** `indice_reference` (§4.8.C#5 Enum EEX_BASE/EEX_PEAK/PEG)
- **P1-MATV1-039** `cjs_gaz_t3_t4` (§4.8.C#6 float)

---

## 5. 6 imprécisions matrice v1 détectées

### 5.1 §4.1#13 `chiffre_affaires_eur` typage

- **Matrice** : `EurAmount(B)`
- **Repo** : `Float`
- **Recommandation** : `Numeric(20,2)` cohérent doctrine pricing (`contract_v2_models.py:Numeric(18,6)`)
- **Confidence** : MEDIUM
- **Action** : à figer Phase D-4 (cosmétique précision financière)

### 5.2 §4.2#22 nombre champs imprécis

- **Matrice** : 22 champs annoncés
- **Réalité** : 21 effectifs (consentements en réalité au niveau Org §4.1, pas EJ)
- **Action** : matrice v1 à corriger (rephrasing §4.2 cible 21 champs)

### 5.3 §4.4#56 `intensity_kwh_m2_an` matrice obsolète

- **Matrice** : "manquant calculé en frontend (anti-pattern)"
- **Réalité** : ✅ résolu Sprint C-2 — `intensity_kwh_m2_total` + `intensity_kwh_m2_tertiaire` persistés backend
- **Action** : matrice v1 à mettre à jour (statut ✅)

### 5.4 §4.4#43 `bacs_puissance_cvc_totale_kw` typage flou

- **Matrice** : `float` (origine non précisée)
- **Question** : Site agrégé `Σ(Batiment.cvc_power_kw)` ou saisie propre ?
- **Décision architecturale** : ADR-D-04 candidat (cascade Σ Batiment)
- **Risque sans ADR** : double SoT possible

### 5.5 §4.6.A#12 `batiment_id` FK Compteur→Batiment

- **Matrice** : "À vérifier"
- **Verdict audit** : **ABSENT du repo**
- **Action** : ADR-D-03 candidat (FK ajout cascade analytics par bâtiment)

### 5.6 §4.6.B#5 `option_tarifaire` divergence sémantique

- **Matrice** : place ce champ au DP
- **Repo** : place sur `ContractAnnexe.tariff_option`
- **Recommandation** : conserver repo (option = contrat / segment = DP) — cohérent doctrine
- **Action** : matrice v1 à corriger (déplacer #5 §4.6.B → §4.8.B)

---

## 6. 4 bonus repo non documentés matrice

### 6.1 `Site.s_ce_m2` (Surface CE OPERAT distincte SDP/tertiaire)

- **Origine** : Sprint C-7 Phase 7.1
- **Source réglementaire** : NOR LOGL2005904A art. 2-j
- **Cardinal** : 3 surfaces distinctes (totale / tertiaire / CE OPERAT) — supérieur à matrice

### 6.2 `DeliveryPoint.tou_schedule_id` FK TOUSchedule

- **Origine** : chantier HC reprog TURPE 7 (V110-HC livré 08/04/2026)
- **Cardinal** : résultat reprog HC matérialisé via FK

### 6.3 ContratCadre champs CEE + capacité + GO offre verte

- **Origine** : Sprint C-1+C-2 cumulés
- **Cardinal** : différenciants vs matrice v1 (CEE éligibilité, capacité incluse, garantie d'origine)

### 6.4 4 champs RGPD audit étendu

- **Origine** : Sprint C-5 Phase 5.3 (ADR-007 ext)
- **Champs** : `consentement_*_by` (FK User) + `consentement_*_cgu_version`
- **Cardinal** : audit RGPD complet (qui + quelle CGU + quand)

---

## 7. État effectif décisions D1-D7

| ID | Décision | Statut |
| --- | --- | --- |
| **D1** | Compteur unifié + DeliveryPoint riche | ✅ **HONORÉE** — `Compteur.type` Enum (élec/gaz/eau) + `DeliveryPoint` ~50 champs |
| **D2** | Audit SMÉ table séparée | ✅ **HONORÉE** — `models/audit_sme.py` confirmé via matrice §4.2 |
| **D3** | BACS tables séparées | ✅ **HONORÉE** — `bacs_models.py` + `bacs_regulatory.py` + `bacs_remediation.py` |
| **D4** | Contrat V2 statu quo | ✅ **HONORÉE** — `contract_v2_models.py` 5 modèles (repo plus riche que matrice 123%) |
| **D5** | ContractDeliveryPoint N:N | ✅ **HONORÉE** — UC `uq_contract_dp` confirmée |
| **D6** | SousCompteur self-FK | ✅ **HONORÉE Phase D-0** — `Compteur.sub_meter_of_id` + ADR-D-01 dualité Compteur/Meter |
| **D7** | Matrice v1 commitée | ✅ **HONORÉE** — `docs/produit/patrimoine_parametrage_requis_v1.md` 951 lignes |

**Conclusion** : 7/7 ✅ honorées intégralement.

---

## 8. Roadmap Phase D-4+ recommandée

| Tier | Périmètre | Effort | Priorité |
| --- | --- | --- | --- |
| **D-4 Tier 1** | 10 P0 cardinaux (Audit SMÉ 3y_gwh + Accises CIBS élec+gaz + DP gaz 5 champs + Compteur.batiment_id + categorie_operat_batiment + bacs_assujetti/cvc + consentement_site_overrides) | **8-12 j-h** | 🔴 BLOCK pilote externe |
| **D-4 Tier 2** | 8 P1 doctrine (dpe_emissions_kgco2_m2 + categorie_operat_batiment + usage_batiment + pcs_kwh_par_nm3 + cdc_pas_temporel_minutes + indice_reference Enum + formule_indexation + cjs_gaz_t3_t4 + EJ adresse_siege) | **6-8 j-h** | 🟠 Avant pilote externe complet |
| **D-4 Tier 3** | 21 P1 polish (Portefeuille responsable_id/actif/tags/couleur_ui + Bâtiment siret/etage_count/parties_communes_pct + DP élec dataconnect_token/scopes/cosphi/modulable + DP gaz pcs/zone_implantation/pitd/adict_token + EJ adresse complète/effectif_etp/CA) | **4-6 j-h** | 🟡 MVP polish |

**Total Phase D-4** : ~18-26 j-h pour 100% couverture matrice v1.

---

## 9. 4 ADR candidats listés post-audit

### ADR-D-02 — Matérialisation vs dérivation runtime DP gaz

- **Contexte** : 5 champs §4.6.C P0 (pce_format, type_reseau, referentiel_tarifaire, est_profile, mode_releve) déductibles via regex/grd_code mais non matérialisés
- **Options** : (a) matérialiser colonnes physiques avec validators cohérence ; (b) `@property` derived runtime ; (c) hybride (matériel + cache)
- **Recommandation** : (a) matérialiser pour traçabilité audit + perf query
- **Effort** : 4-6h migration Alembic 16e

### ADR-D-03 — `Compteur.batiment_id` FK ajout cascade analytics

- **Contexte** : matrice §4.6.A#12 "À vérifier" → ABSENT du repo
- **Options** : (a) FK `batiment_id` nullable + cascade analytics ; (b) cascade via Site.batiments + Compteur.site_id (lourd)
- **Recommandation** : (a) FK directe — gain analytics par bâtiment (différenciateur BACS + APER)
- **Effort** : 3-4h migration + tests cascade

### ADR-D-04 — `Site.bacs_puissance_cvc_totale_kw` cascade Σ(Batiment)

- **Contexte** : matrice §4.4.E#43 typage flou (saisie vs agrégé)
- **Options** : (a) cascade `cascade_recompute_service` ; (b) saisie utilisateur directe ; (c) hybride avec validation
- **Recommandation** : (a) cascade Σ Batiment.cvc_power_kw — anti double SoT
- **Effort** : 2-3h cascade + tests anti-régression

### ADR-D-05 — Accise CIBS Enum strict DP élec + gaz

- **Contexte** : 2 P0 cardinaux billing (P0-MATV1-002 + P0-MATV1-003) — actuellement déduction heuristique
- **Options** : (a) Enum strict `AcciseCategorieElec` + `AcciseCategorieGaz` à matérialiser ; (b) fonction service `get_accise_categorie(dp)` runtime
- **Recommandation** : (a) Enum strict — bloquant billing pilote externe
- **Effort** : 2h Enums + validators + migration

---

## 10. Verdict pilote post audit

| Pilote | Pré audit (assertion Phase D-3 Tier 2) | Post audit |
| --- | --- | --- |
| Interne | ✅ READY | ✅ READY |
| **Investisseur démo** | ✅ READY consolidé | ✅ **READY consolidé** (80% couverture matrice v1) |
| **Externe complet** | 🟢 READY conditionnel | 🟠 **BLOCK Phase D-4 Tier 1** (10 P0 ~8-12 j-h) |

**Note** : assertion "READY conditionnel externe complet" Phase D-3 Tier 2 révisée 🟠 BLOCK suite audit cardinal (10 P0 résiduels matrice v1 cardinaux).

---

## Métadonnées audit

- **3 agents SDK** mobilisés : `architect-helios` cumul (Phase D-2 + D-3 Tier 2 + audit matrice v1)
- **9 fichiers models** lus directement (~1100 lignes cumulées)
- **Confidence globale** : HIGH
- **Pattern Pilier 6 ADR-016** : 6e cycle stable confirmé (Sprint C-7 → C-8 → D → D-3 → audit réglementaire → audit matrice v1)
- **Pattern Pilier 11 ADR-016** : audit systémique pré-livraison majeure (Phase D-4) honoré

**Auditeur** : Sprint Audit Écarts Matrice v1 — `architect-helios` SDK
**Date livraison** : 2026-05-08
**Branche** : `claude/refonte-sol2`
**Décision tactique cardinale** : pause stratégique 24h + GO Phase D-4 Tier 1 ou Tier 2 ciblé billing post-pause.
