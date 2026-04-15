# DT Audit Phase 1-bis -- Conformite Decret Tertiaire
Date : 2026-04-03
Auditeur : Claude Code (Opus 4.6)

---

## RESUME EXECUTIF

**Score global DT : 6.5 / 10**

Le socle reglementaire DT est solide (modele EFA complet, trajectoire implementee, tests 16/16 OK, UX fonctionnelle) mais souffre de **3 problemes structurels** qui compromettent la credibilite demo :

### Top 3 P0 a corriger immediatement

| # | Probleme | Impact |
|---|----------|--------|
| **P0-1** | **3 services de trajectoire divergents** : `dt_trajectory_service.py` (sans DJU), `operat_trajectory.py` (avec DJU), `cockpit.py:get_cockpit_trajectory()` (hardcode). Meme site = 3 calculs differents. | Score trajectoire incoherent selon la page consultee |
| **P0-2** | **Dualite Site vs TertiaireEfa** : RegOps lit `Site.tertiaire_area_m2` tandis que trajectoire lit `TertiaireEfa.reference_year_kwh`. Desynchronisation possible (ex: Usine Toulouse `tertiaire_area_m2=None` alors que `surface_m2=6000`). | Site assujetti non detecte par le moteur RegOps |
| **P0-3** | **Jalon 2026 (-25%) fantome** : retourne par l'API cockpit/trajectory mais commente "pas de jalon officiel en 2026" dans le code. Absent de regs.yaml et operat_trajectory.py. Le decret n2019-771 ne prevoit que -40%/-50%/-60%. | Donnee reglementaire potentiellement trompeuse |

---

## AXE 1 -- Systemes de Scoring

### Tableau des 3 systemes

| Systeme | Fichier:Lignes | Formule exacte | Echelle | Direction | Inputs | Cache |
|---------|---------------|----------------|---------|-----------|--------|-------|
| **S1 -- compliance_score_service.py** | `services/compliance_score_service.py:143-234` | `score = weighted_avg(DT*0.45 + BACS*0.30 + APER*0.25) - min(criticals*5, 20)` clamp [0,100] | 0-100 | higher = better | RegAssessment par framework, fallback ComplianceFinding | Persiste sur `Site.compliance_score_composite` via `sync_site_unified_score()` |
| **S2 -- regops/scoring.py** | `regops/scoring.py:118-208` | `raw_score = 100 - (weighted_sum / total_weight * 100)` | 0-100 | higher = better | Findings actifs, `scoring_profile.json` (poids = 1.0 pour tous) | Aucun cache |
| **S3 -- regops/engine.py** | `regops/engine.py:180-190` | `composite = score_S1 * 0.84 + audit_sme * 100 * 0.16` | 0-100 | higher = better | S1 + audit_sme_service | Persiste dans `RegAssessment.compliance_score` |

### Architecture du flux

```
regops/engine.py:evaluate_site()  -- point d'entree
  |-- appelle compliance_score_service.compute_site_compliance_score() [S1]
  |     poids : DT 0.45 / BACS 0.30 / APER 0.25 (regs.yaml)
  |-- applique bonus Audit/SME : composite = S1 * 0.84 + audit_sme * 0.16
  |-- persiste dans RegAssessment.compliance_score [S3]
  |
  regops/scoring.py [S2] -- utilise UNIQUEMENT pour score_explain (detail)
        poids : 1.0/1.0/1.0 (scoring_profile.json) -- DIVERGENT
```

### Verdict : les 3 systemes sont-ils coherents ?

**PARTIELLEMENT.** S1 et S3 sont convergents (S3 appelle S1 + ajustement Audit/SME). S2 est un module historique avec des **poids differents** (1.0 partout vs 0.45/0.30/0.25) utilise uniquement pour le detail `score_explain`. Risque : si `score_explain` est affiche cote UI, l'utilisateur voit un detail qui ne correspond pas au score global.

### Constantes hardcodees frontend

**AUCUNE.** Le frontend consomme `risque_eur` depuis le backend sans recalcul. Les tests `source_guards` verifient l'absence de `* 7500` ou `* 3750` dans le code source frontend. Le fichier `normalizeRisk.jsx` documente `BASE_PENALTY = 7500` en commentaire uniquement.

### Constantes backend

| Constante | Valeur | Fichier |
|-----------|--------|---------|
| `BASE_PENALTY_EURO` | 7 500 | `config/emission_factors.py:38` |
| `A_RISQUE_PENALTY_RATIO` | 0.5 | `config/emission_factors.py:39` |
| `A_RISQUE_PENALTY_EURO` | 3 750 | `config/emission_factors.py:40` |
| `framework_weights.tertiaire_operat` | 0.45 | `regops/config/regs.yaml:141` |
| `framework_weights.bacs` | 0.30 | `regops/config/regs.yaml:142` |
| `framework_weights.aper` | 0.25 | `regops/config/regs.yaml:143` |

---

## AXE 2 -- Trajectoire DT

### Jalons definis dans le code

| Source | 2026 | 2030 | 2040 | 2050 |
|--------|------|------|------|------|
| **Decret n2019-771 (officiel)** | -- | -40% | -50% | -60% |
| `regs.yaml:13-15` | ABSENT | -0.40 | -0.50 | -0.60 |
| `operat_trajectory.py:57-61` | ABSENT | 0.60 (garder) | 0.50 | 0.40 |
| `dt_trajectory_service.py:25-27` | ABSENT | 40.0% | 50.0% | 60.0% |
| `routes/cockpit.py:442` | ABSENT | -0.40 | -0.50 | -0.60 |
| `routes/cockpit.py:521-526` | **-25.0%** | -0.40 | -0.50 | -0.60 |

**ALERTE** : Le jalon 2026 (-25%) apparait UNIQUEMENT dans `cockpit.py:521` avec le commentaire explicite "pas de jalon officiel en 2026". Il est retourne par l'API mais ne correspond a aucun texte du decret n2019-771 (Art. R131-39 CCH).

### Calcul trajectoire implemente ?

**OUI, dans 3 services distincts (P0)** :

| Service | Formule | Correction DJU | Source conso |
|---------|---------|---------------|--------------|
| `dt_trajectory_service.py:162` | `reduction_pct = (1 - conso_actuelle / conso_ref) * 100` | **NON** | ConsumptionTarget (brute) |
| `operat_trajectory.py:172-260` | `current_kwh vs baseline * TARGETS[year]` | **OUI** (si `is_normalized=True`) | TertiaireEfaConsumption |
| `routes/cockpit.py:get_cockpit_trajectory()` | `ConsumptionTarget.actual_kwh` agregge | **NON** | ConsumptionTarget |

### Correction DJU appliquee ?

**PARTIELLEMENT.** Seul `operat_trajectory.validate_trajectory()` supporte la normalisation DJU via les champs `is_normalized`, `normalized_kwh_total`, `dju_heating`, `dju_reference` sur `TertiaireEfaConsumption`. Les 2 autres services utilisent la conso brute. Les seeds laissent `is_normalized=False` pour toutes les consommations.

### Endpoint progression DT par site ?

**2 endpoints, pas de vue site individuelle** :
- `GET /api/cockpit/trajectory` -- niveau portefeuille, serie annuelle
- `GET /api/tertiaire/efa/{efa_id}/trajectory` -- par EFA individuelle

Il manque un `GET /api/sites/{id}/dt-progress` retournant le pourcentage de progression DT par site.

### Calcul frontend ?

**AUCUN.** Le hook `useCockpitData.js` stipule : "Ce hook ne calcule RIEN. Il fetch, normalise, et expose." Tests `source_guards` verifient l'absence de formules. Conforme.

### ConsumptionTargets 2020-2026 seedes ?

**728 entrees trouvees** (vs ~416 attendues) :

| Annee | Count |
|-------|-------|
| 2020 | 104 |
| 2021 | 104 |
| 2022 | 104 |
| 2023 | 104 |
| 2024 | 104 |
| 2025 | 104 |
| 2026 | 104 |
| **Total** | **728** |

La granularite est plus fine qu'attendu : 104 targets/an = 5 sites x ~20 periodes (mensuel + annuel par usage). Seeds presents et complets.

---

## AXE 3 -- Modele EFA / OPERAT

### Tables presentes

| Table | Modele | Role |
|-------|--------|------|
| `tertiaire_efa` | `TertiaireEfa` | Entite Fonctionnelle Assujettie |
| `tertiaire_efa_consumption` | `TertiaireEfaConsumption` | Conso annuelle par EFA |
| `tertiaire_efa_building` | -- | Association EFA <-> Batiment |
| `tertiaire_efa_link` | -- | Liens EFA (turnover, fusion) |
| `tertiaire_responsibility` | -- | Responsabilites acteurs |
| `tertiaire_perimeter_event` | -- | Evenements perimetre |
| `tertiaire_declaration` | -- | Declarations annuelles OPERAT |
| `tertiaire_proof_artifact` | -- | Preuves documentaires |
| `tertiaire_data_quality_issue` | -- | Issues qualite donnees |
| `tertiaire_efa_dpe` | -- | DPE Tertiaire (decret 2024-1040) |
| `tertiaire_seuil_absolu` | -- | Seuils Cabs OPERAT par categorie |
| `consumption_targets` | `ConsumptionTarget` | Objectifs conso DT |
| `csrd_site_reporting` | -- | Reporting CSRD |

### EFA seedees HELIOS : 4 / 5 attendues

| EFA | Site | reference_year_kwh | conso_2024 | Trajectory |
|-----|------|--------------------|-----------|------------|
| EFA Siege HELIOS Paris | Paris | 595 000 | 500 000 | **off_track** (obj 2030 = 357k) |
| EFA Hotel HELIOS Nice | Nice | 1 120 000 | 700 000 | on_track |
| EFA Retail HELIOS Lyon | Lyon | 204 000 | 110 000 | on_track |
| EFA Logistique HELIOS Marseille | Marseille | 308 000 | 250 000 | off_track |
| **(MANQUANT)** Usine Toulouse | Toulouse | -- | -- | -- |

Chaque EFA a 5 `TertiaireEfaConsumption` (2020-2024) = 20 lignes total.

### Champs OPERAT critiques -- dualite Site vs EFA

| Champ | Sur `Site` (legacy) | Sur `TertiaireEfa` (canonique) |
|-------|--------------------|-----------------------------|
| Surface assujettie | `tertiaire_area_m2` | (implicite via building) |
| Annee reference | **ABSENT** | `reference_year` |
| Conso reference | `annual_kwh_total` | `reference_year_kwh` |
| Statut OPERAT | `operat_status` | `trajectory_status` |
| Normalisation DJU | -- | `baseline_normalization_status` |

**P0** : `regops/rules/tertiaire_operat.py` lit les champs de `Site` (`site.tertiaire_area_m2`, `site.operat_status`), tandis que `operat_trajectory.py` lit `TertiaireEfa`. Risque de desynchronisation si les champs Site ne sont pas mis a jour apres modification d'une EFA.

---

## AXE 4 -- Tests RegOps

### Tests passant : 16/16

```
tests/test_regops_rules.py ................  [100%]
16 passed in 6.03s
```

**Progres majeur** : 0/16 -> 16/16. Le YAML mismatch precedent a ete corrige.

### Cause YAML mismatch (resolue)

Le fichier `regs.yaml` et les tests sont maintenant parfaitement alignes :

| Parametre | regs.yaml | Tests | Statut |
|-----------|-----------|-------|--------|
| `scope_threshold_m2` | 1000 | Tests : 1200 (in), 800 (out) | OK |
| `non_declaration` | 7500 | `penalties.get("non_declaration", 7500)` | OK |
| `non_affichage` | 1500 | Idem | OK |

### Tests EFA/trajectoire DT : 97+ tests

| Fichier | Tests | Couverture |
|---------|-------|-----------|
| `test_regops_rules.py` | 16 | Scope DT/BACS/APER/CEE |
| `test_operat_trajectory.py` | 16 | Trajectoire -40%/-50%/-60% |
| `test_seed_dt_baseline.py` | 16 | Seeds ConsumptionTarget |
| `test_router_mount_tertiaire.py` | 12 | Routes CRUD EFA |
| `test_operat_hardening.py` | 10 | Robustesse EFA |
| `test_dt_e2e_parcours.py` | 9 | Parcours E2E |
| `test_operat_normalization.py` | 8 | Normalisation DJU |
| `test_v44_patrimoine_operat.py` | 8 | Patrimoine OPERAT |
| `test_v113_operat_golden.py` | 6 | Golden tests export |
| `test_step14_penalty.py` | 5 | Penalites |
| `test_operat_safety.py` | 4 | Securite OPERAT |

**Note** : Le test global `pytest tests/ -x` echoue sur un SQLite lock dans `test_action_close_rules_v49.py` (concurrence DB, pas un defaut DT).

---

## AXE 5 -- UX Conformite

### Page /conformite/tertiaire : EXISTE + fonctionnelle

- **Fichier** : `frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx`
- **Contenu** : Dashboard complet avec KPIs (EFA enregistrees, anomalies ouvertes, issues critiques, countdown deadline OPERAT J-xxx)
- **Section** "Sites a traiter" avec filtres par signal (assujetti_probable, a_verifier, non_concerne)
- **Export OPERAT** modal integre (V113)
- **Pages additionnelles** :
  - `/conformite/tertiaire/efa/:id` -- Fiche detail EFA
  - `/conformite/tertiaire/anomalies` -- Anomalies
  - Wizard creation EFA

### Ecran trajectoire -25%/-40% : PARTIEL

- **Cockpit** (`Cockpit.jsx:591-638`) : Widget "Progression trajectoire mensuelle" avec barre de progression vers l'objectif -40%, affichage avance/retard, projection MWh.
- **Fiche EFA detail** : Bloc `EfaTrajectoryBlock` avec statut trajectoire par EFA (on_track / off_track / not_evaluable).
- **Absent** : vue synthetique multi-site montrant -25%/-40% cote a cote pour tous les sites.

### Banner DT cockpit : PRESENT avec nuance

- **Banner retard trajectoire** (`data-testid="banner-retard-trajectoire"`, Cockpit.jsx:604-638) : Declenche quand `reductionPctActuelle > objectifPremierJalonPct`. Texte : "Trajectoire DT 2030 en retard de X.X pts" + risque EUR + "Actions P0 a lancer avant le 30 avril 2026" + lien "Plan de rattrapage".
- **ABSENT** : Banner specifique "Deadline OPERAT 30/09/2026" dans le Cockpit. Ce compteur apparait dans `TertiaireDashboardPage.jsx` (`Deadline OPERAT J-xxx`) mais PAS dans le Cockpit principal.

### ConformitePage -- findings TERTIAIRE_OPERAT : CORRECTEMENT CABLE

- `ConformitePage.jsx` appelle `getComplianceBundle()` qui retourne sites et summary.
- `sitesToObligations()` transforme les findings en obligations affichables.
- L'obligation `decret_tertiaire_operat` est reconnue avec preuves pre-seedees (Declaration_OPERAT_2025.pdf, Attestation_trajectoire_-40pct.pdf).
- Bouton "Ouvrir OPERAT" navigue vers `/conformite/tertiaire`.
- `ComplianceScoreHeader` affiche le breakdown avec poids 45% pour tertiaire_operat.

---

## AXE 6 -- Seeds HELIOS

### Sites >= 1000 m2 assujettis : 4/5

| Site | surface_m2 | tertiaire_area_m2 | >= 1000 | conso (kWh) | operat_status |
|------|-----------|-------------------|---------|-------------|---------------|
| Siege HELIOS Paris | 3 500 | 3 500 | OUI | 595 000 | SUBMITTED |
| Bureau Regional Lyon | 1 200 | 1 200 | OUI | 204 000 | IN_PROGRESS |
| Usine HELIOS Toulouse | 6 000 | **None** | OUI | 720 000 | **None** |
| Hotel HELIOS Nice | 4 000 | 4 000 | OUI | 1 120 000 | NOT_STARTED |
| Ecole Jules Ferry Marseille | 2 800 | 2 800 | OUI | 308 000 | IN_PROGRESS |

**ECART P0** : Usine Toulouse (6 000 m2) a `tertiaire_area_m2 = None` et `operat_status = None`. Le moteur RegOps la classe SCOPE_UNKNOWN. **4 sites sur 5 correctement marques assujettis.**

### ref_year 2020 seedee : 0/5 sites (champ absent du modele)

Le champ `ref_year` **n'existe pas** dans le modele `Site`. L'annee de reference est geree au niveau `TertiaireEfa.reference_year` (= 2020 pour les 4 EFA seedees) et `TertiaireEfaConsumption.is_reference` (= True pour l'annee 2020). Pas de traçabilite au niveau site.

### ConsumptionTargets : 728 trouves (vs ~416 attendus)

728 entries = 104 par an x 7 annees (2020-2026). Granularite plus fine qu'estime (mensuel + annuel par usage). **Seeds complets et coherents.**

### Penalite risque_eur coherente ?

**PARTIELLEMENT.** Le moteur RegOps applique correctement les constantes :
- `non_declaration` : 7 500 EUR/site (regs.yaml + emission_factors.py)
- `non_affichage` : 1 500 EUR/site

Mais le calcul reel est finding-par-finding, pas `n_efa x 7500`. Avec 1 seul site NOT_STARTED ayant `tertiaire_area_m2` renseigne (Nice), la penalite seedee est ~7 500 EUR, pas 37 500 EUR. L'ecart vient de Toulouse (non detecte car `tertiaire_area_m2 = None`).

---

## PLAN DE CORRECTION

### P0 (bloquants credibilite demo)

| # | Action | Fichiers concernes | Effort |
|---|--------|-------------------|--------|
| P0-1 | **Unifier le calcul trajectoire** : `dt_trajectory_service.py` doit deleguer a `operat_trajectory.validate_trajectory()` (seul service avec DJU). Supprimer le calcul inline dans `cockpit.py`. | `dt_trajectory_service.py`, `operat_trajectory.py`, `routes/cockpit.py` | M |
| P0-2 | **Corriger seed Toulouse** : seeder `tertiaire_area_m2 = 6000` et `operat_status = 'NOT_STARTED'` + creer la 5eme EFA | `services/demo_seed/gen_tertiaire_efa.py`, `services/demo_seed/gen_sites.py` | S |
| P0-3 | **Retirer le jalon 2026 (-25%) fantome** : supprimer de `cockpit.py:521` et du test associe, ou le documenter comme objectif interne (pas reglementaire) avec un label explicite | `routes/cockpit.py`, `tests/test_cockpit_p0.py` | S |
| P0-4 | **Resoudre divergence poids scoring** : `scoring_profile.json` (1.0/1.0/1.0) vs `regs.yaml` (0.45/0.30/0.25). Aligner ou supprimer `scoring_profile.json` si S2 n'est plus utilise pour le score affiche | `regops/config/scoring_profile.json`, `regops/scoring.py` | S |

### P1 (correctifs scoring)

| # | Action | Fichiers concernes | Effort |
|---|--------|-------------------|--------|
| P1-1 | **Ajouter banner deadline OPERAT 30/09/2026 dans le Cockpit** : widget countdown a cote du banner retard trajectoire | `frontend/src/pages/Cockpit.jsx` | S |
| P1-2 | **Vue multi-site trajectoire** : ecran comparatif -40% pour tous les sites avec statut on_track/off_track | `frontend/src/pages/tertiaire/` | M |
| P1-3 | **Activer normalisation DJU dans les seeds** : passer `is_normalized=True` avec des valeurs DJU realistes pour au moins 2 EFA demo | `services/demo_seed/gen_tertiaire_efa.py` | S |
| P1-4 | **Resoudre SQLite lock** dans `test_action_close_rules_v49.py` pour que `pytest tests/ -x` passe au complet | `tests/test_action_close_rules_v49.py` | S |

### P2 (enrichissements)

| # | Action | Effort |
|---|--------|--------|
| P2-1 | Endpoint `GET /api/sites/{id}/dt-progress` retournant % progression DT par site | M |
| P2-2 | Deprecation formelle de `regops/scoring.py` (S2) si confirm inutilise pour le score affiche | S |
| P2-3 | Migration des champs DT de `Site` vers `TertiaireEfa` exclusivement (supprimer la dualite) | L |

---

## RAPPELS CANONIQUES

| Constante | Valeur | Source | Statut code |
|-----------|--------|--------|-------------|
| Jalons DT | -40% 2030 / -50% 2040 / -60% 2050 | Decret n2019-771 du 23/07/2019 | OK (regs.yaml + 3 services) |
| Jalon 2026 (-25%) | **Non officiel** | Pas dans le decret | PRESENT dans cockpit.py -- P0-3 |
| Penalite base | 7 500 EUR/EFA non declaree | Decret n2019-771, art. R131-38 | OK (emission_factors.py) |
| Penalite a risque | 3 750 EUR (50%) | Idem | OK |
| Surface assujettie | >= 1 000 m2 (tertiaire) | Decret n2019-771, art. R131-26 | OK (regs.yaml scope_threshold_m2) |
| Deadline OPERAT | 30 septembre N pour N-1 | OPERAT ADEME | OK (TertiaireDashboard, absent Cockpit) |
| CO2 electricite | 0.052 kgCO2/kWh | ADEME Base Empreinte V23.6 | Backend only -- conforme |
| Annee reference | 2010-2020, seedee 2020 | Decret 2019-771 | OK (TertiaireEfa.reference_year) |
| SoT compliance_score | RegAssessment via engine.py | Architecture PROMEOS | OK (S3 appelle S1) |
| Poids DT scoring | 45% (sans Audit/SME) / 39% (avec) | Canonical PROMEOS | OK (regs.yaml 0.45, engine.py *0.84) |
