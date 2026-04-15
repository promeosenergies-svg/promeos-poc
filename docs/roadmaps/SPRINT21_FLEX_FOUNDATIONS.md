# Sprint 21 — Flex Foundations

**Date :** 2026-03-18
**Branche :** `audit/flex-current-vision`
**Commit :** `915a61c`

---

## 1. Décision

Sprint 21 pose les fondations data de la flexibilité sans créer de navigation dédiée ni de pilotage réel. Les objets flex s'intègrent dans les vues patrimoine et conformité existantes.

---

## 2. Fichiers modifiés

| Fichier | Rôle | Risque |
|---------|------|--------|
| `backend/models/flex_models.py` | 4 modèles + 2 enums | Nul |
| `backend/models/__init__.py` | Registration | Nul |
| `backend/services/flex_assessment_service.py` | Assessment + BACS sync | Faible |
| `backend/routes/flex.py` | 5 endpoints + flex_mini préservé | Faible |
| `backend/routes/__init__.py` | Registration router | Nul |
| `backend/main.py` | Registration router | Nul |
| `backend/tests/test_flex_foundation.py` | 8 tests | Nul |
| `frontend/src/services/api/actions.js` | 5 appels API | Nul |
| `docs/backlog/flex-sprint-21-spec.md` | Spec exécutable | Nul |
| `docs/decisions/adr/ADR-flex-foundation-v2.md` | Décisions architecture | Nul |
| `docs/data-dictionary/flex-foundation-v2.md` | Modèles + enums | Nul |

---

## 3. Modèles ajoutés

### FlexAsset
Inventaire des assets pilotables par site. 9 types (hvac, irve, battery, pv, etc.), 5 méthodes de contrôle, lien BACS optionnel, règle confidence=high → data_source obligatoire.

### FlexAssessment
Évaluation du potentiel flex par site. Score 0-100, potential_kw/kwh_year, source (asset_based vs heuristic), KPI metadata obligatoire (définition, formule, unité, période, périmètre, source, confidence).

### NebcoSignal
Structure de signal marché NEBCO. Direction up (réduction) ou down (augmentation, nouveau NEBCO). Aucun moteur de valorisation — structure uniquement.

### RegulatoryOpportunity
Opportunités réglementaires par site. APER en 2 temps (obligation solarisation + opportunité autoconso/ACC/stockage), CEE P6 avec caveat (éligibilité potentielle, TRI > 3 ans).

---

## 4. Endpoints

| Méthode | Path | Description |
|---------|------|-------------|
| GET | /api/flex/assets | Liste assets (filtre site_id, type) |
| POST | /api/flex/assets | Créer un asset |
| PATCH | /api/flex/assets/{id} | Modifier un asset |
| GET | /api/flex/assets/sync-from-bacs | Sync CVC → FlexAsset |
| GET | /api/flex/assessment | Assessment (asset > heuristic) |
| GET | /api/sites/{id}/flex/mini | flex_mini existant (préservé) |

---

## 5. Tests (8)

1. Create flex asset OK
2. List flex assets filtrés
3. Confidence high sans source = 400
4. Confidence high avec source = OK
5. Assessment heuristic fallback
6. Assessment asset-based
7. KPI metadata présente
8. flex_mini backward compat

---

## 6. Règles métier implémentées

| Règle | Implémentation |
|-------|---------------|
| confidence=high → data_source requis | Validation dans POST/PATCH |
| BACS classe A/B → is_controllable=true | sync_bacs_to_flex_assets() |
| gtb_class dérivé de BacsCvcSystem.system_class | sync auto |
| APER = solarisation + opportunités séparées | RegulatoryOpportunity.is_obligation vs opportunity_type |
| CEE = éligibilité potentielle + caveat | cee_caveat field obligatoire |
| NEBCO direction=down (nouveau) | NebcoSignal.direction enum |
| Tout KPI = définition+formule+unité+période+périmètre+source+confidence | FlexAssessment.kpi_* fields |

---

## 7. Risques / limites

| Risque | Sévérité |
|--------|----------|
| Pas de météo réelle (Sprint 22) | Attendu |
| Pas de DJU/DJC | Attendu |
| Pas de TURPE 7 grille seed | Sprint 22 |
| Pas de dispatch/pilotage | Intentionnel |
| Pas de navigation "Flexibilité" | Intentionnel |

---

## 8. Definition of Done

- [x] FlexAsset modèle + CRUD
- [x] FlexAssessment avec KPI metadata
- [x] NebcoSignal structure
- [x] RegulatoryOpportunity (APER 2 temps, CEE caveat)
- [x] Sync BACS → FlexAsset
- [x] flex_mini préservé (backward compat)
- [x] 8 tests fondations
- [x] 126 tests backend total OK
- [x] Build frontend OK
- [x] Aucun menu "Flexibilité" créé
- [x] Aucun dispatch/pilotage codé
- [x] Docs spec + ADR + data dictionary
