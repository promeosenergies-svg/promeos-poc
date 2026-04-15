# Audit Phase 1 — Conformite / Decret Tertiaire

> **Date** : 2026-03-30
> **Auteur** : Claude Code (audit automatise)
> **Methode** : Lecture seule — zero modification
> **Scope** : 32 fichiers backend + frontend + tests + seed + docs

---

## 1. Cartographie des fichiers

### Backend — Core

| Fichier | Lignes | Role | Dependances cles |
|---------|--------|------|------------------|
| `regops/config/regs.yaml` | 165 | Config unique : poids, seuils, deadlines, penalites | — |
| `regops/engine.py` | 275 | Orchestrateur 4 evaluateurs (DT, BACS, APER, CEE) | rules/*, scoring.py, compliance_score_service |
| `regops/scoring.py` | 208 | Scoring unifie avec dedup, urgence, confiance | regs.yaml |
| `regops/rules/tertiaire_operat.py` | 126 | 4 regles DT : scope, operat_not_started, energy_data, multi_occupied | regs.yaml |
| `regops/rules/bacs.py` | ~80 | Delegation vers bacs_engine | bacs_engine.py |
| `regops/rules/aper.py` | ~100 | Parking + toiture solaire | regs.yaml |
| `regops/rules/cee_p6.py` | ~60 | Hints CEE (non score) | — |
| `services/compliance_score_service.py` | 483 | **SOURCE UNIQUE A.2** : score 0-100, higher=better | regs.yaml, RegAssessment |
| `services/compliance_engine.py` | 1255 | **LEGACY** : snapshots Site, reg_risk (higher=worse) | Obligation, Evidence |
| `services/operat_trajectory.py` | ~350 | Trajectoire baseline, normalisation DJU, TARGETS | TertiaireEfa, EfaConsumption |
| `services/dt_trajectory_service.py` | ~150 | Trajectoire dynamique, avancement % | consumption_unified_service |
| `config/emission_factors.py` | 46 | CO2 : ELEC=0.052, GAZ=0.227 (ADEME V23.6) | — |

### Backend — Modeles

| Fichier | Lignes | Role |
|---------|--------|------|
| `models/tertiaire.py` | 372 | EFA, Consumption, Building, Responsibility, Declaration, Proof, DPE, SeuilAbsolu, CSRD |
| `models/reg_assessment.py` | ~50 | Cache RegAssessment |

### Backend — Routes

| Fichier | Lignes | Role |
|---------|--------|------|
| `routes/tertiaire.py` | 1051 | CRUD EFA, declarations, preuves, export |
| `routes/cockpit.py` | 611 | KPIs portfolio, trajectoire, jalons |
| `routes/regops.py` | ~100 | Assessment endpoints |

### Backend — Seed

| Fichier | Lignes | Role |
|---------|--------|------|
| `services/demo_seed/packs.py` | ~160 | Definition pack HELIOS (5 sites) |
| `services/demo_seed/gen_tertiaire_efa.py` | ~240 | Seed 3 EFA (Paris, Nice, Lyon) |
| `services/demo_seed/gen_compliance.py` | ~200 | Seed findings compliance |

### Frontend

| Fichier | Lignes | Role | Calcul metier ? |
|---------|--------|------|-----------------|
| `pages/ConformitePage.jsx` | 828 | Cockpit conformite, 4 onglets | Non |
| `pages/RegOps.jsx` | 372 | Panel dual audit + IA | Non |
| `pages/tertiaire/TertiaireDashboardPage.jsx` | ~150 | Dashboard EFA | Non |
| `pages/tertiaire/TertiaireWizardPage.jsx` | ~150 | Wizard creation EFA 6 etapes | Non |
| `pages/tertiaire/TertiaireEfaDetailPage.jsx` | ~100 | Detail EFA + trajectoire | Non |
| `pages/tertiaire/TertiaireAnomaliesPage.jsx` | ~100 | Anomalies DT | Non |
| `pages/ConsumptionExplorerPage.jsx` | ~400 | Exploration conso | **OUI** (0.052) |
| `pages/consumption/constants.js` | ~15 | Constantes conso | **OUI** (CO2E_FACTOR) |
| `domain/compliance/complianceLabels.fr.js` | ~486 | Labels FR + refs legales | Non |
| `utils/format.js` | 159 | Formatage FR (EUR, kWh, m2, %) | Non |
| `models/dashboardEssentials.js` | ~450 | Watchlist, briefing, health | Non |
| `services/kpiMessaging.js` | 512 | Messages KPI contextuels | Non |

### Tests

| Fichier | Tests | Role |
|---------|-------|------|
| `backend/tests/test_regops_rules.py` | 16 | Regles DT/BACS/APER/CEE |
| `backend/tests/test_conformite_source_guards.py` | 22 | Guards poids, seuils, deadlines |
| `backend/tests/test_consumption_source_guard.py` | 10 | Guards conso unifiee |
| `backend/tests/test_router_mount_tertiaire.py` | 12 | Mount routes + OpenAPI |

### Documentation

| Fichier | Role | Completude |
|---------|------|------------|
| `docs/decisions/tertiaire_sources_map.md` | Tracabilite legale | 0% page/section |
| `docs/kpi-coherence-audit.md` | Coherence KPI | Score 55/100 |
| `docs/kpi_dictionary.md` | Definitions KPI | Partiel |

---

## 2. Scoring : systemes identifies et divergences

### 3 systemes de scoring coexistent

| Systeme | Fichier | Echelle | Direction | Formule |
|---------|---------|---------|-----------|---------|
| **A.2 Unifie (SoT)** | `compliance_score_service.py` | 0-100 | Higher = better | `avg_ponderee(DT*0.45 + BACS*0.30 + APER*0.25) - penalty_critiques` |
| **Legacy Snapshot** | `compliance_engine.py` | 0-100 | Higher = **worse** | `100 - risk_score`, persiste dans `Site.compliance_score_composite` |
| **Cockpit Count** | `routes/cockpit.py` | N/M | Count | Nombre de findings NOK/total |

### Divergence critique : penalite A_RISQUE

| Source | NON_CONFORME | A_RISQUE | Formule |
|--------|-------------|----------|---------|
| `compliance_engine.py:85-88` | 7 500 EUR | **0 EUR** | `7500 * count(NON_CONFORME)` |
| `migrations.py:841` | 7 500 EUR | **3 750 EUR** | `7500 * NOK + 3750 * A_RISQUE` |
| `demo_seed/orchestrator.py` | 7 500 EUR | **3 750 EUR** | idem migration |
| `schemas/kpi_catalog.py:39` | 7 500 EUR | **3 750 EUR** | formule documentation |

**Impact** : Site avec 2 NON_CONFORME + 1 A_RISQUE :
- Via compliance_engine : **15 000 EUR**
- Via seed/migration : **18 750 EUR**
- **Ecart : +3 750 EUR (25%)**

### Constantes hardcodees

| Constante | Localisation production | Localisation config | Statut |
|-----------|------------------------|--------------------|---------|
| 7 500 EUR | `tertiaire_operat.py:59` (fallback YAML) | `regs.yaml` | OK (fallback) |
| 3 750 EUR | `compliance_engine.py:59` | Derive de 7500*0.5 | OK |
| 0.052 kgCO2/kWh | `ConsumptionExplorerPage.jsx:344` | `emission_factors.py` | **VIOLATION** |
| CO2E_FACTOR | `consumption/constants.js:13` | — | **VIOLATION** |

---

## 3. Trajectoire : etat actuel

### 2 services coexistent

| Aspect | `operat_trajectory.py` | `dt_trajectory_service.py` |
|--------|------------------------|----------------------------|
| Granularite | Par EFA | Par Site |
| Format cible | TARGETS = {2030: 0.60, 2040: 0.50, 2050: 0.40} | OBJECTIF_2030_PCT=40, 2040=50, 2050=60 |
| Equivalence | baseline * 0.60 = remaining 60% = -40% | (1 - actual/ref) * 100 / 40 * 100 |
| Normalisation DJU | Oui (9 statuts : normalized, raw_only, mixed_basis_warning...) | Non |
| Persistance | `EFA.trajectory_status` | `Site.avancement_decret_pct` |
| Confiance | baseline_normalization_status + confidence | Aucun champ |

### Constats

- Les 2 services sont **algebriquement equivalents** (-40% = garder 60%) mais utilises en parallele
- `operat_trajectory.py` est le service autoritaire (gouvernance normalisation, reliability tracking)
- `dt_trajectory_service.py` est un "raccourci" pour le cockpit
- **Risque** : les 2 ecrivent en DB de maniere non coordonnee
- **Jalon 2026 (-25%)** : present dans `routes/cockpit.py` (jalons API) mais PAS dans TARGETS officiel. C'est une interpolation, pas un objectif reglementaire au sens strict du decret (note : le decret mentionne un premier jalon en 2030, mais l'echeance OPERAT 2026 est la date de premiere declaration obligatoire)

### Champs trajectoire dans le modele

- `TertiaireEfa.reference_year` : **present** (Integer, nullable)
- `TertiaireEfa.reference_year_kwh` : **present** (Float, nullable)
- `TertiaireEfa.trajectory_status` : **present** (on_track / off_track / not_evaluable)
- `TertiaireEfa.baseline_normalization_status` : **present** (normalized / raw_only / not_possible / unknown)
- `TertiaireEfaConsumption.is_reference` : **present** (Boolean)
- `TertiaireEfaConsumption.dju_*` : **present** (heating, cooling, reference, weather_data_source)
- `TertiaireEfaConsumption.normalization_*` : **present** (method, confidence, normalized_kwh_total)

---

## 4. Modele EFA : champs presents vs manquants

### Champs presents (bien structures)

| Champ | Table | Type | Commentaire |
|-------|-------|------|-------------|
| reference_year | TertiaireEfa | Integer | Annee de reference |
| reference_year_kwh | TertiaireEfa | Float | Conso reference verrouillee |
| trajectory_status | TertiaireEfa | String(20) | on_track / off_track / not_evaluable |
| baseline_normalization_status | TertiaireEfa | String(20) | normalized / raw_only / unknown |
| is_reference | TertiaireEfaConsumption | Boolean | Flag annee de reference |
| dju_heating / dju_cooling / dju_reference | TertiaireEfaConsumption | Float | Donnees climatiques |
| normalization_method / normalization_confidence | TertiaireEfaConsumption | String | Methode + confiance |
| usage_label / surface_m2 | TertiaireEfaBuilding | String/Float | Usage et surface par batiment |
| classe_energie / classe_ges | TertiaireEfaDpe | Enum | DPE tertiaire |
| zone_climatique | TertiaireSeuilAbsolu | String(10) | Zone OPERAT (H1a...H3) |

### Champs manquants pour OPERAT complet

| Champ manquant | Table cible | Impact | Priorite |
|----------------|-------------|--------|----------|
| `zone_climatique` | TertiaireEfa ou Site | Impossible de faire le lookup Cabs (seuils absolus) | P1 |
| `categorie_fonctionnelle` | TertiaireEfa | Impossible de selectionner le seuil Cabs par categorie OPERAT | P1 |
| `conso_reference_kwh_m2` | TertiaireEfa | Derive (ref_kwh / surface) mais pas stocke, utile pour comparaisons | P2 |
| `nb_occupants` (IIU) | TertiaireEfa | Necessaire pour modulation IIU | P3 |
| `horaires_ouverture` (IIU) | TertiaireEfa | Necessaire pour modulation IIU | P3 |
| `modulation_applicable` | TertiaireEfa | Boolean pour tracker eligibilite modulation | P3 |
| `groupe_mutualisation_id` | TertiaireEfa | FK pour regroupement mutualisation inter-sites | P3 |

### Tables presentes et fonctionnelles

- TertiaireEfa (entite principale)
- TertiaireEfaConsumption (conso annuelle avec normalisation DJU)
- TertiaireEfaBuilding (batiments associes)
- TertiaireResponsibility (responsabilites par acteur)
- TertiairePerimeterEvent (evenements : changement occupant, vacance, renovation)
- TertiaireDeclaration (declarations OPERAT annuelles)
- TertiaireProofArtifact (preuves documentaires)
- TertiaireDataQualityIssue (anomalies qualite)
- TertiaireEfaDpe (DPE tertiaire)
- TertiaireSeuilAbsolu (Cabs par categorie + zone)
- TertiaireEfaLink (liens entre EFA : scission, fusion)
- CsrdAssujettissementSite (CSRD)

---

## 5. UX/UI : constats par page

| Page | Route | Etats geres | Labels FR | Calcul metier frontend | Tooltips DT | Constat |
|------|-------|-------------|-----------|----------------------|-------------|---------|
| ConformitePage | `/conformite` | Loading, Empty (NO_SITES, NO_DATA), Error, Ready | Excellent (complianceLabels.fr.js) | Aucun | Partiel (Explain wrapper) | 4 onglets bien structures, guided mode |
| RegOps | `/regops/:id` | Loading, NotFound, Ready | Bon | Aucun | Minimal | Dual panel audit + IA |
| TertiaireDashboard | `/conformite/tertiaire` | Loading, Empty, Ready | Excellent | Aucun | Drawer "Pourquoi ?" | Signaux EFA bien presentes |
| TertiaireWizard | `/conformite/tertiaire/wizard` | 6 etapes, validation | Parfait | Aucun | Non | Manque barre progression + brouillon |
| TertiaireEfaDetail | `/conformite/tertiaire/efa/:id` | Loading, Ready | Bon | Aucun | Status badges | Trajectoire OPERAT block present |
| TertiaireAnomalies | `/conformite/tertiaire/anomalies` | Loading, Ready | Bon | Aucun | Non | Workflow anomalies OK |
| ConsumptionExplorer | `/consumption` | Loading, Ready | Bon | **OUI : `totalKwh * 0.052`** | Non | **VIOLATION source-guard** |

### Constats UX globaux

- **Positif** : Labels FR centralises (486 lignes), guided mode non-expert, 4 onglets logiques
- **Manquant** : Glossaire DT inline (EFA, IIU, DJU, CRefAbs, modulation) — aucun GlossaireTip
- **Manquant** : Jalons explicites 2030/2040/2050 sur le graphe trajectoire
- **Manquant** : Wizard sans barre progression ni mode brouillon
- **Manquant** : Responsive non teste a 1280px

---

## 6. Tests : resultats

### Backend — 2026-03-30

| Suite | Tests | Resultat | Duree |
|-------|-------|----------|-------|
| `test_regops_rules.py` | 16 | **16/16 PASS** | 3.3s |
| `test_conformite_source_guards.py` | 22 | **22/22 PASS** | 1.8s |
| `test_consumption_source_guard.py` | 10 | **10/10 PASS** | — |
| `test_router_mount_tertiaire.py` | 12 | **12/12 PASS** (1 warning) | 11.2s |
| **Total backend DT** | **60** | **60/60 PASS** | ~16s |

Warning : `Duplicate Operation ID kb_ping` dans OpenAPI — cosmétique.

### Frontend — 2026-03-30

| Resultat global | Fichiers | Tests | Skipped |
|-----------------|----------|-------|---------|
| **145 fichiers PASS** | 145 | **3616 PASS** | 2 skipped |

Tests DT-specifiques confirmes verts :
- `conformiteUxUpgrade.test.js` : 16 tests UX conformite
- `step4_co2_guard.test.js` : guards CO2 factor
- `step30_efa_guard.test.js` : 5 tests seed EFA
- `consumptionSourceGuard.test.js` : 13 tests source conso
- `sourceGuards.test.js` : guards generaux

**Note** : Le test `step4_co2_guard` verifie que `VecteurEnergetiqueCard.jsx` n'a PAS de 0.052 hardcode (PASS). Mais `ConsumptionExplorerPage.jsx` n'est PAS couvert par ce guard — le 0.052 y est present en production.

---

## 7. Sources reglementaires : tracabilite

### Etat de `docs/decisions/tertiaire_sources_map.md`

| Categorie | Total | Source nommee | Page/section exacte | Tracabilite |
|-----------|-------|---------------|--------------------|-----------|
| Regles implementees | 5 | 5/5 | **0/5** | **0%** |
| Seuils/parametres | 5 | 5/5 | **0/5** | **0%** |
| Regles a ajouter (TODO) | 9 | 9/9 | **0/9** | **0%** |
| **Total** | **19** | **19/19** | **0/19** | **0%** |

Toutes les entrees indiquent "A CLARIFIER (page/section)". Les textes de reference (Decret n2019-771, Arrete du 10 avril 2020, Code construction L174-1) sont nommes mais aucune page/section n'est extraite.

### Contraste frontend

Le fichier `complianceLabels.fr.js` contient des `RULE_LEGAL_REFS` avec articles specifiques et URLs Legifrance. Cette couche est **plus avancee** que le backend `tertiaire_sources_map.md`.

### Documents a ingerer

- Decret n2019-771 (texte consolide) — non indexe
- Arrete du 10 avril 2020 (modalites) — non indexe
- FAQ ADEME Decret tertiaire — non localise
- Guide OPERAT utilisateur — non localise

---

## 8. Seed : etat des donnees demo DT

### Pack HELIOS — 5 sites

| Site | Ville | Surface tertiaire | CVC kW | OPERAT | EFA creee | reference_year | reference_year_kwh | Conso annuelle |
|------|-------|-------------------|--------|--------|-----------|----------------|-------------------|----------------|
| Siege Paris | Paris | 3 500 m2 | 300 | SUBMITTED | Oui (ACTIVE) | **NULL** | **NULL** | 800 000 kWh |
| Bureau Lyon | Lyon | 1 200 m2 | 50 | IN_PROGRESS | Oui (ACTIVE) | **NULL** | **NULL** | 350 000 kWh |
| Usine Toulouse | Toulouse | **NULL** | 150 | NULL | Non | — | — | 2 500 000 kWh |
| Hotel Nice | Nice | 4 000 m2 | 280 | NOT_STARTED | Oui (ACTIVE) | **NULL** | **NULL** | 1 200 000 kWh |
| Ecole Marseille | Marseille | 2 800 m2 | 120 | IN_PROGRESS | **Non** | — | — | 600 000 kWh |

### Constats seed

| # | Constat | Impact |
|---|---------|--------|
| 1 | **reference_year = NULL** pour les 3 EFA | Trajectoire = "not_evaluable" systematiquement |
| 2 | **reference_year_kwh = NULL** pour les 3 EFA | Aucun calcul baseline possible |
| 3 | **Aucune TertiaireEfaConsumption** seedee | declare_consumption() jamais appele dans gen_tertiaire_efa.py |
| 4 | **Marseille** (2 800 m2 tertiaire) n'a **pas d'EFA** | 4e site eligible sans EFA = couverture demo incomplete |
| 5 | **Toulouse** : tertiaire_area = NULL | Evalue comme UNKNOWN, pas OUT_OF_SCOPE explicite |
| 6 | **Pas de site < 1000 m2** dans le pack | Scenario "hors perimetre" non demontre |
| 7 | Reporting period = 2024, pas d'annee ref 2010-2020 | Non conforme au cadre reglementaire DT |
| 8 | Aucune declaration SUBMITTED/VERIFIED | Tous en DRAFT — pas de scenario "declaration validee" |

---

## MATRICE DE RISQUE

| # | Constat | Severite | Impact demo | Effort fix | Priorite |
|---|---------|----------|-------------|------------|----------|
| R1 | Divergence A_RISQUE : engine=0EUR vs seed/migration=3750EUR | **CRITIQUE** | Risque financier affiche incorrect (25%) | S | **P0** |
| R2 | 2 services trajectoire ecrivent en DB sans coordination | **HAUTE** | Statut trajectoire potentiellement stale | M | **P0** |
| R3 | Seed EFA sans reference_year ni reference_year_kwh | **HAUTE** | Trajectoire always "not_evaluable" en demo | S | **P0** |
| R4 | Seed EFA sans TertiaireEfaConsumption | **HAUTE** | Aucune donnee conso EFA → calcul impossible | S | **P0** |
| R5 | 0% tracabilite legale (page/section) | **HAUTE** | Non auditable pour deploiement reel | L | **P1** |
| R6 | zone_climatique + categorie_fonctionnelle absentes | **MOYENNE** | Seuils absolus Cabs inutilisables | M | **P1** |
| R7 | ConsumptionExplorerPage.jsx : `* 0.052` hardcode | **MOYENNE** | Violation source-guard non detectee | S | **P1** |
| R8 | TertiaireSeuilAbsolu table vide (pas de Cabs seeds) | **MOYENNE** | Alternative trajectoire absolue non demo | M | **P2** |
| R9 | Legacy compliance_engine.py (1255 lignes) encore actif | **MOYENNE** | Confusion, 2 formules de penalite | L | **P2** |
| R10 | Marseille sans EFA malgre 2 800 m2 tertiaire | **BASSE** | Couverture demo incomplete | S | **P2** |
| R11 | Glossaire DT absent (EFA, DJU, CRefAbs, IIU, modulation) | **BASSE** | UX degradee pour non-experts | M | **P3** |
| R12 | Wizard sans barre progression ni brouillon | **BASSE** | UX non guidante | M | **P3** |
| R13 | Pas de site hors perimetre (<1000m2) dans seed | **BASSE** | Scenario OUT_OF_SCOPE non demontre | S | **P3** |

---

## SCORE PAR AXE (0-10)

| Axe | Score | Justification |
|-----|-------|---------------|
| **Sources & tracabilite** | **2/10** | 0% page/section dans tertiaire_sources_map.md. Les articles sont nommes mais jamais detailles. Frontend (complianceLabels) a des refs meilleures mais non verifiees. |
| **Calculs & formules** | **6/10** | Formule A.2 correcte et bien documentee (DT 45% + BACS 30% + APER 25%). Trajectoire algebriquement correcte. Mais divergence A_RISQUE critique (25% gap), 2 services trajectoire non coordonnes. |
| **UX/UI** | **7/10** | Labels FR excellents (486 lignes centralisees), guided mode, 4 onglets. Manque : glossaire DT, wizard progress bar, jalons explicites trajectoire. |
| **Coherence cross-module** | **5/10** | KPI coherence score = 55/100 (doc existant). 3 systemes scoring coexistent. A_RISQUE diverge entre modules. Consommation dual-source non reconciliee. |
| **Architecture** | **7/10** | compliance_score_service.py est une SoT bien documentee. Config centralisee YAML. Modele EFA riche (12 tables). Mais legacy compliance_engine.py (1255 lignes) encore actif, 2 services trajectoire. |
| **Verifiabilite** | **4/10** | Evidence drawer existe (V89) mais pas enrichi pour DT. Pas de "Pourquoi ce chiffre ?" sur trajectoire. Pas de decomposition DT/BACS/APER visible. Legal_ref absent des findings. |
| **Lisibilite** | **6/10** | Copy FR bonne, labels structures. Mais 0 glossaire DT inline, termes techniques non expliques (EFA, IIU, DJU, CRefAbs, modulation). Non-expert perdu. |
| **Donnees demo** | **3/10** | 3 EFA creees mais sans reference_year, sans conso EFA, sans Cabs. Trajectoire = "not_evaluable". Marseille sans EFA. Pas de site hors perimetre. |

### Score global

| Methode | Score |
|---------|-------|
| Moyenne simple | **5.0/10** |
| Moyenne ponderee (calculs + coherence x1.5) | **5.2/10** |

---

## Resume executif

L'architecture backend est **plus solide que le score initial de 4.9/10 ne le suggerait** :
- Le scoring A.2 unifie existe et est bien documente
- La config est centralisee dans regs.yaml
- Le modele EFA est riche (12 tables, normalisation DJU integree)
- 60 tests backend DT passent a 100%
- Le frontend ne fait aucun calcul metier DT (sauf 1 violation CO2 dans ConsumptionExplorer)

Les **bloquants majeurs** sont :
1. **Donnees demo** : les EFA n'ont ni annee de reference ni consommation seedee → trajectoire non demontrable
2. **Divergence A_RISQUE** : 25% d'ecart sur le risque financier selon le chemin de calcul
3. **Tracabilite legale** : 0% des regles ont une reference page/section precise
4. **2 services trajectoire** non coordonnes, ecriture concurrente en DB

**Prochaine etape recommandee** : Phase 2 (Fondations P0) — fixer R1, R3, R4 en priorite pour debloquer la demo trajectoire.
