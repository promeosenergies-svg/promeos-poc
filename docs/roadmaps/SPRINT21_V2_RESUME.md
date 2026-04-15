# Sprint 21 v2 — Flex Foundations (version mergeable)

**Date :** 2026-03-18
**Branche :** `audit/flex-current-vision`
**Commit :** `b7f301f`

---

## 1. Décision

Sprint 21 v2 corrige les simplifications de v1 et produit une fondation flex complète, mergeable dans main.

---

## 2. Corrections appliquées

| v1 | v2 | Impact |
|----|-----|--------|
| Pas de TariffWindow | **TariffWindow model** (saison, period_type, day_types, segment) | Plus de hardcode HC |
| sync-from-bacs = GET | **POST** (side-effect explicite) | Sémantique HTTP correcte |
| BACS A/B → is_controllable=true | **is_controllable=false** toujours, hint control_method | Pas de faux positif |
| FlexAssessment = score unique | **4 dimensions** : technical, data, economic, regulatory | Évaluation défendable |
| RegulatoryOpportunity sans endpoint | **GET/POST /regulatory-opportunities** | APER 2 temps exploitable |
| Pas de vue portfolio | **GET /flex/portfolio** (ranking par site) | Priorisation multi-sites |

---

## 3. Fichiers modifiés

| Fichier | Changement | Risque |
|---------|-----------|--------|
| `backend/models/flex_models.py` | +TariffWindow, +4 dimensions FlexAssessment | Faible |
| `backend/models/__init__.py` | Registration TariffWindow | Nul |
| `backend/services/flex_assessment_service.py` | BACS fix + 4 dimensions + sync POST | Faible |
| `backend/routes/flex.py` | +6 endpoints, sync GET→POST | Faible |
| `backend/tests/test_flex_foundation.py` | +9 tests (17 total) | Nul |
| `frontend/src/services/api/actions.js` | +5 appels API v2 | Nul |

---

## 4. Modèles / endpoints

### Nouveau modèle : TariffWindow

| Champ | Description |
|-------|-------------|
| season | hiver, ete, mi_saison, toute_annee |
| period_type | HC_NUIT, HC_SOLAIRE, HP, POINTE, SUPER_POINTE |
| months | JSON [1,2,...] |
| day_types | JSON ["weekday","weekend","holiday","all"] |
| segment | C5, C4, C3, HTA |
| source | CRE, Enedis, manual |

### Endpoints ajoutés (v2)

| Méthode | Path | Description |
|---------|------|-------------|
| GET | /api/flex/tariff-windows | Liste fenêtres tarifaires |
| POST | /api/flex/tariff-windows | Créer fenêtre |
| GET | /api/flex/regulatory-opportunities | Liste opportunités réglementaires |
| POST | /api/flex/regulatory-opportunities | Créer opportunité |
| GET | /api/flex/portfolio | Ranking flex multi-sites |
| POST | /api/flex/assets/sync-from-bacs | Sync BACS → FlexAsset (fix GET→POST) |

### FlexAssessment 4 dimensions

| Dimension | Calcul |
|-----------|--------|
| technical_readiness | % assets controllables / total |
| data_confidence | % assets vérifiés (high/medium) / total |
| economic_relevance | f(total_kw) simplifié |
| regulatory_alignment | aligned si BACS lié + controllable, sinon partial/unknown |

---

## 5. Tests (17)

| Classe | Tests | Vérifie |
|--------|-------|---------|
| TestFlexAssetCRUD | 4 | CRUD, confidence validation |
| TestFlexAssessment | 3 | Heuristic fallback, asset-based, KPI metadata |
| TestFlexMiniPreserved | 1 | Backward compat |
| TestTariffWindow | 2 | CRUD fenêtres |
| TestRegulatoryOpportunity | 2 | APER obligation + opportunity |
| TestSyncBacsPost | 2 | POST only, GET = 405 |
| TestFlexAssessmentDimensions | 1 | 4 dimensions présentes |
| TestBacsNotAutoControllable | 1 | BACS sync ≠ auto controllable |
| TestFlexPortfolio | 1 | Portfolio ranking |

---

## 6. Risques restants

| Risque | Sévérité | Action |
|--------|----------|--------|
| Pas de seed TURPE 7 grilles CRE | Moyen | Sprint 22 |
| Météo réelle absente | Moyen | Sprint 22 (Open-Meteo) |
| economic_relevance simplifié (f(kW)) | Faible | Enrichir avec données facture |
| regulatory_alignment basique | Faible | Enrichir avec données conformité |
| Pas de composants UI dans les écrans existants | Moyen | Sprint 22 |

---

## 7. Definition of Done

- [x] TariffWindow model + CRUD
- [x] sync-from-bacs = POST (pas GET)
- [x] BACS ≠ auto-controllable
- [x] FlexAssessment 4 dimensions
- [x] RegulatoryOpportunity endpoints (APER 2 temps)
- [x] Portfolio flex ranking
- [x] 17 tests flex fondation
- [x] 135 tests backend total OK
- [x] Build frontend OK
- [x] Aucun menu "Flexibilité"
- [x] Aucun dispatch/pilotage
- [x] Aucun hardcode HC
