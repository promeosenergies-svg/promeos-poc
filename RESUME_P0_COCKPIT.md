# Rapport P0 — Cockpit Credibility Fix

**Branche** : `feat/cockpit-world-class`
**Date** : 2026-03-23
**Statut** : DONE — 12/12 tests P0 verts, 0 regression (38/38 smoke)

---

## Problemes resolus

### P0-1 — Score conformite : source unique RegAssessment
- **Avant** : 3 systemes divergents (snapshot, RegOps, cockpit count brut)
- **Apres** : `compliance_score` dans `/api/cockpit` provient de `RegAssessment` via `compliance_score_service` (0-100, higher=better)
- **Tracabilite ajoutee** :
  - `compliance_source: "RegAssessment"`
  - `compliance_computed_at: <ISO timestamp>`
  - `sites_evaluated: <int>`

### P0-2 — Risque financier A_RISQUE aligne a 3 750 EUR
- **Avant** : `compliance_engine.py` traitait A_RISQUE a 0 EUR (via `BASE_PENALTY_EURO * 0`), tandis que `migrations.py` et `orchestrator.py` utilisaient `BASE_PENALTY_EURO * 0.5`
- **Apres** : Constantes centralisees dans `compliance_engine.py` :
  ```
  BASE_PENALTY_EURO       = 7 500
  A_RISQUE_PENALTY_RATIO  = 0.5
  A_RISQUE_PENALTY_EURO   = 3 750
  ```
- `migrations.py` et `orchestrator.py` importent `A_RISQUE_PENALTY_EURO` — plus aucun `* 0.5` hardcode
- **Reponse enrichie** : `risque_breakdown` (reglementaire / billing / contract / total)

### P0-3 — Trajectoire DT : nouvel endpoint backend
- **Avant** : Aucun endpoint trajectoire ; le front devait calculer `(1 - conso_N / conso_ref) * 100`
- **Apres** : `GET /api/cockpit/trajectory` retourne :
  - `ref_year`, `ref_kwh` (MWh)
  - `annees[]`, `reel_mwh[]`, `objectif_mwh[]`
  - `reduction_pct_actuelle`
  - `jalons` DT : -25% (2026), -40% (2030), -50% (2040), -60% (2050)
  - `surface_m2_total`, `computed_at`
- Interpolation lineaire entre jalons reglementaires
- Consommations reelles agregees depuis `MeterReading` (freq granulaires uniquement, evite doublons)
- Test structurel : aucun calcul trajectoire dans les fichiers JSX/hooks du front

### P0-4 — CO2 facteur aligne ADEME 2024
- **Avant** : 0.052 kgCO2/kWh (non source)
- **Apres** :
  ```
  CO2_FACTOR_ELEC_KG_KWH = 0.0569  (ADEME 2024)
  CO2_FACTOR_GAZ_KG_KWH  = 0.2270  (ADEME 2024)
  ```

---

## Fichiers modifies

| Fichier | Type de changement |
|---------|--------------------|
| `backend/services/compliance_engine.py` | Constantes centralisees (BASE_PENALTY, A_RISQUE, CO2) + fix `compute_risque_financier` |
| `backend/routes/cockpit.py` | Import RegAssessment, tracabilite score, risque_breakdown, nouvel endpoint `/trajectory` |
| `backend/database/migrations.py` | Import `A_RISQUE_PENALTY_EURO`, suppression `* 0.5` hardcode |
| `backend/services/demo_seed/orchestrator.py` | Import `A_RISQUE_PENALTY_EURO`, suppression `* 0.5` hardcode |
| `backend/tests/test_cockpit_p0.py` | **NOUVEAU** — 12 tests (score source, risk constants, trajectory, CO2 factor, no-calc-front) |

---

## Tests

```
tests/test_cockpit_p0.py::TestCockpitComplianceScore::test_score_from_reg_assessment    PASSED
tests/test_cockpit_p0.py::TestCockpitComplianceScore::test_computed_at_present          PASSED
tests/test_cockpit_p0.py::TestCockpitComplianceScore::test_sites_evaluated_present      PASSED
tests/test_cockpit_p0.py::TestCockpitRisk::test_a_risque_penalty_constant               PASSED
tests/test_cockpit_p0.py::TestCockpitRisk::test_no_hardcoded_half_penalty_in_migrations PASSED
tests/test_cockpit_p0.py::TestCockpitRisk::test_risque_breakdown_present                PASSED
tests/test_cockpit_p0.py::TestCockpitTrajectory::test_trajectory_endpoint_exists        PASSED
tests/test_cockpit_p0.py::TestCockpitTrajectory::test_trajectory_structure              PASSED
tests/test_cockpit_p0.py::TestCockpitTrajectory::test_trajectory_jalons_correct         PASSED
tests/test_cockpit_p0.py::TestCockpitTrajectory::test_no_calc_in_frontend_trajectory    PASSED
tests/test_cockpit_p0.py::TestCo2Factor::test_co2_factor_elec_canonical                 PASSED
tests/test_cockpit_p0.py::TestCo2Factor::test_co2_factor_gaz_canonical                  PASSED
```

**Regression** : 0 (38/38 smoke tests passent)

---

## Definition of Done

- [x] `pytest tests/test_cockpit_p0.py -v` — 12/12 verts
- [x] `pytest tests/test_smoke.py -v` — 0 regression (38/38)
- [x] `GET /api/cockpit` retourne `compliance_score` + `compliance_source = "RegAssessment"`
- [x] `GET /api/cockpit/trajectory` retourne jalons DT corrects (-25%/2026, -40%/2030)
- [x] `A_RISQUE_PENALTY_EURO = 3750` dans `compliance_engine.py`
- [x] `CO2_FACTOR_ELEC_KG_KWH = 0.0569` dans `compliance_engine.py`
- [x] Aucune valeur hardcodee `* 0.5` sans import de constante
- [x] Aucun calcul trajectoire dans fichier JSX ou hook React
- [x] Aucun fichier front modifie

---

## Guards respectes

- Aucun composant React/JSX modifie
- `avancement_decret_pct` et tous champs existants conserves (retro-compatible)
- `regops/scoring.py` non touche (source de verite, lecture seule)
- Pas de migration MaturiteConformite% du front (backlog separe)
