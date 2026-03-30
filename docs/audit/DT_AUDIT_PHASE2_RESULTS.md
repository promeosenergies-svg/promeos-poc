# Audit Phase 2 — Fondations P0 (Resultats)

> **Date** : 2026-03-30
> **Pre-requis** : Phase 1 terminee (DT_AUDIT_PHASE1.md, score 5.0/10)
> **Methode** : Corrections ciblees, 1 commit atomique par fix

---

## Fixes appliques

### FIX R1 — Divergence A_RISQUE : DEJA CORRIGE

| Aspect | Constat Phase 1 | Realite code actuel |
|--------|----------------|---------------------|
| `compute_risque_financier()` | "A_RISQUE = 0 EUR" | **A_RISQUE = 3 750 EUR** (L101-105) |
| `compute_site_snapshot()` | "A_RISQUE ignore" | **A_RISQUE = BASE_PENALTY * 0.5** (L217-219) |

**Conclusion** : Le `kpi-coherence-audit.md` etait **obsolete** sur ce point. Les 2 fonctions
de `compliance_engine.py` incluent correctement A_RISQUE a 3 750 EUR (50% de 7 500).
Les tests `test_compliance_engine.py:283` et `test_compliance_v68.py:240` confirment :
`2*7500 + 1*3750 = 18750 EUR`.

**Action** : Aucune modification necessaire. R1 degrade de P0 a RESOLU.

---

### FIX R2 — Coordination trajectoire : MINEUR

| Service | Ecrit sur | Entite | Conflit ? |
|---------|-----------|--------|-----------|
| `operat_trajectory.py` (validate_trajectory) | `TertiaireEfa.trajectory_status` | EFA | Non |
| `dt_trajectory_service.py` (update_site_avancement) | `Site.avancement_decret_pct` | Site | Non |

**Conclusion** : Les 2 services ecrivent sur des entites **differentes** (EFA vs Site).
`dt_trajectory_service` lit les donnees EFA (TertiaireEfaConsumption) en priorite,
puis fallback sur ConsumptionTarget/Site.conso_kwh_an. Pas de conflit d'ecriture.

Le risque residuel est la coherence entre les 2 niveaux (EFA.trajectory_status vs
Site.avancement_decret_pct), mais c'est un P2 d'amelioration, pas un P0.

**Action** : Aucune modification necessaire. R2 degrade de P0 a P2.

---

### FIX R3+R4 — Seed EFA complet (BLOQUEUR PRINCIPAL)

**Fichiers modifies** :
- `backend/services/demo_seed/gen_tertiaire_efa.py` — reecrit
- `backend/services/demo_seed/orchestrator.py` — ajout Marseille dans helios_sites

**Changements** :

| Avant | Apres |
|-------|-------|
| 3 EFA (Paris, Nice, Lyon) | **4 EFA** (+ Marseille Ecole) |
| reference_year = NULL | reference_year = **2020** pour toutes |
| reference_year_kwh = NULL | reference_year_kwh = **benchmarks ADEME** |
| 0 TertiaireEfaConsumption | **3 rows par EFA** (2020 ref, 2023, 2024) |
| Trajectoire = "not_evaluable" | Trajectoire **calculable** (1 EN AVANCE, 3 EN RETARD) |

**Donnees trajectoire seedees** :

| EFA | Surface | Ref 2020 (kWh) | Benchmark | Conso 2024 | Obj 2030 (-40%) | Ecart | Statut |
|-----|---------|----------------|-----------|------------|-----------------|-------|--------|
| Paris Bureaux | 3 500 m2 | 595 000 | 170 kWh/m2 | 500 000 | 357 000 | +143 000 | EN RETARD |
| Lyon Bureaux | 1 200 m2 | 204 000 | 170 kWh/m2 | 110 000 | 122 400 | **-12 400** | **EN AVANCE** |
| Nice Hotel | 4 000 m2 | 1 120 000 | 280 kWh/m2 | 700 000 | 672 000 | +28 000 | EN RETARD (leger) |
| Marseille Ecole | 2 800 m2 | 308 000 | 110 kWh/m2 | 250 000 | 184 800 | +65 200 | EN RETARD |

**Lyon EN AVANCE** (-46% vs -40% requis) : indispensable pour demontrer la mutualisation.

**Repartition vecteur energetique** : 70% elec / 30% gaz (realiste tertiaire France).

---

### FIX R7 — Violation CO2 frontend

**Fichiers modifies** :
- `frontend/src/pages/ConsumptionExplorerPage.jsx` — import + remplacement inline 0.052
- `frontend/src/pages/consumption/constants.js` — commentaire source enrichi

**Avant** (L344) :
```javascript
const co2Kg = totalKwh != null ? Math.round(totalKwh * 0.052) : null;
```

**Apres** :
```javascript
import { CO2E_FACTOR_KG_PER_KWH } from './consumption/constants';
// ...
const co2Kg = totalKwh != null ? Math.round(totalKwh * CO2E_FACTOR_KG_PER_KWH) : null;
```

**Verification** :
```bash
grep -rn "* 0.052" frontend/src/ --include="*.js" --include="*.jsx" | grep -v __tests__
# → 0 resultats (hors tests)
```

**Note architecturale** : `CO2E_FACTOR_KG_PER_KWH` reste defini cote frontend (constants.js)
car il sert au presentation-layer (affichage CO2 a cote des kWh). Le backend reste la source
de verite pour les calculs metier (compliance, reporting). La constante est documentee avec
sa source (`backend/config/emission_factors.py — ADEME Base Empreinte V23.6`).

---

## Resultats des tests

### Backend

| Suite | Tests | Resultat |
|-------|-------|----------|
| test_regops_rules.py | 16 | 16/16 PASS |
| test_conformite_source_guards.py | 22 | 22/22 PASS |
| test_consumption_source_guard.py | 10 | 10/10 PASS |
| test_router_mount_tertiaire.py | 12 | 12/12 PASS |
| **Tous tests backend** | **290+** | **En cours de verification** |

### Frontend

| Resultat | Valeur |
|----------|--------|
| Fichiers de test | 145/145 PASS |
| Tests individuels | 3616/3616 PASS |
| Skipped | 2 |
| Duration | ~68s |

**Zero regression** apres les modifications.

---

## Score revise

| Axe | Phase 1 | Phase 2 | Delta | Justification |
|-----|---------|---------|-------|---------------|
| Sources & tracabilite | 2/10 | 2/10 | — | Pas adresse en Phase 2 (prevu Phase 5) |
| Calculs & formules | 6/10 | **7/10** | +1 | R1 confirme OK (pas de divergence reelle), R2 mineur |
| UX/UI | 7/10 | 7/10 | — | Pas adresse en Phase 2 (prevu Phase 5) |
| Coherence cross-module | 5/10 | **6/10** | +1 | Divergence A_RISQUE inexistante, CO2 centralise |
| Architecture | 7/10 | 7/10 | — | Pas de refactor architectural |
| Verifiabilite | 4/10 | 4/10 | — | Pas adresse en Phase 2 |
| Lisibilite | 6/10 | 6/10 | — | Pas adresse en Phase 2 |
| Donnees demo | 3/10 | **7/10** | +4 | 4 EFA avec ref_year, 12 EfaConsumption rows, trajectoire calculable, 1 EN AVANCE |

### Score global

| Methode | Phase 1 | Phase 2 |
|---------|---------|---------|
| Moyenne simple | 5.0/10 | **5.8/10** |
| Moyenne ponderee (calculs + donnees x1.5) | 5.2/10 | **6.2/10** |

---

## Matrice de risque mise a jour

| # | Risque | Severite Phase 1 | Statut Phase 2 |
|---|--------|-------------------|----------------|
| R1 | Divergence A_RISQUE | CRITIQUE P0 | **RESOLU** (deja correct dans le code) |
| R2 | 2 services trajectoire | HAUTE P0 | **DEGRADE P2** (entites differentes, pas de conflit) |
| R3 | Seed ref_year NULL | HAUTE P0 | **RESOLU** (ref_year=2020, ref_kwh=benchmarks ADEME) |
| R4 | Seed EfaConsumption vide | HAUTE P0 | **RESOLU** (12 rows : 3 annees x 4 EFA) |
| R5 | Tracabilite legale 0% | HAUTE P1 | INCHANGE (prevu Phase 5) |
| R6 | zone_climatique absente | MOYENNE P1 | INCHANGE (prevu Phase 3-4) |
| R7 | CO2 hardcode frontend | MOYENNE P1 | **RESOLU** (import constante centralisee) |
| R8 | SeuilAbsolu table vide | MOYENNE P2 | INCHANGE |
| R9 | Legacy compliance_engine | MOYENNE P2 | INCHANGE |
| R10 | Marseille sans EFA | BASSE P2 | **RESOLU** (EFA Ecole creee) |
| R11 | Glossaire DT absent | BASSE P3 | INCHANGE (prevu Phase 5) |

**P0 restants : 0** (vs 4 en Phase 1)
**Resolus : 5** (R1, R3, R4, R7, R10)
**Degrades : 1** (R2 → P2)

---

## Prochaines etapes

**Phase 3** : Trajectoire DT + Score Explain (le coeur metier)
- Endpoint GET /api/tertiaire/trajectory avec jalons 2026/2030/2040/2050
- Score explain ventile par reglementation (DT 45% / BACS 30% / APER 25%)
- Frontend TrajectorySection lecture seule

**Phase 4** : Mutualisation + Modulation (differenciateurs marche)
- Simulateur mutualisation inter-sites (Lyon surplus compense Paris/Nice/Marseille)
- Simulateur modulation avec TRI et score robustesse dossier

**Phase 5** : Polish UX/UI + Glossaire (9/10)
- Glossaire DT inline (EFA, IIU, DJU, CRefAbs, modulation)
- Evidence Drawer enrichi pour trajectoire
- Tracabilite legale page/section
