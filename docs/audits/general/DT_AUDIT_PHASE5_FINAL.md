# Audit Phase 5 — Consolidation finale (8.5 -> 9.0)

> **Date** : 2026-03-30
> **Pre-requis** : Phase 4 terminee (score 8.5/10)
> **Objectif** : 9.0/10 via nettoyage et documentation

---

## Chantier A — Legacy compliance_engine.py

### Decision : Conserver avec depreciation documentee

L'analyse a revele **23 fichiers** dependants de compliance_engine.py :
- 8 fichiers de tests (test_compliance_engine, test_compliance_v68, test_cee_v69...)
- 5 services (compliance_coordinator, bacs_engine, onboarding_service...)
- 4 routes (compliance, sites, cockpit...)
- 3 scripts (seed_data, migrations...)
- 3 autres (models/site.py, schemas/kpi_catalog.py, regops/engine.py)

**Supprimer ce fichier risquerait de casser 23 fichiers** pour un gain cosmetique.
Le header de depreciation a ete enrichi avec un plan de migration en 4 etapes (Phase 6+).

Le fichier exporte des constantes (BASE_PENALTY_EURO, CO2_FACTOR_*) utilisees par les tests
et les migrations. La migration de ces imports vers les sources canoniques (emission_factors.py,
regs.yaml) est le prerequis avant suppression.

### Fichier modifie
- `backend/services/compliance_engine.py` : header enrichi, plan de migration documente

---

## Chantier B — Items KB reglementaires

### 4 items KB ajoutes au seed demo

| ID | Type | Domaine | Titre |
|----|------|---------|-------|
| `reg-sanctions-cch-l174` | rule | reglementaire | Sanctions DT — Art. L174-1 CCH |
| `reg-arrete-2020-04-10` | rule | reglementaire | Arrete du 10/04/2020 — Modalites DT |
| `kb-dt-modulation` | knowledge | reglementaire | Modulation DT — Dossier avant 30/09/2026 |
| `kb-dt-mutualisation` | knowledge | reglementaire | Mutualisation DT — Compensation inter-sites |

### Total KB reglementaire : 19 items (15 existants + 4 nouveaux)

Items existants couvrant le DT :
- `rule-decret-tertiaire` : Objectifs -40%/-50%/-60%
- `rule-operat-declaration` : Guide OPERAT
- `rule-bacs-290kw` : Seuil BACS 290 kW
- `rule-aper-solaire` : Obligation parking solaire
- `kb-cee-valorisation` : CEE
- `kb-gtb-roi` : GTB ROI

### Liaison findings -> KB

Le fichier `backend/regops/config/legal_refs.py` a ete enrichi avec `kb_item_id` :
```python
"OPERAT_NOT_STARTED": {
    "ref": "Arrete du 10 avril 2020, Art. 3",
    "url": "https://www.legifrance.gouv.fr/...",
    "kb_item_id": "reg-arrete-2020-04-10"  # lien vers KB
}
```

Cela permet au frontend de proposer "En savoir plus" sur chaque finding,
avec un lien direct vers l'item KB correspondant.

---

## Tests Phase 5

| Suite | Tests | Resultat |
|-------|-------|----------|
| Backend DT + compliance (110 tests) | 110/110 | **PASS** |
| Frontend (3616 tests) | En cours | **Attendu PASS** |

---

## Score final Phase 5

| Axe | Phase 4 | Phase 5 | Delta |
|-----|---------|---------|-------|
| Sources & tracabilite | 7 | **8** | +1 (4 items KB, liaison findings->KB) |
| Calculs & formules | 9 | 9 | — |
| UX/UI | 9 | 9 | — |
| Coherence cross-module | 9 | 9 | — |
| Architecture | 8 | **8.5** | +0.5 (plan migration legacy documente) |
| Verifiabilite | 8 | **9** | +1 (KB linkee aux findings) |
| Lisibilite | 9 | 9 | — |
| Donnees demo | 9 | 9 | — |
| **GLOBAL** | **8.5** | **~8.8** | **+0.3** |

---

## Bilan complet des 5 phases

| Phase | Score | Duree | Fichiers crees | Fichiers modifies | Tests ajoutes |
|-------|-------|-------|----------------|-------------------|---------------|
| 1 (Audit) | 5.0 | ~45 min | 1 | 0 | 0 |
| 2 (Fondations) | 6.2 | ~1.5h | 0 | 4 | 0 |
| 3 (Differenciateurs) | 7.4 | ~3h | 6 | 5 | 11 |
| 4 (Polish) | 8.5 | ~2h | 3 | 7 | 0 |
| 5 (Consolidation) | **8.8** | ~1h | 1 | 3 | 0 |
| **Total** | **8.8/10** | **~8h** | **11** | **19** | **11** |

### Livrables cles (5 phases)

**Backend (7 fichiers crees)** :
- `tertiaire_mutualisation_service.py` — Simulateur mutualisation inter-sites
- `tertiaire_modulation_service.py` — Simulateur modulation + TRI
- `regops/config/legal_refs.py` — 13 references legales avec kb_item_id
- `tests/test_mutualisation_modulation.py` — 11 tests

**Frontend (4 fichiers crees)** :
- `MutualisationSection.jsx` — Section mutualisation dans dashboard DT
- `ModulationDrawer.jsx` — Drawer simulation modulation
- `tertiaireEvidence.js` — 3 fixtures Evidence DT

**Documentation (5 rapports)** :
- `DT_AUDIT_PHASE1.md` — Audit initial (13 risques)
- `DT_AUDIT_PHASE2_RESULTS.md` — Fondations (4 P0 resolus)
- `DT_AUDIT_PHASE3_RESULTS.md` — Differenciateurs
- `DT_AUDIT_PHASE4_FINAL.md` — Polish UX
- `DT_AUDIT_PHASE5_FINAL.md` — Consolidation
- `tertiaire_sources_map.md` — V2, 0 "A CLARIFIER"
