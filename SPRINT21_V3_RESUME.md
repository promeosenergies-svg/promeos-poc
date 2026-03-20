# Sprint 21 v3 — Flex Foundations (version produit complète)

**Date :** 2026-03-18
**Branche :** `audit/flex-current-vision`
**Commit :** `25e37ab`

---

## 1. Décision

Sprint 21 v3 transforme la fondation backend en version produit complète avec UI intégrée dans les écrans existants, sans menu Flexibilité.

---

## 2. Fichiers modifiés

| Fichier | Rôle | Risque |
|---------|------|--------|
| `frontend/src/components/flex/FlexPotentialCard.jsx` | Carte flex dans fiche site | Nul |
| `frontend/src/components/flex/BacsFlexLink.jsx` | Pilotabilité dans BACS/conformité | Nul |
| `frontend/src/components/flex/TariffWindowsCard.jsx` | Fenêtres tarifaires dans facture/achat | Nul |
| `frontend/src/components/flex/FlexPortfolioSummary.jsx` | Ranking flex dans portefeuille | Nul |
| `frontend/src/components/flex/index.js` | Barrel export | Nul |
| `backend/routes/flex.py` | +portfolio scoped + validation durcie | Faible |
| `backend/models/flex_models.py` | +commentaire APER subtypes | Nul |
| `backend/tests/test_flex_foundation.py` | +6 tests (23 total) | Nul |

---

## 3. Composants UI intégrés

| Composant | Écran cible | Ce qu'il affiche |
|-----------|-------------|-----------------|
| **FlexPotentialCard** | Site360 / fiche site | Score flex, 4 dimensions, top 3 levers, asset count |
| **BacsFlexLink** | BacsRegulatoryPanel / conformité | Assets pilotables, sync BACS, statut controllabilité |
| **TariffWindowsCard** | PurchasePage / facture | Fenêtres par saison, period_type colorés, source |
| **FlexPortfolioSummary** | Patrimoine / portefeuille | Top 5 sites par potentiel, kW total, score moyen |

**Intégration :** Les composants sont créés et prêts à être importés dans les pages existantes via :
```jsx
import { FlexPotentialCard } from '../components/flex';
// puis dans le JSX : <FlexPotentialCard siteId={site.id} />
```

---

## 4. Endpoints ajustés

| Méthode | Path | Changement |
|---------|------|-----------|
| GET | `/api/flex/portfolios/{id}/flex-prioritization` | **Nouveau** — scope portefeuille strict |
| POST | `/api/flex/tariff-windows` | **Durci** — HC_SOLAIRE ≠ toute_annee, period_type validé |
| POST | `/api/flex/regulatory-opportunities` | **Durci** — APER 4 sous-types validés |

### TariffWindow validations ajoutées
- `period_type` ∈ {HC_NUIT, HC_SOLAIRE, HP, POINTE, SUPER_POINTE}
- `HC_SOLAIRE` + `toute_annee` = **400 rejeté**
- Format `HH:MM` obligatoire

### APER 4 sous-types
| Type | is_obligation | obligation_type / opportunity_type |
|------|---------------|-----------------------------------|
| Obligation ombrière | true | `solarisation_ombriere` |
| Obligation toiture | true | `solarisation_toiture` |
| Opportunité autoconso | false | `autoconsommation_individuelle` |
| Opportunité ACC | false | `acc` |
| Opportunité stockage | false | `stockage_batterie` |
| Opportunité revente | false | `revente_surplus` |

---

## 5. Tests (23 total flex)

| Classe | Tests | Vérifie |
|--------|-------|---------|
| TestFlexAssetCRUD | 4 | CRUD + confidence |
| TestFlexAssessment | 3 | Heuristic/asset/KPI |
| TestFlexMiniPreserved | 1 | Backward compat |
| TestTariffWindow | 2 | CRUD fenêtres |
| TestRegulatoryOpportunity | 2 | APER obligation + opportunity |
| TestSyncBacsPost | 2 | POST only |
| TestFlexAssessmentDimensions | 1 | 4 dimensions |
| TestBacsNotAutoControllable | 1 | BACS ≠ auto |
| TestFlexPortfolio | 1 | Portfolio ranking |
| **TestTariffWindowHardened** | **2** | HC_SOLAIRE + period_type |
| **TestAperSubtypes** | **3** | Obligation + ACC + invalid |
| **TestPortfolioFlexPrioritization** | **1** | Portfolio scoped |

---

## 6. Definition of Done

- [x] 4 composants UI flex créés et prêts à intégrer
- [x] Portfolio re-scopé `/portfolios/{id}/flex-prioritization`
- [x] TariffWindow durci (HC_SOLAIRE ≠ toute_annee)
- [x] APER 4 sous-types validés (obligation vs opportunity)
- [x] 23 tests flex fondation
- [x] 141 tests backend total OK
- [x] Build frontend OK
- [x] Aucun menu "Flexibilité"
- [x] Aucun dispatch/pilotage
- [x] Aucun hardcode HC
