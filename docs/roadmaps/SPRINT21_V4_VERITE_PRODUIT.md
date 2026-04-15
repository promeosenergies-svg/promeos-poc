# Sprint 21 v4 — Correctif vérité produit

**Date :** 2026-03-18
**Branche :** `audit/flex-current-vision`
**Commit :** `7ab2853`

---

## 1. Décision

Ce patch corrige l'écart entre le résumé v3 ("composants prêts à intégrer") et la réalité du code (0 composant monté). Les 4 composants flex sont maintenant **réellement câblés** dans les pages existantes.

---

## 2. Pages réellement patchées

| Page | Composant | Ligne | Point d'insertion |
|------|-----------|-------|-------------------|
| **Site360.jsx** | `FlexPotentialCard` | L388 | TabResume, après delivery points + segmentation |
| **Site360.jsx** | `BacsFlexLink` | L1322 | TabConformite, après BacsRegulatoryPanel |
| **PurchasePage.jsx** | `TariffWindowsCard` | L567 | Après MarketContextBanner, avant les tabs |
| **Patrimoine.jsx** | `FlexPortfolioSummary` | L841 | Section portefeuille, après Segmentation Card |

---

## 3. Composants réellement montés

| Composant | Statut v3 | Statut v4 |
|-----------|-----------|-----------|
| FlexPotentialCard | "ready to import" | **Monté dans Site360 TabResume** |
| BacsFlexLink | "ready to import" | **Monté dans Site360 TabConformite** |
| TariffWindowsCard | "ready to import" | **Monté dans PurchasePage** |
| FlexPortfolioSummary | "ready to import" | **Monté dans Patrimoine** |

---

## 4. API/doc corrigées

| Point | Correction |
|-------|-----------|
| TariffWindowsCard label | "Fenêtres tarifaires" → **"Fenêtres tarifaires actives"** |
| Portfolio endpoint | `/portfolios/{id}/flex-prioritization` confirmé existant (L301 flex.py) |
| `/portfolio` backward compat | Conservé (L356 flex.py) |
| HC_SOLAIRE affichage | Jamais affiché comme label client générique — toujours via period_type dans TariffWindow |

---

## 5. Tests

- 141 tests backend OK (inchangés — les composants front ne nécessitent pas de nouveaux tests backend)
- Build frontend OK (2724 modules, 40s)
- Vérification grep : 4/4 imports + 4/4 montages confirmés

---

## 6. Definition of Done

- [x] FlexPotentialCard monté dans Site360 TabResume
- [x] BacsFlexLink monté dans Site360 TabConformite
- [x] TariffWindowsCard monté dans PurchasePage
- [x] FlexPortfolioSummary monté dans Patrimoine
- [x] Label "Fenêtres tarifaires actives" (pas générique)
- [x] 0 composant "ready to import" restant
- [x] 141 tests OK + build OK
- [x] Aucun menu Flexibilité
- [x] Aucun dispatch/pilotage

---

## Bilan Sprint 21 complet (v1 → v4)

| Version | Focus | Tests |
|---------|-------|-------|
| v1 | Modèles + service + 5 endpoints | 126 |
| v2 | TariffWindow + 4 dimensions + BACS fix + portfolio + RegOpp | 135 |
| v3 | UI components + portfolio scoped + TariffWindow durci + APER 4 types | 141 |
| **v4** | **Câblage réel dans 4 pages existantes** | **141** |

La branche `audit/flex-current-vision` est maintenant **mergeable** avec une intégration produit complète.
